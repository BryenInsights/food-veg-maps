"""
Stub functions for future NLP/OCR integration.

These functions provide hooks for extracting and analyzing menu text
from downloaded photos. Implementation is left for future enhancement.
"""

from typing import Dict, List


def extract_text_from_menu(image_path: str) -> str:
    """
    Extract text from menu photo using OCR.

    This is a stub function. A full implementation would:
    - Use an OCR library (e.g., pytesseract, Google Vision API, AWS Textract)
    - Preprocess the image (resize, denoise, enhance contrast)
    - Extract text with proper handling of multi-column layouts
    - Clean and normalize the extracted text

    Args:
        image_path: Path to menu photo file

    Returns:
        Extracted text from the menu image

    Example implementation approach:
        ```python
        from PIL import Image
        import pytesseract

        image = Image.open(image_path)
        # Preprocess image if needed
        text = pytesseract.image_to_string(image, lang='eng+fra')
        return text.strip()
        ```
    """
    raise NotImplementedError(
        "OCR text extraction not yet implemented. "
        "Consider using pytesseract, Google Vision API, or AWS Textract."
    )


def classify_menu_items(menu_text: str) -> Dict[str, List[str]]:
    """
    Classify and extract menu items from text.

    This is a stub function. A full implementation would:
    - Use NLP to identify menu item names, descriptions, and prices
    - Classify items into categories (appetizers, mains, desserts, etc.)
    - Extract dietary information (vegetarian, vegan, gluten-free, etc.)
    - Identify ingredients and cuisine type
    - Extract pricing information

    Args:
        menu_text: Extracted text from menu

    Returns:
        Dictionary with classified menu items, e.g.:
        {
            "categories": ["appetizers", "mains", "desserts"],
            "vegetarian_items": ["Caprese Salad", "Margherita Pizza"],
            "vegan_items": ["Mediterranean Salad"],
            "items": [
                {
                    "name": "Caprese Salad",
                    "category": "appetizers",
                    "price": "$12",
                    "ingredients": ["tomato", "mozzarella", "basil"],
                    "dietary": ["vegetarian"]
                }
            ]
        }

    Example implementation approach:
        ```python
        import spacy
        import re

        nlp = spacy.load("en_core_web_sm")
        doc = nlp(menu_text)

        items = []
        # Extract entities, prices, and patterns
        # Classify using keywords or ML model
        # ...

        return {
            "categories": categories,
            "vegetarian_items": veg_items,
            "items": items
        }
        ```
    """
    raise NotImplementedError(
        "Menu item classification not yet implemented. "
        "Consider using spaCy, NLTK, or transformer models for NLP analysis."
    )


def score_vegetarian_friendliness(menu_data: Dict) -> float:
    """
    Calculate a vegetarian-friendliness score for a restaurant.

    This is a stub function. A full implementation would:
    - Count vegetarian/vegan options
    - Weight by menu section (mains vs. sides)
    - Consider variety and quality of descriptions
    - Compare to total menu size
    - Return a normalized score (0-1 or 0-100)

    Args:
        menu_data: Classified menu data from classify_menu_items()

    Returns:
        Vegetarian-friendliness score (0.0-1.0)

    Example implementation:
        ```python
        total_items = len(menu_data.get("items", []))
        veg_items = len(menu_data.get("vegetarian_items", []))
        vegan_items = len(menu_data.get("vegan_items", []))

        if total_items == 0:
            return 0.0

        # Weight vegan items higher
        score = (veg_items + vegan_items * 1.5) / total_items
        return min(score, 1.0)
        ```
    """
    raise NotImplementedError(
        "Vegetarian scoring not yet implemented. "
        "Implement based on your specific scoring criteria."
    )
