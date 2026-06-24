import os
import sys
sys.path.insert(0, "/home/samu2505/SAAS/tradenexus-cli")

from google import genai
from google.genai import types as gtypes
from tradenexus.config import get_api_key, DEFAULT_MODEL

print(f"API Key: {get_api_key()[:10]}...")
print(f"Model: {DEFAULT_MODEL}")

client = genai.Client(api_key=get_api_key())

prompt = "Classify product: Mini Excavator. Return json with role: component or machine."

try:
    print("Sending content generation request with response_schema...")
    response = client.models.generate_content(
        model=DEFAULT_MODEL,
        contents=prompt,
        config=gtypes.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema={
                "type": "object",
                "properties": {
                    "role": {"type": "string", "enum": ["component", "machine"]}
                },
                "required": ["role"]
            }
        )
    )
    print("Response received:")
    print(response.text)
except Exception as e:
    print(f"Error: {e}")
