import os
import sys
import asyncio
from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

load_dotenv()

from backend.news.ingestion import ingest_news_batch, DEFAULT_TOPICS, GLOBAL_ID
from backend.storage.supabase_client import get_supabase_client
from backend.rag.pipeline import RAGPipeline
from backend.config import get_settings

async def init_news():
    print("🚀 Initializing Global News System...")
    settings = get_settings()
    sb = get_supabase_client()
    
    if not sb:
        print("❌ Supabase client failed.")
        return

    # 1. Create System Founder (UUID 0s) if not exists
    print(f"Checking for System Founder ({GLOBAL_ID})...")
    try:
        # Check if auth.users has it? No, founders table is enough for RAG FK
        # But wait, document_embeddings references founders(id) which references auth.users(id)
        # We can't insert into auth.users via client easily.
        # FIX: Remove foreign key constraint or use a real founder ID for system news?
        # Actually, let's just insert into 'founders' table directly if FK allows.
        # If migration 001 has FK to auth.users, this might fail.
        
        # Let's try to upsert into founders table
        res = sb.table("founders").upsert({
            "id": GLOBAL_ID,
            "email": "system@foundrai.local",
            "full_name": "System AI",
            "company_name": "FoundrAI Global"
        }).execute()
        print("✅ System Founder initialized.")
    except Exception as e:
        print(f"⚠️ Could not create system founder (FK might be active): {e}")
        print("Continuing anyway...")

    # 2. Run ingestion
    if not settings.newscatcher_api_key:
        print("❌ NEWSCATCHER_API_KEY missing in .env")
        return

    print(f"Running news ingestion for topics: {DEFAULT_TOPICS}...")
    rag = RAGPipeline(supabase_client=sb)
    try:
        result = await ingest_news_batch(
            topics=DEFAULT_TOPICS,
            api_key=settings.newscatcher_api_key,
            supabase_client=sb,
            rag_pipeline=rag
        )
        print(f"✅ Ingestion complete: {result}")
    except Exception as e:
        print(f"❌ Ingestion failed: {e}")

if __name__ == "__main__":
    asyncio.run(init_news())
