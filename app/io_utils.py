"""I/O utilities for logging, file writing, and path management."""

import csv
import json
import logging
from pathlib import Path
from typing import Any, List, Dict
from datetime import datetime


def setup_logging(log_dir: Path, log_level: int = logging.INFO) -> logging.Logger:
    """
    Set up logging with both file and console handlers.

    Args:
        log_dir: Directory where log files will be stored
        log_level: Logging level (default: INFO)

    Returns:
        Configured logger instance
    """
    log_dir.mkdir(parents=True, exist_ok=True)

    # Create logger
    logger = logging.getLogger("places_collector")
    logger.setLevel(log_level)

    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()

    # File handler
    log_file = log_dir / f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(log_level)
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    file_handler.setFormatter(file_formatter)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)  # Only warnings and errors to console
    console_formatter = logging.Formatter('%(levelname)s - %(message)s')
    console_handler.setFormatter(console_formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    logger.info(f"Logging initialized. Log file: {log_file}")
    return logger


def ensure_dir(path: Path) -> Path:
    """
    Ensure directory exists, creating it if necessary.

    Args:
        path: Directory path

    Returns:
        The path (for chaining)
    """
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_json(data: List[Dict[str, Any]], output_path: Path, logger: logging.Logger) -> None:
    """
    Write data to JSON file with pretty printing.

    Args:
        data: List of dictionaries to write
        output_path: Path to output JSON file
        logger: Logger instance
    """
    try:
        ensure_dir(output_path.parent)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.info(f"Wrote {len(data)} records to {output_path}")
    except Exception as e:
        logger.error(f"Error writing JSON to {output_path}: {e}")
        raise


def write_csv(data: List[Dict[str, Any]], output_path: Path, logger: logging.Logger) -> None:
    """
    Write data to CSV file with proper escaping of JSON fields.

    Args:
        data: List of dictionaries to write
        output_path: Path to output CSV file
        logger: Logger instance
    """
    if not data:
        logger.warning("No data to write to CSV")
        return

    try:
        ensure_dir(output_path.parent)

        # Define CSV columns
        fieldnames = [
            'place_id',
            'name',
            'lat',
            'lng',
            'formatted_address',
            'rating',
            'user_ratings_total',
            'website',
            'opening_hours_json',
            'photo_local_paths_json',
            'menu_urls_json',
            'source_timestamp'
        ]

        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for record in data:
                # Convert nested structures to JSON strings
                csv_record = {
                    'place_id': record.get('place_id', ''),
                    'name': record.get('name', ''),
                    'lat': record.get('lat', ''),
                    'lng': record.get('lng', ''),
                    'formatted_address': record.get('formatted_address', ''),
                    'rating': record.get('rating', ''),
                    'user_ratings_total': record.get('user_ratings_total', ''),
                    'website': record.get('website', ''),
                    'opening_hours_json': json.dumps(record.get('opening_hours', {})),
                    'photo_local_paths_json': json.dumps(record.get('photo_local_paths', [])),
                    'menu_urls_json': json.dumps(record.get('menu_urls', [])),
                    'source_timestamp': record.get('source_timestamp', '')
                }
                writer.writerow(csv_record)

        logger.info(f"Wrote {len(data)} records to {output_path}")
    except Exception as e:
        logger.error(f"Error writing CSV to {output_path}: {e}")
        raise


def get_photo_filename(place_id: str, photo_index: int) -> str:
    """
    Generate deterministic photo filename.

    Args:
        place_id: Google Places ID
        photo_index: Index of photo (0-based)

    Returns:
        Filename string (e.g., "p0.jpg")
    """
    return f"p{photo_index}.jpg"


def get_photo_dir(base_dir: Path, place_id: str) -> Path:
    """
    Get photo directory for a specific place.

    Args:
        base_dir: Base photos directory
        place_id: Google Places ID

    Returns:
        Path to place-specific photo directory
    """
    photo_dir = base_dir / place_id
    ensure_dir(photo_dir)
    return photo_dir


def photo_exists(base_dir: Path, place_id: str, photo_index: int) -> bool:
    """
    Check if a photo already exists (for idempotency).

    Args:
        base_dir: Base photos directory
        place_id: Google Places ID
        photo_index: Index of photo

    Returns:
        True if photo exists
    """
    photo_path = get_photo_dir(base_dir, place_id) / get_photo_filename(place_id, photo_index)
    return photo_path.exists()
