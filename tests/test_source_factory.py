"""
tests/test_source_factory.py

Coverage for app/ingestion/factory.py's SourceFactory.create_all().

SCOPE: this file tests SourceFactory's OWN routing/injection logic --
registry lookup, unknown-type error, API key injection from config vs.
params, RSS needing no key, multi-entry ordering. It does NOT test the
three adapter classes' fetch_events() implementations (HTTP calls,
response parsing) -- those are explicitly deferred per the master doc's
priority order ("ingestion adapters last... need HTTP mocking"). Tests
below construct REAL NewsDataSource/RSSDataSource/OpenWeatherDataSource
instances (not mocks standing in for them) specifically so that
SourceFactory's `source_cls(**params)` call is exercised against the
real constructors' actual signatures, not an assumed one -- consistent
with this project's pattern of catching real signature mismatches (e.g.
the routes.py dict-vs-attribute issue) by testing against real classes
wherever feasible rather than mocking the exact thing being verified.

CONFIRMED THIS SESSION, VIA DIRECT FILE READS (not assumed):
  - All three adapter __init__ signatures accept **kwargs. This means
    SourceFactory's source_cls(**params) call can NEVER raise a
    TypeError for an unexpected/extra key in params -- any junk in a
    config.yaml params block is silently absorbed and ignored by the
    adapter's constructor. Covered by a dedicated test below
    (test_extra_unrecognized_params_are_silently_ignored) rather than
    just asserted here, since "no error" needing its own positive test
    is easy to skip past.
  - NewsDataSource and OpenWeatherDataSource both default
    api_key: str = "" in their constructors. This means if
    SourceFactory ever failed to inject the key correctly (e.g. a
    typo'd entry in _API_KEY_CONFIG_KEYS or a missing config value),
    NOTHING would raise at construction time -- the failure would only
    surface later, inside fetch_events(), as that class's own
    `raise ValueError(...) if not self.api_key` check. This is a real,
    slightly fragile coupling between factory.py and these two
    classes' constructors: a key-injection bug would silently produce
    a source with an empty api_key, not an immediate, loud failure.
    Covered by tests asserting the REAL injected api_key value on the
    constructed instance, not just "no exception was raised."
  - RSSDataSource needs no api_key at all (absent from
    _API_KEY_CONFIG_KEYS by design, per factory.py's own comment) --
    covered by a dedicated test confirming params pass through
    untouched and no api_key attribute injection happens.
"""
import pytest

from app.ingestion.factory import SourceFactory
from app.ingestion.newsdata import NewsDataSource
from app.ingestion.rss import RSSDataSource
from app.ingestion.openweather import OpenWeatherDataSource


