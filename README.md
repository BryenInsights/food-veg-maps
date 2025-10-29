# Google Places Restaurant Data Collector

A production-ready Python tool for collecting restaurant data from Google Places API, downloading menu photos, and optionally crawling restaurant websites for menu URLs and PDFs.

## Features

- **Google Places API Integration**: Search for restaurants using text search or nearby search
- **Detailed Place Information**: Fetch name, location, ratings, hours, website, and more
- **Photo Downloads**: Automatically download up to N menu photos per restaurant
- **Website Crawling**: Optional crawler to find menu URLs and PDFs on restaurant websites
- **Multiple Output Formats**: Export data to both JSON and CSV
- **Production Ready**: Includes retry logic, rate limiting, error handling, and logging
- **Extensible**: Stub functions provided for future OCR/NLP integration

## Prerequisites

- Python 3.10 or higher
- Google Maps API key with Places API enabled
  - Get your API key: https://console.cloud.google.com/google/maps-apis/credentials
  - Enable Places API: https://console.cloud.google.com/apis/library/places-backend.googleapis.com

## Installation

1. **Clone or download this repository**

2. **Install dependencies**:
   ```bash
   make install
   ```

   Or manually:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure API key**:

   Create a `.env` file in the project root:
   ```bash
   cp .env.example .env
   ```

   Edit `.env` and add your API key:
   ```
   GOOGLE_MAPS_API_KEY=your_api_key_here
   ```

## Usage

### Quick Start

Run the example to collect data for 50 restaurants in Paris:

```bash
make run-example
```

### Command Line Interface

The tool supports two search modes: **text search** and **nearby search**.

#### Text Search

Search for restaurants by city or query:

```bash
python -m app.main --text "restaurants in Paris" --max-places 300
```

```bash
python -m app.main --text "vegetarian restaurants in Tokyo" --max-places 100 --photos-per-place 5
```

#### Nearby Search

Search for restaurants within a radius of coordinates:

```bash
python -m app.main --nearby --lat 48.8566 --lng 2.3522 --radius 2000 --max-places 200
```

#### With Website Crawling

Enable website crawling to find menu URLs and PDFs:

```bash
python -m app.main --text "restaurants in London" --crawl-website --max-places 50
```

### All Command Line Options

```
--text QUERY              Text search query (e.g., "restaurants in Paris")
--nearby                  Use nearby search (requires --lat, --lng)
--lat LATITUDE            Latitude for nearby search
--lng LONGITUDE           Longitude for nearby search
--radius METERS           Search radius in meters (default: 1000)
--max-places NUM          Maximum places to process (default: 200)
--photos-per-place NUM    Max photos to download per place (default: 3)
--outdir PATH             Output directory (default: ./out)
--crawl-website           Enable website crawling for menu URLs
--rate-limit QPS          Rate limit for web crawling in QPS (default: 8)
--user-agent STRING       User agent for HTTP requests
--timeout SECONDS         HTTP request timeout (default: 10)
--verbose                 Enable verbose logging
```

## Output

The tool generates the following outputs in the specified output directory (default: `./out`):

### 1. JSON Output (`places.json`)

Pretty-printed JSON with full place details:

```json
[
  {
    "place_id": "ChIJ...",
    "name": "Le Restaurant Français",
    "lat": 48.8566,
    "lng": 2.3522,
    "formatted_address": "123 Rue de Paris, 75001 Paris, France",
    "rating": 4.5,
    "user_ratings_total": 234,
    "website": "https://example.com",
    "opening_hours": {
      "open_now": true,
      "periods": [...]
    },
    "photo_local_paths": [
      "photos/ChIJ.../p0.jpg",
      "photos/ChIJ.../p1.jpg"
    ],
    "menu_urls": [
      "https://example.com/menu.pdf",
      "https://example.com/carte"
    ],
    "source_timestamp": "2024-01-01T12:00:00Z"
  }
]
```

### 2. CSV Output (`places.csv`)

Flattened CSV for analysis (nested fields are JSON-encoded):

```csv
place_id,name,lat,lng,formatted_address,rating,user_ratings_total,website,opening_hours_json,photo_local_paths_json,menu_urls_json,source_timestamp
ChIJ...,Le Restaurant Français,48.8566,2.3522,"123 Rue...",4.5,234,https://example.com,...
```

### 3. Photos (`photos/<place_id>/`)

Downloaded photos organized by place ID:

```
out/
├── photos/
│   ├── ChIJ.../
│   │   ├── p0.jpg
│   │   ├── p1.jpg
│   │   └── p2.jpg
│   └── ChIJ.../
│       └── p0.jpg
```

### 4. Logs (`logs/run_YYYYMMDD_HHMMSS.log`)

Detailed logs with timestamps for debugging and monitoring.

## Data Schema

Each place record contains:

| Field | Type | Description |
|-------|------|-------------|
| `place_id` | string | Google Places unique identifier |
| `name` | string | Restaurant name |
| `lat` | float | Latitude |
| `lng` | float | Longitude |
| `formatted_address` | string | Full address |
| `rating` | float | Average rating (0-5) |
| `user_ratings_total` | int | Number of ratings |
| `website` | string | Restaurant website URL |
| `opening_hours` | object | Opening hours information |
| `photo_local_paths` | array | Paths to downloaded photos |
| `menu_urls` | array | Menu URLs found via crawling |
| `source_timestamp` | string | ISO8601 timestamp of data collection |

