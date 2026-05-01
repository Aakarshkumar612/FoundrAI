import os
import sys
from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

load_dotenv()

from backend.rag.pipeline import RAGPipeline
from backend.storage.supabase_client import get_supabase_client
from backend.config import get_settings

def diagnose_rag():
    print("Testing RAG Pipeline...")
    sb = get_supabase_client()
    if sb is None:
        print("❌ Supabase client failed to initialize.")
        return

    # Try a dummy founder ID (UUID format)
    founder_id = "00000000-0000-0000-0000-000000000000"
    rag = RAGPipeline(supabase_client=sb)

    print(f"Querying for: 'latest finance news' with founder_id: {founder_id}")
    try:
        results = rag.query("latest finance news", founder_id)
        print(f"✅ Query succeeded. Found {len(results)} chunks.")
        for i, res in enumerate(results):
            print(f"  [{i}] Source: {res.source}, Score: {res.score:.4f}, Text: {res.text[:100]}...")
    except Exception as e:
        print(f"❌ RAG Query failed: {e}")

    print("\nChecking news article count...")
    try:
        res = sb.table("news_articles").select("count", count="exact").execute()
        count = res.count if hasattr(res, 'count') else (len(res.data) if res.data else 0)
        print(f"✅ Total news articles in DB: {count}")
    except Exception as e:
        print(f"❌ Failed to count news articles: {e}")

if __name__ == "__main__":
    diagnose_rag()
