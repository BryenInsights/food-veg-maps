"""Website crawler for detecting menu URLs and PDFs."""

import re
import time
import logging
from typing import Set, List, Optional
from urllib.parse import urljoin, urlparse, urlunparse
from html.parser import HTMLParser
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class RobotsTxtParser:
    """Simple robots.txt parser."""

    def __init__(self, robots_content: str, user_agent: str):
        """
        Initialize robots.txt parser.

        Args:
            robots_content: Content of robots.txt file
            user_agent: User agent string to check rules for
        """
        self.disallowed_paths: Set[str] = set()
        self._parse(robots_content, user_agent)

    def _parse(self, content: str, user_agent: str):
        """Parse robots.txt content."""
        current_ua = None
        applies_to_us = False

        for line in content.split('\n'):
            line = line.strip()
            if not line or line.startswith('#'):
                continue

            if line.lower().startswith('user-agent:'):
                ua = line.split(':', 1)[1].strip().lower()
                applies_to_us = (ua == '*' or user_agent.lower() in ua)
                current_ua = ua
            elif applies_to_us and line.lower().startswith('disallow:'):
                path = line.split(':', 1)[1].strip()
                if path:
                    self.disallowed_paths.add(path)

    def is_allowed(self, path: str) -> bool:
        """Check if path is allowed by robots.txt."""
        for disallowed in self.disallowed_paths:
            if path.startswith(disallowed):
                return False
        return True


class LinkExtractor(HTMLParser):
    """HTML parser to extract links and image sources."""

    def __init__(self):
        super().__init__()
        self.links: Set[str] = set()

    def handle_starttag(self, tag: str, attrs: List[tuple]):
        """Extract href from <a> tags and src from <img> tags."""
        if tag == 'a':
            for attr, value in attrs:
                if attr == 'href' and value:
                    self.links.add(value)
        elif tag == 'img':
            for attr, value in attrs:
                if attr == 'src' and value:
                    self.links.add(value)


