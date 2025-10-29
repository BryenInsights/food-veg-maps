"""Google Places API client with pagination, retry logic, and photo downloads."""

import time
import logging
from typing import Dict, List, Optional, Any
from pathlib import Path
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class PlacesClient:
    """Client for interacting with Google Places API."""

    BASE_URL = "https://maps.googleapis.com/maps/api/place"

    def __init__(
        self,
        api_key: str,
        logger: logging.Logger,
        timeout: int = 10,
        retry_attempts: int = 3
    ):
        """
        Initialize Places API client.

        Args:
            api_key: Google Maps API key
            logger: Logger instance
            timeout: HTTP request timeout in seconds
            retry_attempts: Number of retry attempts for transient errors

        Raises:
            ValueError: If API key is empty
        """
        if not api_key:
            raise ValueError("API key cannot be empty")

        self.api_key = api_key
        self.logger = logger
        self.timeout = timeout

        # Configure session with retry logic
        self.session = requests.Session()
        retry_strategy = Retry(
            total=retry_attempts,
            backoff_factor=1,  # Exponential backoff: 1s, 2s, 4s...
            status_forcelist=[500, 502, 503, 504],  # Retry on server errors
            allowed_methods=["GET", "POST"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

    def text_search(
        self,
        query: str,
        max_results: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Perform text search for places.

        Args:
            query: Search query (e.g., "restaurants in Paris")
            max_results: Maximum number of results to return (None for all)

        Returns:
            List of place dictionaries with basic information
        """
        url = f"{self.BASE_URL}/textsearch/json"
        results = []
        next_page_token = None

        while True:
            params = {
                "query": query,
                "key": self.api_key
            }

            if next_page_token:
                params["pagetoken"] = next_page_token
                # Required delay before using next_page_token
                time.sleep(2)

            try:
                self.logger.debug(f"Text search request: {query}")
                response = self.session.get(url, params=params, timeout=self.timeout)
                response.raise_for_status()
                data = response.json()

                status = data.get("status")
                if status == "OK":
                    places = data.get("results", [])
                    results.extend(places)
                    self.logger.info(f"Retrieved {len(places)} places (total: {len(results)})")

                    next_page_token = data.get("next_page_token")

                    # Check if we've reached max_results
                    if max_results and len(results) >= max_results:
                        self.logger.info(f"Reached max_results limit: {max_results}")
                        return results[:max_results]

                    # Continue pagination if token exists
                    if not next_page_token:
                        break
                elif status == "ZERO_RESULTS":
                    self.logger.warning("No results found for query")
                    break
                else:
                    error_msg = data.get("error_message", "Unknown error")
                    self.logger.error(f"API error: {status} - {error_msg}")
                    break

            except requests.exceptions.RequestException as e:
                self.logger.error(f"Request error during text search: {e}")
                break

            # Small delay between requests
            time.sleep(0.1)

        return results

    def nearby_search(
        self,
        lat: float,
        lng: float,
        radius: int,
        place_type: str = "restaurant",
        max_results: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Perform nearby search for places.

        Args:
            lat: Latitude
            lng: Longitude
            radius: Search radius in meters
            place_type: Type of place to search for
            max_results: Maximum number of results to return (None for all)

        Returns:
            List of place dictionaries with basic information
        """
        url = f"{self.BASE_URL}/nearbysearch/json"
        results = []
        next_page_token = None

        while True:
            params = {
                "location": f"{lat},{lng}",
                "radius": radius,
                "type": place_type,
                "key": self.api_key
            }

            if next_page_token:
                params["pagetoken"] = next_page_token
                # Required delay before using next_page_token
                time.sleep(2)

            try:
                self.logger.debug(f"Nearby search: lat={lat}, lng={lng}, radius={radius}")
                response = self.session.get(url, params=params, timeout=self.timeout)
                response.raise_for_status()
                data = response.json()

                status = data.get("status")
                if status == "OK":
                    places = data.get("results", [])
                    results.extend(places)
                    self.logger.info(f"Retrieved {len(places)} places (total: {len(results)})")

                    next_page_token = data.get("next_page_token")

                    # Check if we've reached max_results
                    if max_results and len(results) >= max_results:
                        self.logger.info(f"Reached max_results limit: {max_results}")
                        return results[:max_results]

                    # Continue pagination if token exists
                    if not next_page_token:
                        break
                elif status == "ZERO_RESULTS":
                    self.logger.warning("No results found in this area")
                    break
                else:
                    error_msg = data.get("error_message", "Unknown error")
                    self.logger.error(f"API error: {status} - {error_msg}")
                    break

            except requests.exceptions.RequestException as e:
                self.logger.error(f"Request error during nearby search: {e}")
                break

            # Small delay between requests
            time.sleep(0.1)

        return results

    def place_details(self, place_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a place.

        Args:
            place_id: Google Places ID

        Returns:
            Dictionary with place details or None on error
        """
        url = f"{self.BASE_URL}/details/json"
        params = {
            "place_id": place_id,
            "fields": "place_id,name,formatted_address,geometry/location,rating,"
                     "user_ratings_total,opening_hours,website,photos",
            "key": self.api_key
        }

        try:
            self.logger.debug(f"Fetching details for place_id: {place_id}")
            response = self.session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()

            if data.get("status") == "OK":
                return data.get("result")
            else:
                error_msg = data.get("error_message", "Unknown error")
                self.logger.warning(f"Place details error for {place_id}: {error_msg}")
                return None

        except requests.exceptions.RequestException as e:
            self.logger.error(f"Request error fetching details for {place_id}: {e}")
            return None

    def download_photo(
        self,
        photo_reference: str,
        output_path: Path,
        max_width: int = 1600
    ) -> bool:
        """
        Download a photo from Google Places.

        Args:
            photo_reference: Photo reference from place details
            output_path: Path where photo will be saved
            max_width: Maximum width of photo in pixels

        Returns:
            True if download successful, False otherwise
        """
        url = f"{self.BASE_URL}/photo"
        params = {
            "photoreference": photo_reference,
            "maxwidth": max_width,
            "key": self.api_key
        }

        try:
            self.logger.debug(f"Downloading photo to {output_path}")
            # Follow redirects to get actual image
            response = self.session.get(
                url,
                params=params,
                timeout=self.timeout,
                allow_redirects=True
            )
            response.raise_for_status()

            # Save photo
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'wb') as f:
                f.write(response.content)

            self.logger.debug(f"Photo saved: {output_path}")
            return True

        except requests.exceptions.RequestException as e:
            self.logger.warning(f"Failed to download photo: {e}")
            return False
        except IOError as e:
            self.logger.error(f"Failed to save photo to {output_path}: {e}")
            return False

    def close(self):
        """Close the session."""
        self.session.close()
