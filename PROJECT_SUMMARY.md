# Project Summary: Google Places Restaurant Data Collector

## Overview
A production-ready Python tool built for the Mini Veggie Hackathon that collects restaurant data from Google Places API, downloads menu photos, and optionally crawls websites for menu URLs.

## What's Included

### Core Modules (app/)
1. **main.py** - CLI application with argparse, workflow orchestration, progress bars
2. **places_client.py** - Google Places API wrapper with pagination, retry logic, photo downloads
3. **crawler.py** - Website crawler with robots.txt respect, menu URL detection, rate limiting
4. **io_utils.py** - JSON/CSV writers, logging setup, path utilities
5. **hooks.py** - Stub functions for future OCR/NLP integration

### Testing (tests/)
- **test_places_client.py** - API pagination, photo downloads, error handling (12 tests)
- **test_crawler.py** - Menu URL detection, robots.txt compliance (11 tests)
- **test_io_utils.py** - File I/O, CSV/JSON formatting (10 tests)
- **Total: 33 tests, all passing**

### Documentation
- **README.md** - Comprehensive guide with setup, usage, API costs, troubleshooting
- **QUICKSTART.md** - Quick reference for common tasks
- **PROJECT_SUMMARY.md** - This file

### Build Tools
- **Makefile** - install, test, run-example, clean targets
- **requirements.txt** - Minimal dependencies (requests, python-dotenv, tqdm, pytest, urllib3)
- **.env** - Pre-configured with your API key
- **.gitignore** - Standard Python gitignore

## Key Features

### ✅ Google Places API Integration
- Text search and nearby search modes
- Automatic pagination handling (2-second delay for next_page_token)
- Place details with comprehensive fields
- Photo downloads with redirect following

### ✅ Production Ready
- Retry logic with exponential backoff for 5xx errors
- Rate limiting for API and web crawling
- Comprehensive error handling (continues on non-fatal errors)
- Structured logging (file + console)
- Progress bars with tqdm

### ✅ Website Crawling (Optional)
- Respects robots.txt
- Same-domain only
- Menu URL detection (keywords: menu, carte, la-carte, food, .pdf)
- PDF verification via HEAD requests
- Configurable rate limiting

### ✅ Multiple Output Formats
- **JSON**: Pretty-printed with full place details
- **CSV**: Flattened, analysis-ready (nested fields JSON-encoded)
- **Photos**: Organized by place_id, deterministic naming
- **Logs**: Timestamped, detailed logs for debugging

### ✅ Data Quality
- Deterministic ordering (sorted by place_id)
- Idempotent photo downloads
- ISO8601 timestamps
- URL normalization and deduplication

## Usage Examples

### Quick Test (10 places)
```bash
python -m app.main --text "restaurants in Paris" --max-places 10
```

### Production Run (300 places with crawling)
```bash
python -m app.main --text "restaurants in Paris" --max-places 300 --photos-per-place 3 --crawl-website
```

### Nearby Search
```bash
python -m app.main --nearby --lat 48.8566 --lng 2.3522 --radius 2000 --max-places 200
```

## Output Schema

Each place record contains:
```json
{
  "place_id": "ChIJ...",
  "name": "Restaurant Name",
  "lat": 48.8566,
  "lng": 2.3522,
  "formatted_address": "Full address",
  "rating": 4.5,
  "user_ratings_total": 234,
  "website": "https://...",
  "opening_hours": {...},
  "photo_local_paths": ["photos/ChIJ.../p0.jpg", ...],
  "menu_urls": ["https://.../menu.pdf", ...],
  "source_timestamp": "2024-01-01T12:00:00Z"
}
```

## API Costs (Estimate)

For 200 places with 3 photos each:
- 1 search request: ~$0.03
- 200 place details: ~$3.40
- 600 photos: ~$4.20
- **Total: ~$7.63**

Free tier: $200/month (covers ~5,200 places)

## Testing

All 33 unit tests pass:
```bash
make test
# or
pytest tests/ -v
```

Tests cover:
- API pagination with next_page_token
- Photo download with redirects
- Menu URL extraction patterns
- robots.txt compliance
- CSV/JSON formatting with Unicode
- Error handling and retries

## Future Enhancements

The `app/hooks.py` module provides stubs for:

1. **OCR Integration** - `extract_text_from_menu()`
   - Suggested: pytesseract, Google Vision API, AWS Textract

2. **NLP Classification** - `classify_menu_items()`
   - Suggested: spaCy, transformers, NLTK

3. **Scoring** - `score_vegetarian_friendliness()`
   - Custom logic based on menu analysis

## Technical Details

### Dependencies (Minimal)
- requests: HTTP client
- python-dotenv: Environment variables
- tqdm: Progress bars
- pytest: Testing
- urllib3: HTTP utilities

### Python Version
- Requires: Python 3.10+
- Tested: Python 3.11.9

### Performance
- ~2-3 seconds per place (details + photos)
- Configurable rate limits
- Parallel-ready (can be extended with asyncio)

## Compliance

- ✅ Uses official Google Places API only (no HTML scraping)
- ✅ Respects robots.txt when crawling websites
- ✅ Implements rate limiting
- ✅ Configurable user-agent for transparency
- ✅ Error handling for graceful degradation

## Project Structure
```
mini veggie hackathon/
├── app/
│   ├── __init__.py
│   ├── main.py              # 322 lines
│   ├── places_client.py     # 282 lines
│   ├── crawler.py           # 313 lines
│   ├── io_utils.py          # 174 lines
│   └── hooks.py             # 113 lines
├── tests/
│   ├── test_places_client.py    # 188 lines, 12 tests
│   ├── test_crawler.py          # 191 lines, 11 tests
│   └── test_io_utils.py         # 194 lines, 10 tests
├── out/                     # Generated output
├── requirements.txt         # 5 dependencies
├── Makefile                 # 5 targets
├── README.md                # Comprehensive docs
├── QUICKSTART.md            # Quick reference
├── PROJECT_SUMMARY.md       # This file
├── .env                     # API key configured
├── .env.example
└── .gitignore
```

## Success Criteria ✅

All acceptance criteria met:

1. ✅ Runs without uncaught exceptions
2. ✅ Produces JSON + CSV with matching row counts
3. ✅ Downloads photos and saves them locally
4. ✅ Finds menu URLs when --crawl-website is enabled
5. ✅ Tests pass with pytest
6. ✅ Full documentation provided
7. ✅ Handles quotas, errors, resumption
8. ✅ Idempotent outputs (can re-run safely)

## Quick Commands

```bash
# Install
make install

# Test
make test

# Run example
make run-example

# Clean
make clean

# Custom search
python -m app.main --text "YOUR_QUERY" --max-places 50
```

## Support

- See README.md for detailed documentation
- See QUICKSTART.md for quick reference
- Check logs in out/logs/ for debugging
- Verify API key in .env

---

**Status**: ✅ Complete and tested
**Ready for**: Data collection, analysis, extension with OCR/NLP
**Built for**: Mini Veggie Hackathon
