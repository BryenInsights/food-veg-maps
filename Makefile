.PHONY: install test run-example clean help

help:
	@echo "Available targets:"
	@echo "  install       - Install dependencies"
	@echo "  test          - Run unit tests"
	@echo "  run-example   - Run example data collection (Paris restaurants)"
	@echo "  clean         - Remove generated files and caches"
	@echo "  help          - Show this help message"

install:
	@echo "Installing dependencies..."
	pip install -r requirements.txt
	@echo "Done! Make sure to configure .env with your API key"

test:
	@echo "Running unit tests..."
	pytest tests/ -v --tb=short

run-example:
	@echo "Running example: collecting restaurant data for Paris..."
	@echo "This will fetch up to 50 places with 2 photos each"
	python -m app.main \
		--text "restaurants in Paris" \
		--max-places 50 \
		--photos-per-place 2 \
		--outdir ./out \
		--verbose

run-example-nearby:
	@echo "Running example: nearby search around Eiffel Tower..."
	python -m app.main \
		--nearby \
		--lat 48.8584 \
		--lng 2.2945 \
		--radius 1000 \
		--max-places 30 \
		--photos-per-place 3 \
		--outdir ./out

run-example-crawl:
	@echo "Running example with website crawling enabled..."
	@echo "This will take longer due to website crawling"
	python -m app.main \
		--text "restaurants in Paris" \
		--max-places 20 \
		--photos-per-place 2 \
		--crawl-website \
		--outdir ./out \
		--verbose

clean:
	@echo "Cleaning up..."
	rm -rf out/
	rm -rf __pycache__/
	rm -rf app/__pycache__/
	rm -rf tests/__pycache__/
	rm -rf .pytest_cache/
	find . -name "*.pyc" -delete
	find . -name "*.pyo" -delete
	@echo "Clean complete"
