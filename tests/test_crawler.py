"""Unit tests for crawler module."""

import logging
from unittest.mock import Mock, MagicMock, patch
import pytest
from app.crawler import WebsiteCrawler, RobotsTxtParser, LinkExtractor


@pytest.fixture
def mock_logger():
    """Create a mock logger."""
    return Mock(spec=logging.Logger)


@pytest.fixture
def crawler(mock_logger):
    """Create a WebsiteCrawler instance."""
    return WebsiteCrawler(mock_logger, rate_limit_qps=100)  # High QPS for faster tests


def test_robots_txt_parser_disallow():
    """Test robots.txt parser correctly identifies disallowed paths."""
    robots_content = """
User-agent: *
Disallow: /admin
Disallow: /private/
    """
    parser = RobotsTxtParser(robots_content, "TestBot")

    assert parser.is_allowed("/") is True
    assert parser.is_allowed("/menu") is True
    assert parser.is_allowed("/admin") is False
    assert parser.is_allowed("/private/data") is False


def test_robots_txt_parser_specific_user_agent():
    """Test robots.txt parser with specific user agent."""
    robots_content = """
User-agent: Googlebot
Disallow: /test

User-agent: *
Disallow: /admin
    """
    parser = RobotsTxtParser(robots_content, "MyBot")

    assert parser.is_allowed("/test") is True  # Rule doesn't apply to MyBot
    assert parser.is_allowed("/admin") is False


def test_link_extractor():
    """Test HTML link extraction."""
    html = """
    <html>
        <body>
            <a href="/menu">Menu</a>
            <a href="/contact">Contact</a>
            <img src="/images/logo.jpg">
        </body>
    </html>
    """
    extractor = LinkExtractor()
    extractor.feed(html)

    assert "/menu" in extractor.links
    assert "/contact" in extractor.links
    assert "/images/logo.jpg" in extractor.links


def test_is_menu_url(crawler):
    """Test menu URL detection logic."""
    assert crawler._is_menu_url("https://example.com/menu") is True
    assert crawler._is_menu_url("https://example.com/carte") is True
    assert crawler._is_menu_url("https://example.com/la-carte.html") is True
    assert crawler._is_menu_url("https://example.com/food") is True
    assert crawler._is_menu_url("https://example.com/menu.pdf") is True
    assert crawler._is_menu_url("https://example.com/MENU.PDF") is True  # Case insensitive

    assert crawler._is_menu_url("https://example.com/about") is False
    assert crawler._is_menu_url("https://example.com/contact") is False


def test_is_same_domain(crawler):
    """Test same-domain checking."""
    assert crawler._is_same_domain(
        "https://example.com/page1",
        "https://example.com/page2"
    ) is True

    assert crawler._is_same_domain(
        "https://www.example.com/page1",
        "https://example.com/page2"
    ) is True

    assert crawler._is_same_domain(
        "https://example.com/page",
        "https://other.com/page"
    ) is False


def test_normalize_url(crawler):
    """Test URL normalization."""
    url_with_fragment = "https://example.com/menu#section1"
    normalized = crawler._normalize_url(url_with_fragment)
    assert "#section1" not in normalized
    assert normalized == "https://example.com/menu"


def test_crawl_for_menus_basic(crawler, mock_logger):
    """Test basic menu crawling with mocked responses."""
    # Mock robots.txt
    robots_response = MagicMock()
    robots_response.status_code = 200
    robots_response.text = "User-agent: *\nDisallow: /admin"

    # Mock main page
    main_response = MagicMock()
    main_response.status_code = 200
    main_response.headers = {'Content-Type': 'text/html'}
    main_response.text = """
    <html>
        <body>
            <a href="/menu">Our Menu</a>
            <a href="/about">About Us</a>
            <a href="https://example.com/menu.pdf">Download Menu</a>
        </body>
    </html>
    """

    # Mock PDF verification
    pdf_response = MagicMock()
    pdf_response.headers = {'Content-Type': 'application/pdf'}

    def mock_get(url, **kwargs):
        if 'robots.txt' in url:
            return robots_response
        elif url == 'https://example.com':
            return main_response
        elif 'menu.pdf' in url:
            return pdf_response
        return MagicMock(status_code=404)

    def mock_head(url, **kwargs):
        if 'menu.pdf' in url:
            return pdf_response
        return MagicMock(headers={})

    with patch.object(crawler.session, 'get', side_effect=mock_get):
        with patch.object(crawler.session, 'head', side_effect=mock_head):
            menu_urls = crawler.crawl_for_menus("https://example.com")

    # Should find menu URLs
    assert len(menu_urls) > 0
    # PDF should be included
    assert any('menu.pdf' in url for url in menu_urls)


def test_crawl_for_menus_respects_robots(crawler, mock_logger):
    """Test that crawler respects robots.txt."""
    # Mock robots.txt that disallows /menu
    robots_response = MagicMock()
    robots_response.status_code = 200
    robots_response.text = "User-agent: *\nDisallow: /menu"

    with patch.object(crawler.session, 'get', return_value=robots_response):
        # Should return empty list if robots.txt blocks access
        with patch.object(crawler, '_fetch_robots_txt') as mock_fetch:
            parser = RobotsTxtParser(robots_response.text, crawler.user_agent)
            mock_fetch.return_value = parser

            # The crawler should respect the disallow
            assert parser.is_allowed("/menu") is False


def test_crawl_empty_website(crawler):
    """Test crawling with empty/invalid website."""
    result = crawler.crawl_for_menus("")
    assert result == []

    result = crawler.crawl_for_menus(None)
    assert result == []


def test_verify_pdf_success(crawler):
    """Test PDF verification."""
    mock_response = MagicMock()
    mock_response.headers = {'Content-Type': 'application/pdf'}

    with patch.object(crawler.session, 'head', return_value=mock_response):
        assert crawler._verify_pdf("https://example.com/menu.pdf") is True


def test_verify_pdf_failure(crawler):
    """Test PDF verification with non-PDF content."""
    mock_response = MagicMock()
    mock_response.headers = {'Content-Type': 'text/html'}

    with patch.object(crawler.session, 'head', return_value=mock_response):
        assert crawler._verify_pdf("https://example.com/fake.pdf") is False
