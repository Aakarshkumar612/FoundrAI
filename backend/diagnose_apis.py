import os
import sys
from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

load_dotenv()

def test_groq():
    print("Testing Groq API...")
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key or "your-groq" in api_key:
        print("❌ GROQ_API_KEY is not set or is a placeholder.")
        return
    
    try:
        from groq import Groq
        client = Groq(api_key=api_key)
        resp = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": "Hello"}],
            max_tokens=10
        )
        print("✅ Groq API is working!")
    except Exception as e:
        print(f"❌ Groq API failed: {e}")

def test_newscatcher():
    print("\nTesting NewsCatcher API...")
    api_key = os.getenv("NEWSCATCHER_API_KEY")
    if not api_key or "your-newscatcher" in api_key:
        print("❌ NEWSCATCHER_API_KEY is not set or is a placeholder.")
        return

    try:
        import httpx
        import asyncio
        
        async def call_api():
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    "https://api.newscatcherapi.com/v2/search",
                    params={"q": "startup", "lang": "en", "page_size": 1},
                    headers={"x-api-key": api_key}
                )
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("articles"):
                        print("✅ NewsCatcher API is working!")
                    else:
                        print("⚠️ NewsCatcher API returned no results (key might be valid but quota/topic issue).")
                else:
                    print(f"❌ NewsCatcher API failed: {resp.status_code} {resp.text}")

        asyncio.run(call_api())
    except Exception as e:
        print(f"❌ NewsCatcher API failed: {e}")

if __name__ == "__main__":
    test_groq()
    test_newscatcher()
