import os
import asyncio
from google import genai
from google.genai import types as gtypes
from dotenv import load_dotenv

load_dotenv()

async def test_text_streaming():
    print("\n--- Test 1: Real-time Text Streaming with Gemma 4 ---")
    api_key = os.environ.get("GEMINI_API_KEY")
    model = "gemma-4-31b-it"
    client = genai.Client(api_key=api_key)
    
    print("Streaming text response: ", end="", flush=True)
    response_stream = await client.aio.models.generate_content_stream(
        model=model,
        contents="Write a 3-sentence motivational quote about trade and global exploration."
    )
    async for chunk in response_stream:
        if chunk.text:
            print(chunk.text, end="", flush=True)
    print("\n")

async def test_structured_output():
    print("--- Test 2: Structured JSON Schema Output with Gemma 4 ---")
    api_key = os.environ.get("GEMINI_API_KEY")
    model = "gemma-4-31b-it"
    client = genai.Client(api_key=api_key)
    
    prompt = (
        "Classify the following industrial product: 'Industrial Solar Inverter'.\n"
        "Provide a classification role (choose from: component, finished system, consumable), "
        "and list 3 typical buyers."
    )
    
    config = gtypes.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema={
            "type": "object",
            "properties": {
                "role": {
                    "type": "string",
                    "enum": ["component", "finished system", "consumable"]
                },
                "buyers": {
                    "type": "array",
                    "items": {"type": "string"}
                }
            },
            "required": ["role", "buyers"]
        }
    )
    
    print("Requesting structured output...")
    response = await client.aio.models.generate_content(
        model=model,
        contents=prompt,
        config=config
    )
    print("Structured JSON Response received:")
    print(response.text)

async def main():
    await test_text_streaming()
    await test_structured_output()

if __name__ == "__main__":
    asyncio.run(main())
