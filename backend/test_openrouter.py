import asyncio
import os
import json
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()

async def test_search():
    client = AsyncOpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=os.getenv("OPENROUTER_API_KEY"),
    )

    try:
        response = await client.chat.completions.create(
            model="perplexity/sonar-pro",
            messages=[
                {"role": "user", "content": "Find the latest news about OpenAI. Return your response in JSON with 'title', 'summary', 'url', and 'image_url' fields where 'image_url' is a link to an image associated with the news if you can find one. Otherwise leave it null."}
            ],
            extra_headers={
                "HTTP-Referer": "http://localhost",
                "X-Title": "Test",
            }
        )
        print("Response Content:")
        print(response.choices[0].message.content)
        
        # OpenRouter usually puts citations in the raw response block if supported
        raw_dict = response.model_dump()
        print("\nFull Response Dump:")
        print(json.dumps(raw_dict, indent=2))
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_search())
