# Quick Start Guide

## 1. Install Dependencies
```bash
make install
```

## 2. Verify Setup
```bash
make test
```
All 33 tests should pass.

## 3. Run a Small Test
Collect data for 10 restaurants in Paris:
```bash
python -m app.main --text "restaurants in Paris" --max-places 10 --photos-per-place 2
```

## 4. Check Output
```bash
ls -la out/
ls -la out/photos/
head -n 20 out/places.json
```

## Common Commands

### Text Search
```bash
# Basic search
python -m app.main --text "vegetarian restaurants in London" --max-places 50

# With website crawling
python -m app.main --text "restaurants in Tokyo" --max-places 30 --crawl-website
```

### Nearby Search
```bash
# Search around specific coordinates
python -m app.main --nearby --lat 40.7128 --lng -74.0060 --radius 1500 --max-places 100
```

### Custom Output
```bash
# Custom output directory
python -m app.main --text "cafes in Berlin" --outdir ./data/berlin --max-places 20

# More photos per place
python -m app.main --text "restaurants in Rome" --photos-per-place 5
```

## Estimated Costs (Google Places API)

For 100 places with 3 photos each:
- Text/Nearby Search: ~$0.03
- Place Details (100): ~$1.70
- Photos (300): ~$2.10
- **Total: ~$3.83**

Free tier provides $200/month credit (covers ~5,200 places with photos).

## Troubleshooting

**No results?**
- Check your API key in `.env`
- Verify Places API is enabled in Google Cloud Console
- Try a different search query

**Tests failing?**
- Ensure Python 3.10+ is installed
- Run `make install` again
- Check pytest version: `pytest --version`

**Rate limit errors?**
- Reduce `--max-places`
- Add delays between runs
- Check quota in Google Cloud Console

## Next Steps

1. **Analyze the data**: Use pandas to analyze `out/places.csv`
2. **Implement OCR**: Add pytesseract to extract menu text from photos
3. **Add NLP**: Implement menu item classification in `app/hooks.py`
4. **Scale up**: Collect data for multiple cities
5. **Visualize**: Create maps and charts from the collected data

## Project Structure
```
mini veggie hackathon/
├── app/                    # Main application code
│   ├── main.py            # CLI entry point
│   ├── places_client.py   # Google Places API
│   ├── crawler.py         # Website crawler
│   ├── io_utils.py        # File I/O
│   └── hooks.py           # Future OCR/NLP
├── tests/                 # Unit tests
├── out/                   # Output (generated)
│   ├── places.json
│   ├── places.csv
│   ├── photos/
│   └── logs/
├── requirements.txt
├── Makefile
└── README.md
```

## Support

See the main [README.md](README.md) for comprehensive documentation.