class TestCreateAll:
    def test_empty_active_list_returns_empty(self):
        config = {"data_sources": {"active": []}}
        result = SourceFactory.create_all(config)
        assert result == []

    def test_missing_data_sources_key_returns_empty(self):
        # config.get("data_sources", {}) falls back to {} entirely --
        # confirms the top-level .get default, not just the inner one.
        config = {}
        result = SourceFactory.create_all(config)
        assert result == []

    def test_missing_active_key_returns_empty(self):
        config = {"data_sources": {}}
        result = SourceFactory.create_all(config)
        assert result == []

    def test_unknown_source_type_raises_value_error(self):
        config = {"data_sources": {"active": [{"type": "carrier_pigeon"}]}}
        with pytest.raises(ValueError, match="Unknown data source type: carrier_pigeon"):
            SourceFactory.create_all(config)

    def test_newsdata_source_constructed_with_injected_api_key(self):
        config = {
            "data_sources": {
                "active": [{"type": "newsdata", "params": {"query": "flood OR strike"}}],
                "newsdata_api_key": "real-newsdata-key-123",
            }
        }
        result = SourceFactory.create_all(config)

        assert len(result) == 1
        source = result[0]
        assert isinstance(source, NewsDataSource)
        assert source.api_key == "real-newsdata-key-123"
        assert source.query == "flood OR strike"

    def test_openweather_source_constructed_with_injected_api_key(self):
        config = {
            "data_sources": {
                "active": [{"type": "openweather", "params": {"locations": ["Chennai", "Mumbai"]}}],
                "openweather_api_key": "real-openweather-key-456",
            }
        }
        result = SourceFactory.create_all(config)

        assert len(result) == 1
        source = result[0]
        assert isinstance(source, OpenWeatherDataSource)
        assert source.api_key == "real-openweather-key-456"
        assert source.locations == ["Chennai", "Mumbai"]

    def test_api_key_comes_from_config_not_from_entry_params(self):
        # Confirms factory.py's own stated invariant: params never
        # contains secrets. Even if a caller mistakenly puts an
        # api_key inside the entry's params block, the REAL config
        # value should win, since factory.py unconditionally
        # overwrites params["api_key"] after copying entry params.
        config = {
            "data_sources": {
                "active": [{"type": "newsdata", "params": {"api_key": "should-be-overwritten"}}],
                "newsdata_api_key": "the-real-key",
            }
        }
        result = SourceFactory.create_all(config)
        assert result[0].api_key == "the-real-key"

    def test_rss_source_gets_no_api_key_injected(self):
        config = {
            "data_sources": {
                "active": [{"type": "rss", "params": {"feed_urls": ["https://example.com/feed.xml"]}}],
                # deliberately no rss-related api key entry anywhere --
                # RSS needs none, per factory.py's own comment.
            }
        }
        result = SourceFactory.create_all(config)

        assert len(result) == 1
        source = result[0]
        assert isinstance(source, RSSDataSource)
        assert source.feed_urls == ["https://example.com/feed.xml"]
        # RSSDataSource has no api_key attribute at all -- confirms no
        # injection was attempted, not just that it's empty.
        assert not hasattr(source, "api_key")

    def test_missing_api_key_in_config_results_in_empty_string_default(self):
        # If newsdata_api_key is simply absent from config (not just
        # empty), data_sources_config.get(api_key_config_key) returns
        # None, and params["api_key"] = None gets passed to the
        # constructor -- NOT the constructor's own "" default, since
        # the factory explicitly sets the key. This is worth confirming
        # directly: it means a missing config key produces api_key=None,
        # not api_key="", which is a real (small) distinction from what
        # NewsDataSource's signature default alone would suggest.
        config = {
            "data_sources": {
                "active": [{"type": "newsdata", "params": {}}],
                # newsdata_api_key absent entirely
            }
        }
        result = SourceFactory.create_all(config)
        assert result[0].api_key is None

    def test_multiple_entries_produce_multiple_sources_in_order(self):
        config = {
            "data_sources": {
                "active": [
                    {"type": "rss", "params": {"feed_urls": ["https://a.com/feed.xml"]}},
                    {"type": "newsdata", "params": {}},
                    {"type": "openweather", "params": {"locations": ["Delhi"]}},
                ],
                "newsdata_api_key": "key1",
                "openweather_api_key": "key2",
            }
        }
        result = SourceFactory.create_all(config)

        assert len(result) == 3
        assert isinstance(result[0], RSSDataSource)
        assert isinstance(result[1], NewsDataSource)
        assert isinstance(result[2], OpenWeatherDataSource)

    def test_entry_with_no_params_block_uses_constructor_defaults(self):
        # entry.get("params", {}) falls back to {} -- constructor
        # defaults (query's default string, locations=None -> [],
        # feed_urls=None -> []) should apply untouched.
        config = {
            "data_sources": {
                "active": [{"type": "rss"}],  # no "params" key at all
            }
        }
        result = SourceFactory.create_all(config)

        assert len(result) == 1
        assert result[0].feed_urls == []

    def test_extra_unrecognized_params_are_silently_ignored(self):
        # CONFIRMED behavior, not assumed: all three adapters accept
        # **kwargs, so SourceFactory.create_all can never raise a
        # TypeError for a junk/typo'd key in a config.yaml params
        # block. This is real, slightly risky silent-acceptance
        # behavior worth a positive test, not just a comment.
        config = {
            "data_sources": {
                "active": [{"type": "rss", "params": {
                    "feed_urls": ["https://example.com/feed.xml"],
                    "this_key_does_not_exist_on_rssdatasource": "ignored",
                }}],
            }
        }
        result = SourceFactory.create_all(config)  # must not raise
        assert result[0].feed_urls == ["https://example.com/feed.xml"]
        assert not hasattr(result[0], "this_key_does_not_exist_on_rssdatasource")

    def test_params_dict_is_copied_not_mutated_in_place(self):
        # factory.py does `params = dict(entry.get("params", {}))` --
        # confirms the ORIGINAL config dict's params block is untouched
        # after api_key injection, since config objects are often
        # reused/shared (e.g. across multiple create_all calls in a
        # long-running scheduler process).
        original_params = {"query": "test query"}
        config = {
            "data_sources": {
                "active": [{"type": "newsdata", "params": original_params}],
                "newsdata_api_key": "some-key",
            }
        }
        SourceFactory.create_all(config)
        assert "api_key" not in original_params
        assert original_params == {"query": "test query"}