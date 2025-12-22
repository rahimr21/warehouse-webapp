import json
import os
from typing import Any, Dict, List, Optional

import requests


GEMINI_API_KEY_ENV = "GEMINI_API_KEY"


class GeminiUnavailable(Exception):
    """Raised when Gemini is not configured or reachable."""


def _get_api_key() -> str:
    api_key = os.getenv(GEMINI_API_KEY_ENV)
    if not api_key:
        raise GeminiUnavailable("Gemini API key not configured")
    return api_key


def interpret_box_speech(transcript: str, current_state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Call Gemini to interpret spoken warehouse box description into structured JSON.

    Returns a dict with:
      {
        "box_number": Optional[str],
        "weight": Optional[float],
        "contents": [
          {"product_type": str, "quantity": int, "lcd_size": Optional[str]}
        ],
        "notes": [str]
      }

    Raises:
      GeminiUnavailable: if key is missing or Gemini is unreachable.
      ValueError: if the returned JSON is invalid.
    """
    api_key = _get_api_key()

    # Normalize current state to keep prompt small and predictable
    box_number = current_state.get("box_number")
    weight = current_state.get("weight")
    contents = current_state.get("contents") or []

    system_instructions = """
You are a warehouse box data parser for a tech recycling company.

Your ONLY job is to convert the operator's spoken description of a single box
into STRICT JSON describing:
  - box_number (string or null)
  - weight (number or null) in pounds
  - contents: list of objects with:
      - product_type (one of: "Laptops", "PCs", "LCDs", "Servers",
        "Switches", "Wires", "Keyboards", "Stands")
      - quantity (integer > 0)
      - lcd_size (string or null), only for LCDs, using these conventions:
          - 24"  => "24\\""
          - 20 inch square, 20\" square, 20 S => "20\\"S"
          - 20 inch wide, widescreen, 20 W  => "20\\"W"
          - Borderless 24 inch              => "Borderless 24\\""

You MUST:
  - Treat the input as an incremental update to the CURRENT box state.
  - Add quantities to existing contents with the same product_type and lcd_size.
  - Never decrease quantities.
  - Keep all unspecified fields from the current state unchanged.
  - If you cannot confidently parse anything from the text, return an `error` field.

Output RULES (very important):
  - Output VALID JSON ONLY.
  - NO comments, NO extra text, NO trailing commas.
  - Either:
      { "box_number": ..., "weight": ..., "contents": [...], "notes": [...] }
    or:
      { "error": "human friendly message" }
"""

    examples = [
        {
            "input": "box 1221, 45 pounds, 12 laptops and 15 twenty inch square LCDs",
            "current_box": {"box_number": None, "weight": None, "contents": []},
            "output": {
                "box_number": "1221",
                "weight": 45,
                "contents": [
                    {"product_type": "Laptops", "quantity": 12, "lcd_size": None},
                    {"product_type": "LCDs", "quantity": 15, "lcd_size": "20\"S"},
                ],
                "notes": ["Parsed 20 inch square as 20\"S"],
            },
        },
        {
            "input": "add 10 more laptops and 5 twenty four inch LCD monitors",
            "current_box": {
                "box_number": "1221",
                "weight": 45,
                "contents": [
                    {"product_type": "Laptops", "quantity": 12, "lcd_size": None},
                    {"product_type": "LCDs", "quantity": 15, "lcd_size": "20\"S"},
                ],
            },
            "output": {
                "box_number": "1221",
                "weight": 45,
                "contents": [
                    {"product_type": "Laptops", "quantity": 22, "lcd_size": None},
                    {"product_type": "LCDs", "quantity": 15, "lcd_size": "20\"S"},
                    {"product_type": "LCDs", "quantity": 5, "lcd_size": "24\""},
                ],
                "notes": ["Accumulated laptops quantity from 12 to 22"],
            },
        },
    ]

    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {
                        "text": json.dumps(
                            {
                                "instructions": system_instructions,
                                "current_box": {
                                    "box_number": box_number,
                                    "weight": weight,
                                    "contents": contents,
                                },
                                "examples": examples,
                                "transcript": transcript,
                            },
                            ensure_ascii=False,
                        )
                    }
                ],
            }
        ],
        "generationConfig": {
            "temperature": 0.1,
            "maxOutputTokens": 512,
        },
    }

    # Use current free-tier friendly model + stable v1 endpoint.
    # You can swap the model name if Google updates recommendations.
    model_name = "gemini-2.5-flash-lite"
    url = f"https://generativelanguage.googleapis.com/v1/models/{model_name}:generateContent"
    try:
        response = requests.post(url, params={"key": api_key}, json=payload, timeout=10)
    except requests.RequestException as exc:
        raise GeminiUnavailable(f"Error calling Gemini: {exc}") from exc

    if response.status_code != 200:
        raise GeminiUnavailable(f"Gemini HTTP {response.status_code}: {response.text}")

    data = response.json()

    try:
        text = data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError) as exc:
        raise ValueError(f"Unexpected Gemini response format: {data}") from exc

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Gemini did not return valid JSON: {text}") from exc

    return parsed