## API Quotas and Pricing

### Google Places API

- **Text Search**: $32 per 1000 requests
- **Nearby Search**: $32 per 1000 requests
- **Place Details**: $17 per 1000 requests (per place)
- **Place Photos**: $7 per 1000 requests (per photo)

**Example cost for 200 places with 3 photos each:**
- 1 search request: ~$0.03
- 200 place details: $3.40
- 600 photos: $4.20
- **Total: ~$7.63**

**Free tier**: $200/month credit (covers ~2,600 places with details)

**Learn more**: https://developers.google.com/maps/billing/gmp-billing

### Rate Limiting

The tool implements the following rate limits:

- **Places API**: 2-second delay between paginated requests (required by API)
- **Website Crawling**: Configurable via `--rate-limit` (default 8 QPS)
- **Retry Logic**: Automatic retry with exponential backoff for 5xx errors

## Testing

Run unit tests:

```bash
make test
```

Or directly:

```bash
pytest tests/ -v
```

Tests include:
- API pagination handling
- Photo download with redirects
- Menu URL extraction
- robots.txt compliance
- JSON/CSV output formatting

## Website Crawling

When `--crawl-website` is enabled, the tool:

1. **Respects robots.txt**: Checks and honors robots.txt rules
2. **Same-domain only**: Only follows links on the same domain
3. **Menu detection**: Identifies URLs containing keywords: menu, carte, la-carte, food, or ending in .pdf
4. **PDF verification**: Verifies PDF content-type via HEAD request
5. **Rate limiting**: Configurable via `--rate-limit` to avoid overwhelming servers
6. **Deduplication**: Returns unique URLs only

## Future Enhancements (Hooks)

The `app/hooks.py` module provides stub functions for future OCR/NLP integration:

```python
from app.hooks import extract_text_from_menu, classify_menu_items

# Extract text from menu photo (requires OCR implementation)
text = extract_text_from_menu("photos/place_id/p0.jpg")

# Classify menu items (requires NLP implementation)
menu_data = classify_menu_items(text)
```

Suggested libraries:
- **OCR**: pytesseract, Google Vision API, AWS Textract
- **NLP**: spaCy, transformers, NLTK

## Troubleshooting

### API Key Issues

**Error**: `GOOGLE_MAPS_API_KEY not found`

**Solution**: Ensure `.env` file exists with valid API key

### API Quota Exceeded

**Error**: API returns `OVER_QUERY_LIMIT`

**Solution**:
- Check your quota in Google Cloud Console
- Reduce `--max-places` value
- Enable billing if using free tier

### No Results Found

**Error**: `No places found`

**Solution**:
- Verify search query is valid
- Try different location or broader search terms
- Check API key has Places API enabled

### Photos Not Downloading

**Issue**: `photo_local_paths` is empty

**Solution**:
- Some places may not have photos
- Check logs for HTTP errors
- Verify internet connectivity

### Website Crawling Slow

**Issue**: Crawling takes too long

**Solution**:
- Reduce `--rate-limit` (but respect server limits)
- Disable `--crawl-website` if not needed
- Some sites may have slow response times

## Idempotency and Resumption

The tool supports idempotent runs:

- **Photos**: Skips download if photo already exists
- **Deterministic ordering**: Places sorted by `place_id` for consistent results
- **Resumption**: Run with lower `--max-places` first, then increase to continue

Example:
```bash
# First run: collect 50 places
python -m app.main --text "restaurants in Paris" --max-places 50

# Later: collect 200 places (will start from beginning, but skip existing photos)
python -m app.main --text "restaurants in Paris" --max-places 200
```

## Project Structure

```
mini veggie hackathon/
├── app/
│   ├── __init__.py
│   ├── main.py              # CLI and main orchestration
│   ├── places_client.py     # Google Places API wrapper
│   ├── crawler.py           # Website crawler
│   ├── io_utils.py          # I/O utilities
│   └── hooks.py             # Stub functions for OCR/NLP
├── tests/
│   ├── test_places_client.py
│   ├── test_crawler.py
│   └── test_io_utils.py
├── out/                     # Output directory (generated)
│   ├── places.json
│   ├── places.csv
│   ├── photos/
│   └── logs/
├── requirements.txt
├── .env                     # Your API key (not in git)
├── .env.example            # Template for .env
├── Makefile
└── README.md
```

## License

This project is provided as-is for educational and commercial use.

## Contributing

Contributions welcome! Areas for improvement:
- OCR implementation for menu photos
- NLP for menu item classification
- Support for other data sources
- Performance optimizations
- Additional output formats

## Compliance and Terms of Service

- **Google Places API**: This tool uses official Google Places API endpoints only. Ensure compliance with Google Maps Platform Terms of Service.
- **Website Crawling**: The crawler respects robots.txt and implements rate limiting. Always verify you have permission to crawl websites.
- **Data Usage**: Collected data is subject to Google's terms regarding caching, attribution, and usage limits.

## Support

For issues or questions:
- Check troubleshooting section above
- Review logs in `out/logs/`
- Verify API key and billing status
- Ensure Python 3.10+ is installed

---

**Built for the Mini Veggie Hackathon** - A production-ready tool for restaurant data collection and analysis.
