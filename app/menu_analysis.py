import pytesseract
from PIL import Image
import json
import pandas as pd
from openai import OpenAI
import os
from pathlib import Path
from dotenv import load_dotenv

# 1️⃣ --- SETUP ---

# Add a .env file with openai API key
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("❌ OPENAI_API_KEY not found in .env file!")

client = OpenAI(api_key=api_key)
MODEL_NAME = "gpt-5-mini"

CSV_INPUT_PATH = "places_test.csv"  # Input CSV file
CSV_OUTPUT_PATH = "restaurants_analyzed.csv"  # Output CSV file
IMAGE_PATH_COLUMN = "menu_local_path"  # Column name in your CSV


# 2️⃣ --- OCR FUNCTION ---
def extract_text_from_image(image_path):
    """Extract text from a menu image using Tesseract OCR."""
    try:
        image = Image.open(image_path)
        return pytesseract.image_to_string(image).strip()
    except Exception as e:
        print(f"❌ Error reading image {image_path}: {e}")
        return ""


# 3️⃣ --- OPENAI LLM FUNCTION ---
def analyze_menu_with_openai(menu_text):
    """Send the extracted menu text to OpenAI GPT-4 mini for classification."""
    if not menu_text:
        return {"dishes": [], "menu_veg_score": 0}

    prompt = f"""TASK: Classify restaurant menu dishes and calculate environmental score.

INSTRUCTIONS:
1. For EACH dish, classify as EXACTLY ONE of: "Vegan", "Vegetarian", or "Non-Vegetarian"
2. Estimate CO₂ emissions (in kg CO₂e) for each dish
3. Calculate menu vegetarian score: (vegan_count * 2 + vegetarian_count) / (total_dishes * 2) * 100

CRITICAL: You MUST respond with ONLY valid JSON, nothing else. No explanations, no markdown, just JSON.

Format:
{{
  "dishes": [
    {{"dish": "dish name", "type": "Vegan", "co2_kg": 0.4}},
    {{"dish": "another dish", "type": "Vegetarian", "co2_kg": 1.2}},
    {{"dish": "meat dish", "type": "Non-Vegetarian", "co2_kg": 3.5}}
  ],
  "menu_veg_score": 67
}}

Menu text:
{menu_text}"""

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
        )
        raw_output = response.choices[0].message.content
        start = raw_output.find("{")
        end = raw_output.rfind("}") + 1
        return (
            json.loads(raw_output[start:end])
            if start != -1 and end > start
            else {"dishes": [], "menu_veg_score": 0}
        )
    except Exception as e:
        print(f"❌ Error calling OpenAI: {e}")
        return {"dishes": [], "menu_veg_score": 0}


# 4️⃣ --- MAIN PIPELINE ---
def main():
    df = pd.read_csv(CSV_INPUT_PATH)
    df["dishes_json"] = ""
    df["menu_veg_score"] = 0

    print(f"📊 Processing {len(df)} menus...")
    for idx, row in df.iterrows():
        image_path = Path(row[IMAGE_PATH_COLUMN])

        print(f"\n[{idx + 1}/{len(df)}] {image_path}")
        menu_text = extract_text_from_image(image_path)

        if menu_text:
            results = analyze_menu_with_openai(menu_text)
            df.at[idx, "dishes_json"] = json.dumps(results.get("dishes", []))
            df.at[idx, "menu_veg_score"] = results.get("menu_veg_score", 0)
            print(f"  ✅ Score: {results.get('menu_veg_score', 0)}%")
        else:
            df.at[idx, "dishes_json"] = json.dumps([])
            df.at[idx, "menu_veg_score"] = 0

    df.to_csv(CSV_OUTPUT_PATH, index=False)
    print(f"\n✅ Results saved to {CSV_OUTPUT_PATH}")


if __name__ == "__main__":
    main()
