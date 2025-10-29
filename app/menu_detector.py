"""
Menu detection module using OCR and text analysis.

Stage A: Quick visual/text signals (OCR-based)
- Text density: >300 words or >30 lines
- Price patterns: €, $, dotted leaders
- Menu keywords: FR/EN (entrées, plats, starters, mains, etc.)
- Layout hints: portrait aspect ratio, multiple columns

Stage B: (Optional) Lightweight classifier using CLIP zero-shot
"""

import re
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from PIL import Image
import pytesseract


# Regex patterns for price detection
EURO_PATTERN = r"\b\d{1,3}([.,]\d{3})*([.,]\d{2})?\s?€\b|€\s?\d+([.,]\d{2})?"
DOLLAR_PATTERN = r"\$\s?\d+([.,]\d{2})?"
DOTTED_LEADER_PATTERN = r"\.{3,}\s*\d+([.,]\d{2})?"
PRICE_PATTERN = rf"(?:{EURO_PATTERN})|(?:{DOLLAR_PATTERN})|(?:{DOTTED_LEADER_PATTERN})"

# Menu keywords (French and English)
FR_KEYWORDS = [
    "menu", "carte", "à la carte", "entrées", "entrée", "plats", "plat",
    "desserts", "dessert", "boissons", "boisson", "formule", "formules",
    "apéritifs", "digestifs", "vins", "prix"
]

EN_KEYWORDS = [
    "menu", "starters", "starter", "appetizers", "appetizer", "mains", "main",
    "entrees", "entree", "sides", "side", "desserts", "dessert",
    "beverages", "beverage", "drinks", "lunch", "dinner", "breakfast",
    "specials", "prix fixe", "course", "courses"
]

ALL_MENU_KEYWORDS = FR_KEYWORDS + EN_KEYWORDS


