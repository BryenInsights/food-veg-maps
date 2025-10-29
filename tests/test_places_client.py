"""Unit tests for places_client module."""

import json
import logging
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
import pytest
from app.places_client import PlacesClient


@pytest.fixture
def mock_logger():
    """Create a mock logger."""
    return Mock(spec=logging.Logger)


@pytest.fixture
def client(mock_logger):
    """Create a PlacesClient instance with mock logger."""
    return PlacesClient("test_api_key", mock_logger, timeout=5)


def test_client_initialization_success(mock_logger):
    """Test successful client initialization."""
    client = PlacesClient("valid_key", mock_logger)
    assert client.api_key == "valid_key"
    assert client.logger == mock_logger
    assert client.timeout == 10  # default


def test_client_initialization_empty_key(mock_logger):
    """Test that empty API key raises ValueError."""
    with pytest.raises(ValueError, match="API key cannot be empty"):
        PlacesClient("", mock_logger)


def test_text_search_pagination(client, mock_logger):
    """Test text search with pagination handling."""
    # Mock responses with pagination
    mock_response_1 = MagicMock()
    mock_response_1.status_code = 200
    mock_response_1.json.return_value = {
        "status": "OK",
        "results": [
            {"place_id": "place1", "name": "Restaurant 1"},
            {"place_id": "place2", "name": "Restaurant 2"}
        ],
        "next_page_token": "token123"
    }

    mock_response_2 = MagicMock()
    mock_response_2.status_code = 200
    mock_response_2.json.return_value = {
        "status": "OK",
        "results": [
            {"place_id": "place3", "name": "Restaurant 3"}
        ]
    }

    with patch.object(client.session, 'get') as mock_get:
        mock_get.side_effect = [mock_response_1, mock_response_2]

        with patch('time.sleep'):  # Skip actual sleep
            results = client.text_search("restaurants in Paris")

        assert len(results) == 3
        assert results[0]["place_id"] == "place1"
        assert results[2]["place_id"] == "place3"
        assert mock_get.call_count == 2


def test_text_search_max_results(client):
    """Test text search respects max_results parameter."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "status": "OK",
        "results": [
            {"place_id": f"place{i}", "name": f"Restaurant {i}"}
            for i in range(10)
        ],
        "next_page_token": "token123"
    }

    with patch.object(client.session, 'get', return_value=mock_response):
        results = client.text_search("restaurants", max_results=5)

    assert len(results) == 5


def test_nearby_search(client):
    """Test nearby search functionality."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "status": "OK",
        "results": [
            {"place_id": "nearby1", "name": "Nearby Restaurant"}
        ]
    }

    with patch.object(client.session, 'get', return_value=mock_response):
        results = client.nearby_search(48.8566, 2.3522, 1000)

    assert len(results) == 1
    assert results[0]["place_id"] == "nearby1"


def test_place_details_success(client):
    """Test successful place details fetch."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "status": "OK",
        "result": {
            "place_id": "test_id",
            "name": "Test Restaurant",
            "rating": 4.5
        }
    }

    with patch.object(client.session, 'get', return_value=mock_response):
        result = client.place_details("test_id")

    assert result is not None
    assert result["name"] == "Test Restaurant"
    assert result["rating"] == 4.5


def test_place_details_error(client, mock_logger):
    """Test place details with API error."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "status": "NOT_FOUND",
        "error_message": "Place not found"
    }

    with patch.object(client.session, 'get', return_value=mock_response):
        result = client.place_details("invalid_id")

    assert result is None
    mock_logger.warning.assert_called()


def test_download_photo_success(client, tmp_path):
    """Test successful photo download with redirect."""
    photo_path = tmp_path / "test_photo.jpg"
    fake_image_data = b'\xff\xd8\xff\xe0'  # JPEG magic bytes

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = fake_image_data

    with patch.object(client.session, 'get', return_value=mock_response):
        success = client.download_photo("photo_ref_123", photo_path)

    assert success is True
    assert photo_path.exists()
    assert photo_path.read_bytes() == fake_image_data


def test_download_photo_failure(client, tmp_path, mock_logger):
    """Test photo download with network error."""
    import requests
    photo_path = tmp_path / "test_photo.jpg"

    with patch.object(client.session, 'get', side_effect=requests.exceptions.RequestException("Network error")):
        success = client.download_photo("photo_ref_123", photo_path)

    assert success is False
    assert not photo_path.exists()
    mock_logger.warning.assert_called()


def test_zero_results(client, mock_logger):
    """Test handling of zero results."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "status": "ZERO_RESULTS",
        "results": []
    }

    with patch.object(client.session, 'get', return_value=mock_response):
        results = client.text_search("nonexistent place")

    assert len(results) == 0
    mock_logger.warning.assert_called()
