import os
import httpx
import asyncio
from dotenv import load_dotenv

load_dotenv()

async def test_nc():
    key = os.getenv("NEWSCATCHER_API_KEY")
    if not key:
        print("❌ NC_KEY_MISSING")
        return
    
    print(f"Testing with key starting: {key[:5]}...")
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.get(
                "https://api.newscatcherapi.com/v2/search",
                params={"q": "startup", "lang": "en", "page_size": 1},
                headers={"x-api-key": key}
            )
            if resp.status_code == 200:
                print("✅ NewsCatcher API is Working!")
            elif resp.status_code == 403:
                print(f"❌ Invalid API Key (403 Forbidden)")
            else:
                print(f"❌ API Error: {resp.status_code} {resp.text}")
        except Exception as e:
            print(f"❌ Connection Failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_nc())