class MenuDetector:
    """OCR-based detector for identifying menu photos."""

    def __init__(self, logger: logging.Logger, ocr_lang: str = "eng+fra"):
        """
        Initialize menu detector with OCR.

        Args:
            logger: Logger instance
            ocr_lang: Tesseract language codes (default: eng+fra for English+French)
        """
        self.logger = logger
        self.ocr_lang = ocr_lang
        self._check_tesseract()

    def _check_tesseract(self):
        """Check if Tesseract is installed."""
        try:
            pytesseract.get_tesseract_version()
            self.logger.debug(f"Tesseract OCR available: {pytesseract.get_tesseract_version()}")
        except Exception as e:
            self.logger.warning(f"Tesseract not available: {e}. Install with: brew install tesseract tesseract-lang")

    def _extract_text(self, image_path: Path) -> Tuple[str, int]:
        """
        Extract text from image using OCR.

        Args:
            image_path: Path to image file

        Returns:
            Tuple of (extracted text, number of lines)
        """
        try:
            # Open image
            img = Image.open(image_path)

            # Convert to grayscale for better OCR
            if img.mode != 'L':
                img = img.convert('L')

            # Run OCR
            text = pytesseract.image_to_string(img, lang=self.ocr_lang)

            # Count non-empty lines
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            n_lines = len(lines)

            self.logger.debug(f"OCR extracted {len(text)} chars, {n_lines} lines from {image_path.name}")

            return text, n_lines

        except Exception as e:
            self.logger.debug(f"OCR failed for {image_path}: {e}")
            return "", 0

    def _count_price_matches(self, text: str) -> int:
        """Count price pattern matches in text."""
        return len(re.findall(PRICE_PATTERN, text, re.IGNORECASE))

    def _count_keyword_matches(self, text: str) -> int:
        """Count menu keyword matches in text."""
        text_lower = text.lower()
        count = 0
        for keyword in ALL_MENU_KEYWORDS:
            # Use word boundaries to avoid false positives
            pattern = rf"\b{re.escape(keyword)}\b"
            if re.search(pattern, text_lower):
                count += 1
        return count

    def _get_image_aspect_ratio(self, image_path: Path) -> float:
        """Get image aspect ratio (width/height)."""
        try:
            with Image.open(image_path) as img:
                width, height = img.size
                if height > 0:
                    return width / height
        except Exception as e:
            self.logger.debug(f"Failed to get aspect ratio for {image_path}: {e}")
        return 0.0

    def detect_menu(self, image_path: Path, save_ocr: bool = False) -> Dict[str, any]:
        """
        Detect if an image is likely a menu using OCR and text analysis.

        Scoring system:
        - Prices found: +2 points
        - 2+ menu keywords: +2 points
        - >30 lines of text: +1 point
        - >300 words: +1 point
        - Portrait aspect (0.6-0.8): +1 point
        - Threshold: ≥3 points = menu

        Args:
            image_path: Path to image file
            save_ocr: If True, save OCR text to adjacent .txt file

        Returns:
            Dictionary with detection results
        """
        if not image_path.exists():
            return {
                "is_menu": False,
                "confidence": 0.0,
                "score": 0,
                "reasons": ["File does not exist"],
                "ocr_text_path": None
            }

        # Extract text via OCR
        text, n_lines = self._extract_text(image_path)

        # Count words
        words = text.split()
        n_words = len(words)

        # Get aspect ratio
        aspect_ratio = self._get_image_aspect_ratio(image_path)

        # Calculate score based on heuristics
        score = 0
        reasons = []

        # Rule 1: Price patterns
        price_count = self._count_price_matches(text)
        if price_count > 0:
            score += 2
            reasons.append(f"Found {price_count} price patterns")

        # Rule 2: Menu keywords
        keyword_count = self._count_keyword_matches(text)
        if keyword_count >= 2:
            score += 2
            reasons.append(f"Found {keyword_count} menu keywords")

        # Rule 3: Text density - lines
        if n_lines > 30:
            score += 1
            reasons.append(f"{n_lines} lines of text")

        # Rule 4: Text density - words
        if n_words > 300:
            score += 1
            reasons.append(f"{n_words} words detected")

        # Rule 5: Portrait aspect ratio (typical for menus)
        if 0.6 <= aspect_ratio <= 0.8:
            score += 1
            reasons.append(f"Portrait aspect ratio ({aspect_ratio:.2f})")

        # Determine if it's a menu (threshold: 3+ points)
        is_menu = score >= 3

        # Calculate confidence (0-1)
        confidence = min(score / 5.0, 1.0)

        # Save OCR text if requested
        ocr_text_path = None
        if save_ocr and is_menu:
            ocr_text_path = image_path.with_suffix('.txt')
            try:
                with open(ocr_text_path, 'w', encoding='utf-8') as f:
                    f.write(text)
                ocr_text_path = str(ocr_text_path)
            except Exception as e:
                self.logger.warning(f"Failed to save OCR text: {e}")

        if not is_menu and score > 0:
            reasons.append(f"Score {score}/5 below threshold (need 3)")

        return {
            "is_menu": is_menu,
            "confidence": confidence,
            "score": score,
            "reasons": reasons,
            "n_lines": n_lines,
            "n_words": n_words,
            "price_count": price_count,
            "keyword_count": keyword_count,
            "aspect_ratio": aspect_ratio,
            "ocr_text_path": ocr_text_path
        }

    def analyze_photos(self, photo_paths: List[Path], save_ocr: bool = False) -> List[Dict[str, any]]:
        """
        Analyze multiple photos and identify likely menus.

        Args:
            photo_paths: List of paths to photo files
            save_ocr: If True, save OCR text for detected menus

        Returns:
            List of analysis results for each photo
        """
        results = []

        for photo_path in photo_paths:
            analysis = self.detect_menu(photo_path, save_ocr=save_ocr)
            analysis["path"] = str(photo_path)
            results.append(analysis)

            if analysis["is_menu"]:
                self.logger.info(
                    f"✓ Menu detected: {photo_path.name} "
                    f"(score: {analysis['score']}/5, "
                    f"{analysis['price_count']} prices, "
                    f"{analysis['keyword_count']} keywords)"
                )
            else:
                self.logger.debug(
                    f"✗ Not a menu: {photo_path.name} "
                    f"(score: {analysis['score']}/5)"
                )

        return results

    def filter_menu_photos(self, photo_paths: List[Path], save_ocr: bool = False) -> List[Path]:
        """
        Filter photo list to only return likely menu photos.

        Args:
            photo_paths: List of paths to photo files
            save_ocr: If True, save OCR text for detected menus

        Returns:
            List of paths that are likely menus
        """
        results = self.analyze_photos(photo_paths, save_ocr=save_ocr)
        menu_photos = [
            Path(r["path"]) for r in results if r["is_menu"]
        ]

        self.logger.info(
            f"Identified {len(menu_photos)} menu photos "
            f"out of {len(photo_paths)} total"
        )

        return menu_photos


def detect_menus_in_directory(
    photo_dir: Path,
    logger: logging.Logger,
    save_ocr: bool = False
) -> Dict[str, List[str]]:
    """
    Scan a directory and detect menu photos.

    Args:
        photo_dir: Directory containing photos
        logger: Logger instance
        save_ocr: If True, save OCR text for detected menus

    Returns:
        Dictionary with:
            - menu_photos: List of menu photo paths
            - other_photos: List of non-menu photo paths
    """
    detector = MenuDetector(logger)

    # Find all image files
    photo_files = []
    for ext in ['*.jpg', '*.jpeg', '*.png', '*.JPG', '*.JPEG', '*.PNG']:
        photo_files.extend(photo_dir.glob(ext))

    if not photo_files:
        return {"menu_photos": [], "other_photos": []}

    # Analyze all photos
    results = detector.analyze_photos(photo_files, save_ocr=save_ocr)

    menu_photos = [r["path"] for r in results if r["is_menu"]]
    other_photos = [r["path"] for r in results if not r["is_menu"]]

    return {
        "menu_photos": menu_photos,
        "other_photos": other_photos
    }
