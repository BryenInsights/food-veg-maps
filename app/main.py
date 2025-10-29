"""
Main CLI application for Google Places restaurant data collector.

Usage examples:
    # Text search
    python -m app.main --text "restaurants in Paris" --max-places 300

    # Nearby search
    python -m app.main --nearby --lat 48.8566 --lng 2.3522 --radius 2000

    # With website crawling
    python -m app.main --text "restaurants in Paris" --crawl-website
"""

import argparse
import os
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
from dotenv import load_dotenv
from tqdm import tqdm

from app.places_client import PlacesClient
from app.crawler import WebsiteCrawler
from app.menu_detector import MenuDetector
from app.io_utils import (
    setup_logging,
    ensure_dir,
    write_json,
    write_csv,
    get_photo_dir,
    get_photo_filename,
    photo_exists
)
import re
import shutil


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Google Places restaurant data collector with menu photo downloads",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Text search for restaurants in Paris
  python -m app.main --text "restaurants in Paris" --max-places 300

  # Nearby search with coordinates
  python -m app.main --nearby --lat 48.8566 --lng 2.3522 --radius 2000

  # With website crawling enabled
  python -m app.main --text "restaurants in Tokyo" --crawl-website --photos-per-place 5
        """
    )

    # Search mode
    search_group = parser.add_mutually_exclusive_group(required=True)
    search_group.add_argument(
        '--text',
        type=str,
        help='Text search query (e.g., "restaurants in Paris")'
    )
    search_group.add_argument(
        '--nearby',
        action='store_true',
        help='Use nearby search (requires --lat, --lng, --radius)'
    )

    # Nearby search parameters
    parser.add_argument('--lat', type=float, help='Latitude for nearby search')
    parser.add_argument('--lng', type=float, help='Longitude for nearby search')
    parser.add_argument('--radius', type=int, default=1000, help='Search radius in meters (default: 1000)')

    # General parameters
    parser.add_argument(
        '--max-places',
        type=int,
        default=50,
        help='Maximum number of places to process (default: 50)'
    )
    parser.add_argument(
        '--photos-per-place',
        type=int,
        default=3,
        help='Maximum photos to download per place (default: 3, 0 = all available)'
    )
    parser.add_argument(
        '--detect-menus',
        action='store_true',
        help='Analyze photos to detect which ones are menus'
    )
    parser.add_argument(
        '--outdir',
        type=str,
        default='./out',
        help='Output directory (default: ./out)'
    )

    # Website crawling
    parser.add_argument(
        '--crawl-website',
        action='store_true',
        help='Enable website crawling for menu URLs'
    )
    parser.add_argument(
        '--rate-limit',
        type=float,
        default=8.0,
        help='Rate limit for website crawling in QPS (default: 8)'
    )

    # HTTP settings
    parser.add_argument(
        '--user-agent',
        type=str,
        default='RestaurantDataCollector/1.0',
        help='User agent for HTTP requests'
    )
    parser.add_argument(
        '--timeout',
        type=int,
        default=10,
        help='HTTP request timeout in seconds (default: 10)'
    )

    # Logging
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )

    args = parser.parse_args()

    # Validate nearby search parameters
    if args.nearby:
        if args.lat is None or args.lng is None:
            parser.error('--nearby requires --lat and --lng')
        if not -90 <= args.lat <= 90:
            parser.error('--lat must be between -90 and 90')
        if not -180 <= args.lng <= 180:
            parser.error('--lng must be between -180 and 180')

    return args


def sanitize_folder_name(name: str) -> str:
    """
    Sanitize a name for use as a folder name.

    Args:
        name: The name to sanitize

    Returns:
        Sanitized folder name
    """
    # Remove or replace invalid characters
    name = re.sub(r'[<>:"/\\|?*]', '', name)
    # Replace spaces and special chars with underscores
    name = re.sub(r'[\s\-]+', '_', name)
    # Remove leading/trailing underscores and dots
    name = name.strip('_.')
    # Limit length
    name = name[:100]
    return name or 'unknown'


def enrich_place_data(
    place: Dict[str, Any],
    client: PlacesClient,
    crawler: WebsiteCrawler,
    menu_detector: MenuDetector,
    args: argparse.Namespace,
    outdir: Path
) -> Dict[str, Any]:
    """
    Enrich basic place data with details, photos, and menu URLs.
    Creates a folder structure: [restaurant_name]/photos/{menus,photos}/information/

    Args:
        place: Basic place information from search
        client: PlacesClient instance
        crawler: WebsiteCrawler instance
        menu_detector: MenuDetector instance
        args: Command line arguments
        outdir: Base output directory

    Returns:
        Enriched place data dictionary
    """
    place_id = place.get('place_id')
    if not place_id:
        return None

    # Get place details
    details = client.place_details(place_id)
    if not details:
        return None

    # Extract location
    geometry = details.get('geometry', {})
    location = geometry.get('location', {})

    # Build enriched record
    name = details.get('name', '')
    record = {
        'place_id': place_id,
        'name': name,
        'lat': location.get('lat', 0.0),
        'lng': location.get('lng', 0.0),
        'formatted_address': details.get('formatted_address', ''),
        'rating': details.get('rating'),
        'user_ratings_total': details.get('user_ratings_total'),
        'website': details.get('website', ''),
        'opening_hours': details.get('opening_hours', {}),
        'photo_local_paths': [],
        'menu_photo_paths': [],
        'menu_urls': [],
        'source_timestamp': datetime.utcnow().isoformat() + 'Z'
    }

    # Create restaurant folder structure
    folder_name = sanitize_folder_name(name) if name else place_id
    restaurant_dir = outdir / folder_name

    # Create subdirectories
    photos_all_dir = restaurant_dir / 'photos' / 'photos'
    photos_menus_dir = restaurant_dir / 'photos' / 'menus'
    info_dir = restaurant_dir / 'information'

    ensure_dir(photos_all_dir)
    ensure_dir(photos_menus_dir)
    ensure_dir(info_dir)

    # Download photos
    photos = details.get('photos', [])
    if photos:
        # If photos_per_place is 0, download all available
        if args.photos_per_place == 0:
            max_photos = len(photos)
        else:
            max_photos = min(len(photos), args.photos_per_place)

        for i in range(max_photos):
            photo_ref = photos[i].get('photo_reference')
            if photo_ref:
                photo_filename = get_photo_filename(place_id, i)
                photo_path = photos_all_dir / photo_filename

                # Download to the photos/photos/ subfolder
                if client.download_photo(photo_ref, photo_path):
                    relative_path = f"{folder_name}/photos/photos/{photo_filename}"
                    record['photo_local_paths'].append(relative_path)

        # Detect menu photos if requested
        if args.detect_menus and record['photo_local_paths']:
            # Get absolute paths for detection
            photo_paths = [photos_all_dir / Path(p).name for p in record['photo_local_paths']]
            menu_photos = menu_detector.filter_menu_photos(photo_paths)

            # Copy detected menus to photos/menus/ subfolder
            for menu_photo in menu_photos:
                dest_path = photos_menus_dir / menu_photo.name
                shutil.copy2(menu_photo, dest_path)
                relative_path = f"{folder_name}/photos/menus/{menu_photo.name}"
                record['menu_photo_paths'].append(relative_path)

    # Crawl website for menu URLs
    if args.crawl_website and record['website']:
        menu_urls = crawler.crawl_for_menus(record['website'])
        record['menu_urls'] = menu_urls

    # Save individual restaurant JSON file
    restaurant_json_path = info_dir / 'data.json'
    write_json([record], restaurant_json_path, client.logger if hasattr(client, 'logger') else None)

    return record


def main():
    """Main application entry point."""
    # Load environment variables
    load_dotenv()

    # Parse arguments
    args = parse_args()

    # Setup paths
    outdir = Path(args.outdir)
    ensure_dir(outdir)
    logs_dir = outdir / 'logs'

    # Setup logging
    log_level = 'DEBUG' if args.verbose else 'INFO'
    import logging
    logger = setup_logging(logs_dir, getattr(logging, log_level))

    logger.info("=" * 60)
    logger.info("Google Places Restaurant Data Collector")
    logger.info("=" * 60)

    # Get API key
    api_key = os.getenv('GOOGLE_MAPS_API_KEY')
    if not api_key:
        logger.error("GOOGLE_MAPS_API_KEY not found in environment variables")
        logger.error("Please set it in .env file or environment")
        sys.exit(1)

    logger.info(f"API key loaded: {api_key[:10]}...")
    logger.info(f"Output directory: {outdir.absolute()}")
    logger.info(f"Max places: {args.max_places}")
    if args.photos_per_place == 0:
        logger.info(f"Photos per place: all available")
    else:
        logger.info(f"Photos per place: {args.photos_per_place}")
    logger.info(f"Menu detection: {'enabled' if args.detect_menus else 'disabled'}")
    logger.info(f"Website crawling: {'enabled' if args.crawl_website else 'disabled'}")

    try:
        # Initialize clients
        client = PlacesClient(api_key, logger, timeout=args.timeout)
        crawler = WebsiteCrawler(
            logger,
            user_agent=args.user_agent,
            timeout=args.timeout,
            rate_limit_qps=args.rate_limit
        ) if args.crawl_website else None
        menu_detector = MenuDetector(logger) if args.detect_menus else None

        # Perform search
        logger.info("Starting place search...")
        if args.text:
            logger.info(f"Text search: {args.text}")
            places = client.text_search(args.text, max_results=args.max_places)
        else:  # nearby search
            logger.info(f"Nearby search: lat={args.lat}, lng={args.lng}, radius={args.radius}")
            places = client.nearby_search(
                args.lat,
                args.lng,
                args.radius,
                max_results=args.max_places
            )

        if not places:
            logger.warning("No places found")
            sys.exit(0)

        logger.info(f"Found {len(places)} places")

        # Sort by place_id for determinism
        places.sort(key=lambda p: p.get('place_id', ''))

        # Enrich place data with progress bar
        logger.info("Enriching place data...")
        enriched_data: List[Dict[str, Any]] = []

        with tqdm(total=len(places), desc="Processing places", unit="place") as pbar:
            for place in places:
                try:
                    record = enrich_place_data(place, client, crawler, menu_detector, args, outdir)
                    if record:
                        enriched_data.append(record)
                except Exception as e:
                    place_name = place.get('name', 'Unknown')
                    logger.warning(f"Failed to enrich {place_name}: {e}")
                finally:
                    pbar.update(1)

        logger.info(f"Successfully enriched {len(enriched_data)} places")

        # Write outputs
        logger.info("Writing outputs...")

        json_path = outdir / 'places.json'
        write_json(enriched_data, json_path, logger)

        csv_path = outdir / 'places.csv'
        write_csv(enriched_data, csv_path, logger)

        logger.info("=" * 60)
        logger.info("Collection complete!")
        logger.info(f"JSON output: {json_path.absolute()}")
        logger.info(f"CSV output: {csv_path.absolute()}")
        logger.info(f"Output directory: {outdir.absolute()}")
        logger.info(f"Total places: {len(enriched_data)}")

        # Statistics
        total_photos = sum(len(p.get('photo_local_paths', [])) for p in enriched_data)
        logger.info(f"Total photos downloaded: {total_photos}")

        if args.detect_menus:
            total_menu_photos = sum(len(p.get('menu_photo_paths', [])) for p in enriched_data)
            places_with_menu_photos = sum(1 for p in enriched_data if p.get('menu_photo_paths'))
            logger.info(f"Menu photos detected: {total_menu_photos}/{total_photos}")
            logger.info(f"Places with menu photos: {places_with_menu_photos}")

        if args.crawl_website:
            total_menu_urls = sum(len(p.get('menu_urls', [])) for p in enriched_data)
            places_with_menus = sum(1 for p in enriched_data if p.get('menu_urls'))
            logger.info(f"Total menu URLs found: {total_menu_urls}")
            logger.info(f"Places with menu URLs: {places_with_menus}")

        logger.info("=" * 60)

    except KeyboardInterrupt:
        logger.warning("Interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
    finally:
        # Cleanup
        if client:
            client.close()
        if crawler:
            crawler.close()


if __name__ == '__main__':
    main()
