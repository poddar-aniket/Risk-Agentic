"""
tests/test_newsdata_source.py

Coverage for app/ingestion/newsdata.py's NewsDataSource.

SCOPE: httpx.get is mocked at the module level inside app.ingestion.newsdata
(not via a real HTTP library like respx/pytest-httpx, to avoid adding new
test dependencies -- consistent with this project's pattern elsewhere of
patching at the class/function level rather than reaching for new
libraries). This file tests NewsDataSource's OWN logic: input validation,
response-to-RawArticle mapping, the paid-plan-content-truncation fallback,
and empty-content skipping. It does NOT test newsdata.io's real API
behavior or response shape -- that's an external-service concern, covered
only insofar as this file's fake response payloads are a reasonable-faith
reconstruction of the real API's documented shape (results[].title,
.content, .description, .link, .pubDate), not a guarantee they're
byte-for-byte accurate.
"""
import pytest
from unittest.mock import MagicMock, patch

from app.ingestion import newsdata as newsdata_module
from app.ingestion.newsdata import NewsDataSource
from app.ingestion.base import RawArticle


def _fake_response(json_data, status_ok=True):
    resp = MagicMock()
    resp.json.return_value = json_data
    if status_ok:
        resp.raise_for_status.return_value = None
    else:
        resp.raise_for_status.side_effect = Exception("HTTP error")
    return resp


class TestNewsDataSourceValidation:
    def test_empty_api_key_raises_before_any_http_call(self):
        source = NewsDataSource(api_key="", query="flood")
        with patch.object(newsdata_module.httpx, "get") as mock_get:
            with pytest.raises(ValueError, match="NEWSDATA_API_KEY is not set"):
                source.fetch_events()
        mock_get.assert_not_called()

    def test_empty_query_raises_before_any_http_call(self):
        source = NewsDataSource(api_key="real-key", query="")
        with patch.object(newsdata_module.httpx, "get") as mock_get:
            with pytest.raises(ValueError, match="requires a non-empty query string"):
                source.fetch_events()
        mock_get.assert_not_called()

    def test_whitespace_only_query_raises(self):
        source = NewsDataSource(api_key="real-key", query="   ")
        with patch.object(newsdata_module.httpx, "get"):
            with pytest.raises(ValueError, match="requires a non-empty query string"):
                source.fetch_events()


class TestNewsDataSourceFetch:
    def test_happy_path_maps_results_to_raw_articles(self):
        source = NewsDataSource(api_key="real-key", query="flood")
        payload = {
            "results": [
                {
                    "title": "Flooding disrupts Chennai port",
                    "content": "Full article content here.",
                    "description": "Short description.",
                    "link": "https://example.com/article1",
                    "pubDate": "2026-06-20 10:00:00",
                }
            ]
        }
        with patch.object(newsdata_module.httpx, "get", return_value=_fake_response(payload)):
            articles = source.fetch_events()

        assert len(articles) == 1
        article = articles[0]
        assert isinstance(article, RawArticle)
        assert article.source == "newsdata.io"
        assert article.title == "Flooding disrupts Chennai port"
        assert article.content == "Full article content here."
        assert article.url == "https://example.com/article1"
        assert article.published_at == "2026-06-20 10:00:00"

    def test_falls_back_to_description_when_content_missing(self):
        source = NewsDataSource(api_key="real-key", query="flood")
        payload = {
            "results": [
                {
                    "title": "Title",
                    "description": "Fallback description text.",
                    "link": "https://example.com/a",
                    "pubDate": "2026-06-20",
                }
            ]
        }
        with patch.object(newsdata_module.httpx, "get", return_value=_fake_response(payload)):
            articles = source.fetch_events()

        assert len(articles) == 1
        assert articles[0].content == "Fallback description text."

    def test_paid_plan_truncated_content_falls_back_to_description(self):
        source = NewsDataSource(api_key="real-key", query="flood")
        payload = {
            "results": [
                {
                    "title": "Title",
                    "content": "ONLY AVAILABLE IN PAID PLANS",
                    "description": "Real usable description.",
                    "link": "https://example.com/a",
                    "pubDate": "2026-06-20",
                }
            ]
        }
        with patch.object(newsdata_module.httpx, "get", return_value=_fake_response(payload)):
            articles = source.fetch_events()

        assert len(articles) == 1
        assert articles[0].content == "Real usable description."

    def test_article_with_no_usable_content_is_skipped(self):
        source = NewsDataSource(api_key="real-key", query="flood")
        payload = {
            "results": [
                {"title": "No content at all", "content": "", "description": "", "link": "https://example.com/a"},
                {"title": "Has content", "content": "Real content", "link": "https://example.com/b"},
            ]
        }
        with patch.object(newsdata_module.httpx, "get", return_value=_fake_response(payload)):
            articles = source.fetch_events()

        assert len(articles) == 1
        assert articles[0].title == "Has content"

    def test_paid_plan_truncation_with_empty_description_is_skipped(self):
        # If content is the paid-plan stub AND description is also
        # empty, there's nothing usable -- should be skipped, not
        # produce an article with the literal stub text or empty content.
        source = NewsDataSource(api_key="real-key", query="flood")
        payload = {
            "results": [
                {"title": "Stub only", "content": "ONLY AVAILABLE IN PAID PLANS", "description": "", "link": "x"},
            ]
        }
        with patch.object(newsdata_module.httpx, "get", return_value=_fake_response(payload)):
            articles = source.fetch_events()

        assert articles == []

    def test_empty_results_returns_empty_list(self):
        source = NewsDataSource(api_key="real-key", query="flood")
        with patch.object(newsdata_module.httpx, "get", return_value=_fake_response({"results": []})):
            articles = source.fetch_events()
        assert articles == []

    def test_missing_results_key_returns_empty_list(self):
        source = NewsDataSource(api_key="real-key", query="flood")
        with patch.object(newsdata_module.httpx, "get", return_value=_fake_response({})):
            articles = source.fetch_events()
        assert articles == []

    def test_http_error_propagates_not_swallowed(self):
        source = NewsDataSource(api_key="real-key", query="flood")
        bad_response = _fake_response({}, status_ok=False)
        with patch.object(newsdata_module.httpx, "get", return_value=bad_response):
            with pytest.raises(Exception, match="HTTP error"):
                source.fetch_events()

    def test_request_params_include_api_key_and_query(self):
        source = NewsDataSource(api_key="my-key", query="port strike")
        with patch.object(newsdata_module.httpx, "get", return_value=_fake_response({"results": []})) as mock_get:
            source.fetch_events()

        _, kwargs = mock_get.call_args
        assert kwargs["params"]["apikey"] == "my-key"
        assert kwargs["params"]["q"] == "port strike"