"""
tests/test_openweather_source.py

Coverage for app/ingestion/openweather.py's OpenWeatherDataSource.
Same mocking approach as test_newsdata_source.py: httpx.get patched at
the module level inside app.ingestion.openweather, no new HTTP-mocking
library dependency.
"""
import pytest
from unittest.mock import MagicMock, patch

from app.ingestion import openweather as openweather_module
from app.ingestion.openweather import OpenWeatherDataSource
from app.ingestion.base import RawArticle


def _fake_response(json_data):
    resp = MagicMock()
    resp.json.return_value = json_data
    resp.raise_for_status.return_value = None
    return resp


class TestOpenWeatherDataSourceValidation:
    def test_empty_api_key_raises_before_any_http_call(self):
        source = OpenWeatherDataSource(api_key="", locations=["Chennai"])
        with patch.object(openweather_module.httpx, "get") as mock_get:
            with pytest.raises(ValueError, match="OPENWEATHER_API_KEY is not set"):
                source.fetch_events()
        mock_get.assert_not_called()

    def test_empty_locations_returns_empty_list_no_http_calls(self):
        source = OpenWeatherDataSource(api_key="real-key", locations=[])
        with patch.object(openweather_module.httpx, "get") as mock_get:
            articles = source.fetch_events()
        assert articles == []
        mock_get.assert_not_called()

    def test_none_locations_defaults_to_empty_list(self):
        # locations=None -> self.locations = [] per the constructor's
        # `locations or []` -- confirms the default itself, not just
        # the fetch_events behavior given an explicit [].
        source = OpenWeatherDataSource(api_key="real-key", locations=None)
        assert source.locations == []


class TestOpenWeatherDataSourceFetch:
    def test_happy_path_single_location(self):
        source = OpenWeatherDataSource(api_key="real-key", locations=["Chennai"])
        payload = {
            "weather": [{"description": "heavy rain"}],
            "main": {"temp": 28.5},
            "wind": {"speed": 4.2},
            "name": "Chennai",
            "sys": {"country": "IN"},
        }
        with patch.object(openweather_module.httpx, "get", return_value=_fake_response(payload)):
            articles = source.fetch_events()

        assert len(articles) == 1
        article = articles[0]
        assert isinstance(article, RawArticle)
        assert article.source == "openweathermap"
        assert article.title == "Weather update: Chennai, IN"
        assert "heavy rain" in article.content
        assert "28.5" in article.content
        assert "4.2" in article.content
        assert article.url is None
        assert article.published_at is None

    def test_multiple_locations_produce_multiple_articles_in_order(self):
        source = OpenWeatherDataSource(api_key="real-key", locations=["Chennai", "Mumbai"])
        chennai_payload = {
            "weather": [{"description": "rain"}], "main": {"temp": 28}, "wind": {"speed": 3},
            "name": "Chennai", "sys": {"country": "IN"},
        }
        mumbai_payload = {
            "weather": [{"description": "clear sky"}], "main": {"temp": 31}, "wind": {"speed": 2},
            "name": "Mumbai", "sys": {"country": "IN"},
        }
        with patch.object(
            openweather_module.httpx, "get",
            side_effect=[_fake_response(chennai_payload), _fake_response(mumbai_payload)],
        ):
            articles = source.fetch_events()

        assert len(articles) == 2
        assert articles[0].title == "Weather update: Chennai, IN"
        assert articles[1].title == "Weather update: Mumbai, IN"

    def test_missing_optional_fields_do_not_crash(self):
        # Minimal payload missing wind, sys, and using fallback name --
        # confirms the .get(..., {})/.get(..., "") chains actually
        # protect against partial responses, not just an assumption
        # that they do.
        source = OpenWeatherDataSource(api_key="real-key", locations=["Unknown City"])
        payload = {"weather": [{}], "main": {}}
        with patch.object(openweather_module.httpx, "get", return_value=_fake_response(payload)):
            articles = source.fetch_events()

        assert len(articles) == 1
        article = articles[0]
        # city falls back to the original location string when "name"
        # is absent from the response
        assert "Unknown City" in article.title
        assert article.content  # should not have raised building the f-string

    def test_completely_empty_response_does_not_crash(self):
        source = OpenWeatherDataSource(api_key="real-key", locations=["Somewhere"])
        with patch.object(openweather_module.httpx, "get", return_value=_fake_response({})):
            articles = source.fetch_events()

        assert len(articles) == 1
        assert "Somewhere" in articles[0].title

    def test_request_params_include_api_key_and_location(self):
        source = OpenWeatherDataSource(api_key="my-key", locations=["Delhi"])
        with patch.object(
            openweather_module.httpx, "get", return_value=_fake_response({})
        ) as mock_get:
            source.fetch_events()

        _, kwargs = mock_get.call_args
        assert kwargs["params"]["appid"] == "my-key"
        assert kwargs["params"]["q"] == "Delhi"