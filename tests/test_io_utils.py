"""Unit tests for io_utils module."""

import json
import csv
import logging
from pathlib import Path
import pytest
from app.io_utils import (
    setup_logging,
    ensure_dir,
    write_json,
    write_csv,
    get_photo_filename,
    get_photo_dir,
    photo_exists
)


def test_ensure_dir(tmp_path):
    """Test directory creation."""
    test_dir = tmp_path / "test" / "nested" / "dir"
    result = ensure_dir(test_dir)

    assert test_dir.exists()
    assert test_dir.is_dir()
    assert result == test_dir


def test_ensure_dir_idempotent(tmp_path):
    """Test that ensure_dir is idempotent."""
    test_dir = tmp_path / "test"
    ensure_dir(test_dir)
    ensure_dir(test_dir)  # Should not raise

    assert test_dir.exists()


def test_setup_logging(tmp_path):
    """Test logging setup."""
    log_dir = tmp_path / "logs"
    logger = setup_logging(log_dir, logging.INFO)

    assert logger is not None
    assert log_dir.exists()
    assert len(logger.handlers) == 2  # File and console

    # Check log file was created
    log_files = list(log_dir.glob("run_*.log"))
    assert len(log_files) == 1


def test_write_json(tmp_path):
    """Test JSON writing."""
    output_path = tmp_path / "test.json"
    test_data = [
        {"id": 1, "name": "Restaurant 1"},
        {"id": 2, "name": "Restaurant 2"}
    ]

    logger = logging.getLogger("test")
    write_json(test_data, output_path, logger)

    assert output_path.exists()

    # Verify content
    with open(output_path, 'r') as f:
        loaded = json.load(f)

    assert loaded == test_data
    assert len(loaded) == 2


def test_write_json_with_unicode(tmp_path):
    """Test JSON writing with Unicode characters."""
    output_path = tmp_path / "test_unicode.json"
    test_data = [
        {"name": "Café Paris", "description": "Crêpes et café"},
        {"name": "东京寿司", "description": "日本料理"}
    ]

    logger = logging.getLogger("test")
    write_json(test_data, output_path, logger)

    with open(output_path, 'r', encoding='utf-8') as f:
        loaded = json.load(f)

    assert loaded[0]["name"] == "Café Paris"
    assert loaded[1]["name"] == "东京寿司"


def test_write_csv(tmp_path):
    """Test CSV writing."""
    output_path = tmp_path / "test.csv"
    test_data = [
        {
            "place_id": "id1",
            "name": "Restaurant 1",
            "lat": 48.8566,
            "lng": 2.3522,
            "formatted_address": "Paris, France",
            "rating": 4.5,
            "user_ratings_total": 100,
            "website": "https://example.com",
            "opening_hours": {"open_now": True},
            "photo_local_paths": ["photo1.jpg", "photo2.jpg"],
            "menu_urls": ["https://example.com/menu"],
            "source_timestamp": "2024-01-01T00:00:00Z"
        }
    ]

    logger = logging.getLogger("test")
    write_csv(test_data, output_path, logger)

    assert output_path.exists()

    # Verify content
    with open(output_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    assert len(rows) == 1
    assert rows[0]["place_id"] == "id1"
    assert rows[0]["name"] == "Restaurant 1"
    assert float(rows[0]["lat"]) == 48.8566

    # Verify JSON fields are properly serialized
    photo_paths = json.loads(rows[0]["photo_local_paths_json"])
    assert len(photo_paths) == 2

    menu_urls = json.loads(rows[0]["menu_urls_json"])
    assert len(menu_urls) == 1


def test_write_csv_empty(tmp_path):
    """Test CSV writing with empty data."""
    output_path = tmp_path / "empty.csv"
    logger = logging.getLogger("test")

    write_csv([], output_path, logger)

    # Should not create file for empty data
    # Or create empty file - both are acceptable
    # Just verify no exception is raised


def test_get_photo_filename():
    """Test photo filename generation."""
    filename = get_photo_filename("place_123", 0)
    assert filename == "p0.jpg"

    filename = get_photo_filename("place_123", 5)
    assert filename == "p5.jpg"


def test_get_photo_dir(tmp_path):
    """Test photo directory creation."""
    base_dir = tmp_path / "photos"
    place_id = "test_place_123"

    photo_dir = get_photo_dir(base_dir, place_id)

    assert photo_dir.exists()
    assert photo_dir.is_dir()
    assert photo_dir == base_dir / place_id


def test_photo_exists(tmp_path):
    """Test photo existence check."""
    base_dir = tmp_path / "photos"
    place_id = "test_place"

    # Create photo directory and file
    photo_dir = get_photo_dir(base_dir, place_id)
    photo_file = photo_dir / get_photo_filename(place_id, 0)
    photo_file.write_bytes(b"fake image data")

    # Check existence
    assert photo_exists(base_dir, place_id, 0) is True
    assert photo_exists(base_dir, place_id, 1) is False
    assert photo_exists(base_dir, "other_place", 0) is False


def test_write_json_creates_parent_dirs(tmp_path):
    """Test that write_json creates parent directories."""
    output_path = tmp_path / "nested" / "dir" / "test.json"
    test_data = [{"id": 1}]

    logger = logging.getLogger("test")
    write_json(test_data, output_path, logger)

    assert output_path.exists()
    assert output_path.parent.exists()


def test_write_csv_with_special_characters(tmp_path):
    """Test CSV writing with special characters that need escaping."""
    output_path = tmp_path / "special.csv"
    test_data = [
        {
            "place_id": "id1",
            "name": 'Restaurant "The Best"',
            "lat": 48.8566,
            "lng": 2.3522,
            "formatted_address": "123 Main St, Paris, France",
            "rating": 4.5,
            "user_ratings_total": 100,
            "website": "https://example.com",
            "opening_hours": {},
            "photo_local_paths": [],
            "menu_urls": [],
            "source_timestamp": "2024-01-01T00:00:00Z"
        }
    ]

    logger = logging.getLogger("test")
    write_csv(test_data, output_path, logger)

    # Verify it can be read back
    with open(output_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    assert rows[0]["name"] == 'Restaurant "The Best"'
