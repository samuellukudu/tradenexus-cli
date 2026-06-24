import os
import asyncio
from google import genai
from google.genai import types as gtypes
from dotenv import load_dotenv

load_dotenv()

async def main():
    api_key = os.environ.get("GEMINI_API_KEY")
    model = "gemma-4-31b-it"
    client = genai.Client(api_key=api_key)
    
    prompt = (
        "You are an industrial product classifier for B2B trade.\n"
        "Classify this product's role in the supply chain and identify the ecosystem around it.\n\n"
        "Product: solar panels\n"
        "Description: solar panels\n"
        "Supplier country: China\n\n"
        "Return only valid JSON:\n"
        "{\n"
        '  "role": "<one of: finished system, machine or equipment, component, consumable, raw material, spare part, installation or service, software-enabled system>",\n'
        '  "resellerTypes": ["who resells this product"],\n'
        '  "installerTypes": ["who installs it"],\n'
        '  "operatorTypes": ["who operates/uses it"],\n'
        '  "maintainerTypes": ["who maintains/services it"],\n'
        '  "financierTypes": ["who finances purchases of it"]\n'
        "}"
    )

    print("Sending content generation request with gemma-4-31b-it and schema...")
    try:
        response = await client.aio.models.generate_content(
            model=model,
            contents={"parts": [{"text": prompt}]},
            config=gtypes.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema={
                    "type": "object",
                    "properties": {
                        "role": {
                            "type": "string",
                            "enum": [
                                "finished system",
                                "machine or equipment",
                                "component",
                                "consumable",
                                "raw material",
                                "spare part",
                                "installation or service",
                                "software-enabled system"
                            ]
                        },
                        "resellerTypes": {"type": "array", "items": {"type": "string"}},
                        "installerTypes": {"type": "array", "items": {"type": "string"}},
                        "operatorTypes": {"type": "array", "items": {"type": "string"}},
                        "maintainerTypes": {"type": "array", "items": {"type": "string"}},
                        "financierTypes": {"type": "array", "items": {"type": "string"}}
                    },
                    "required": ["role"]
                }
            )
        )
        print("Response received:")
        print(response.text)
    except Exception as e:
        print(f"Error occurred: {e}")

if __name__ == "__main__":
    asyncio.run(main())