class WebsiteCrawler:
    """Crawler for detecting menu URLs and PDFs on restaurant websites."""

    MENU_KEYWORDS = ['menu', 'carte', 'la-carte', 'food', 'menus']

    def __init__(
        self,
        logger: logging.Logger,
        user_agent: str = "RestaurantDataCollector/1.0",
        timeout: int = 10,
        rate_limit_qps: float = 8.0
    ):
        """
        Initialize website crawler.

        Args:
            logger: Logger instance
            user_agent: User agent string for HTTP requests
            timeout: Request timeout in seconds
            rate_limit_qps: Maximum queries per second
        """
        self.logger = logger
        self.user_agent = user_agent
        self.timeout = timeout
        self.min_delay = 1.0 / rate_limit_qps if rate_limit_qps > 0 else 0
        self.last_request_time = 0.0

        # Configure session
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': self.user_agent})

        # Add retry logic
        retry_strategy = Retry(
            total=2,
            backoff_factor=0.5,
            status_forcelist=[500, 502, 503, 504],
            allowed_methods=["GET", "HEAD"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

    def _rate_limit(self):
        """Apply rate limiting between requests."""
        if self.min_delay > 0:
            elapsed = time.time() - self.last_request_time
            if elapsed < self.min_delay:
                time.sleep(self.min_delay - elapsed)
        self.last_request_time = time.time()

    def _fetch_robots_txt(self, base_url: str) -> Optional[RobotsTxtParser]:
        """
        Fetch and parse robots.txt.

        Args:
            base_url: Base URL of website

        Returns:
            RobotsTxtParser instance or None if not found/error
        """
        robots_url = urljoin(base_url, '/robots.txt')
        try:
            self._rate_limit()
            response = self.session.get(robots_url, timeout=self.timeout)
            if response.status_code == 200:
                return RobotsTxtParser(response.text, self.user_agent)
            elif response.status_code == 404:
                # No robots.txt means everything is allowed
                return RobotsTxtParser("", self.user_agent)
            else:
                self.logger.warning(f"robots.txt returned status {response.status_code}")
                return None
        except requests.exceptions.RequestException as e:
            self.logger.warning(f"Failed to fetch robots.txt: {e}")
            return None

    def _normalize_url(self, url: str) -> str:
        """
        Normalize URL by removing fragments and normalizing scheme.

        Args:
            url: URL to normalize

        Returns:
            Normalized URL
        """
        parsed = urlparse(url)
        # Remove fragment
        normalized = urlunparse((
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            parsed.query,
            ''  # Remove fragment
        ))
        return normalized

    def _is_same_domain(self, url1: str, url2: str) -> bool:
        """Check if two URLs belong to the same domain."""
        domain1 = urlparse(url1).netloc.lower()
        domain2 = urlparse(url2).netloc.lower()
        # Remove 'www.' prefix for comparison
        domain1 = domain1.replace('www.', '')
        domain2 = domain2.replace('www.', '')
        return domain1 == domain2

    def _is_menu_url(self, url: str) -> bool:
        """
        Check if URL likely contains menu information.

        Args:
            url: URL to check

        Returns:
            True if URL matches menu patterns
        """
        url_lower = url.lower()

        # Check for PDF extension
        if url_lower.endswith('.pdf'):
            return True

        # Check for menu keywords in path
        for keyword in self.MENU_KEYWORDS:
            if keyword in url_lower:
                return True

        return False

    def _verify_pdf(self, url: str) -> bool:
        """
        Verify if URL points to a PDF via HEAD request.

        Args:
            url: URL to check

        Returns:
            True if content-type indicates PDF
        """
        try:
            self._rate_limit()
            response = self.session.head(url, timeout=self.timeout, allow_redirects=True)
            content_type = response.headers.get('Content-Type', '').lower()
            return 'application/pdf' in content_type
        except requests.exceptions.RequestException as e:
            self.logger.debug(f"PDF verification failed for {url}: {e}")
            return False

    def crawl_for_menus(
        self,
        website_url: str,
        max_pages: int = 10
    ) -> List[str]:
        """
        Crawl website to find menu URLs and PDFs.

        Args:
            website_url: Starting URL (restaurant website)
            max_pages: Maximum number of pages to crawl

        Returns:
            List of menu URLs found
        """
        if not website_url:
            return []

        try:
            parsed = urlparse(website_url)
            if not parsed.scheme:
                website_url = 'https://' + website_url
                parsed = urlparse(website_url)

            base_url = f"{parsed.scheme}://{parsed.netloc}"

            self.logger.debug(f"Starting crawl of {website_url}")

            # Check robots.txt
            robots = self._fetch_robots_txt(base_url)
            if robots is None:
                self.logger.warning(f"Could not access robots.txt, skipping {website_url}")
                return []

            # Track visited URLs and menu URLs
            visited: Set[str] = set()
            to_visit: List[str] = [website_url]
            menu_urls: Set[str] = set()

            while to_visit and len(visited) < max_pages:
                current_url = to_visit.pop(0)
                normalized_url = self._normalize_url(current_url)

                if normalized_url in visited:
                    continue

                visited.add(normalized_url)

                # Check robots.txt
                path = urlparse(normalized_url).path
                if not robots.is_allowed(path):
                    self.logger.debug(f"Blocked by robots.txt: {normalized_url}")
                    continue

                # Fetch page
                try:
                    self._rate_limit()
                    response = self.session.get(
                        normalized_url,
                        timeout=self.timeout,
                        allow_redirects=True
                    )
                    response.raise_for_status()

                    # Check if this URL itself is a menu URL
                    if self._is_menu_url(normalized_url):
                        menu_urls.add(normalized_url)

                    # Only parse HTML
                    content_type = response.headers.get('Content-Type', '').lower()
                    if 'text/html' not in content_type:
                        continue

                    # Extract links
                    parser = LinkExtractor()
                    try:
                        parser.feed(response.text)
                    except Exception as e:
                        self.logger.debug(f"HTML parsing error for {normalized_url}: {e}")
                        continue

                    # Process extracted links
                    for link in parser.links:
                        # Convert to absolute URL
                        absolute_url = urljoin(normalized_url, link)
                        absolute_url = self._normalize_url(absolute_url)

                        # Only follow same-domain links
                        if not self._is_same_domain(absolute_url, base_url):
                            continue

                        # Check if it's a menu URL
                        if self._is_menu_url(absolute_url):
                            # For PDFs, optionally verify
                            if absolute_url.lower().endswith('.pdf'):
                                if self._verify_pdf(absolute_url):
                                    menu_urls.add(absolute_url)
                            else:
                                menu_urls.add(absolute_url)

                        # Add to visit queue if not visited
                        if absolute_url not in visited and absolute_url not in to_visit:
                            to_visit.append(absolute_url)

                except requests.exceptions.RequestException as e:
                    self.logger.debug(f"Failed to fetch {normalized_url}: {e}")
                    continue

            self.logger.info(f"Found {len(menu_urls)} menu URLs on {website_url}")
            return sorted(list(menu_urls))

        except Exception as e:
            self.logger.error(f"Crawl error for {website_url}: {e}")
            return []

    def close(self):
        """Close the session."""
        self.session.close()
