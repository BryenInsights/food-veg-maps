# How to Run the Restaurant Data Collector

## Quick Start

### 1. Open Terminal and Navigate to Project
```bash
cd "/Users/adamzer/Desktop/mini veggie hackathon"
```

### 2. Install Dependencies (if not already installed)
```bash
pip install -r requirements.txt
```

### 3. Run a Test Collection

**Option A: Simple test (5 restaurants, 8 photos each, with menu detection)**
```bash
python -m app.main --text "restaurants in Paris" --max-places 5 --photos-per-place 8 --detect-menus
```

**Option B: With website crawling (finds menu PDFs)**
```bash
python -m app.main --text "vegetarian restaurants in London" --max-places 10 --photos-per-place 10 --detect-menus --crawl-website
```

**Option C: Download ALL photos**
```bash
python -m app.main --text "restaurants in Tokyo" --max-places 5 --photos-per-place 0 --detect-menus
```

### 4. Check the Results

After running, check these locations:
- **Global JSON data**: `out/places.json`
- **Global CSV data**: `out/places.csv`
- **Individual restaurants**: `out/[restaurant_name]/`
  - Restaurant data: `out/[restaurant_name]/information/data.json`
  - All photos: `out/[restaurant_name]/photos/photos/`
  - Menu photos only: `out/[restaurant_name]/photos/menus/`
- **Logs**: `out/logs/`

## Example Commands

### Find Vegetarian Restaurants
```bash
python -m app.main \
  --text "vegetarian restaurants in San Francisco" \
  --max-places 20 \
  --photos-per-place 10 \
  --detect-menus \
  --crawl-website
```

### Nearby Search
```bash
python -m app.main \
  --nearby \
  --lat 48.8566 \
  --lng 2.3522 \
  --radius 1500 \
  --max-places 15 \
  --photos-per-place 8 \
  --detect-menus
```

### Quick Test
```bash
python -m app.main --text "restaurants near me" --max-places 3 --photos-per-place 5 --detect-menus --verbose
```

## Understanding the Flags

| Flag | What it does |
|------|--------------|
| `--text "query"` | Search by text (e.g., "restaurants in Paris") |
| `--nearby` | Search by coordinates (needs --lat, --lng, --radius) |
| `--max-places 50` | Collect data for 50 restaurants (default) |
| `--photos-per-place 8` | Download 8 photos per restaurant |
| `--photos-per-place 0` | Download ALL available photos |
| `--detect-menus` | Use OCR to detect which photos are menus |
| `--crawl-website` | Search restaurant websites for menu PDFs |
| `--verbose` | Show detailed progress logs |
| `--outdir ./data` | Save results to custom directory |

## What Happens When You Run It

1. **Searches Google Places API** for restaurants
2. **Downloads photos** from each restaurant
3. **Runs OCR** on each photo (if --detect-menus enabled)
4. **Detects menus** using:
   - Price patterns (€, $, dotted leaders)
   - Menu keywords (entrées, plats, starters, mains, etc.)
   - Text density (lines, words)
5. **Copies menu photos** to `out/[restaurant_name]/photos/menus/`
6. **Crawls websites** for menu PDFs (if --crawl-website enabled)
7. **Saves results** to JSON and CSV

## Check Your Results

```bash
# View the JSON
cat out/places.json | head -100

# Count results
python3 -c "import json; d=json.load(open('out/places.json')); print(f'Found {len(d)} restaurants')"

# See menu detection stats
python3 -c "import json; d=json.load(open('out/places.json')); print(f'Photos: {sum(len(p.get(\"photo_local_paths\",[])) for p in d)}'); print(f'Menus detected: {sum(len(p.get(\"menu_photo_paths\",[])) for p in d)}'); print(f'Menu URLs: {sum(len(p.get(\"menu_urls\",[])) for p in d)}')"

# View logs
tail -50 out/logs/*.log
```

## Test the Menu Detection

To verify OCR is working, test it on the fake menu:
```bash
python << 'EOF'
from pathlib import Path
from app.menu_detector import MenuDetector
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

detector = MenuDetector(logger)
result = detector.detect_menu(Path('out/test_fake_menu.jpg'), save_ocr=True)

print(f"Is menu: {result['is_menu']}")
print(f"Score: {result['score']}/5")
print(f"Prices: {result['price_count']}, Keywords: {result['keyword_count']}")
EOF
```

## Troubleshooting

**If you get "Tesseract not found":**
```bash
brew install tesseract tesseract-lang
```

**If you get "Module not found":**
```bash
pip install -r requirements.txt
```

**If API quota exceeded:**
- Reduce `--max-places` to a smaller number
- Check your Google Cloud Console quota

**If no menus detected:**
- This is normal! Google Places photos are usually food/ambiance
- Use `--crawl-website` to find actual menu PDFs
- Or try `--photos-per-place 20` to download more photos

## API Costs (Estimate)

For 10 restaurants with 8 photos each:
- Search: ~$0.03
- Place Details (10): ~$0.17
- Photos (80): ~$0.56
- **Total: ~$0.76**

## Your API Key

Already configured in `.env`:
```
GOOGLE_MAPS_API_KEY=AIzaSyAjsXbW2nyekjI9Yg6gLa1qlZTNiPSy1nk
```

## Need Help?

Run with `--help`:
```bash
python -m app.main --help
```

---

**Ready to collect restaurant data!** 🍽️
