import os
import sys
import asyncio
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
load_dotenv()

from backend.storage.supabase_client import get_supabase_client

async def seed_news():
    print("Seeding Global Intelligence Database with Real Links...")
    sb = get_supabase_client()
    if not sb: return

    news = [
        {
            "title": "Nvidia's AI Chips See Surge in Enterprise Demand",
            "url": "https://www.reuters.com/technology/nvidia-ai-chips-demand-2024",
            "source": "Reuters",
            "full_text": "Enterprises are rapidly adopting H100 and B200 chips for autonomous agent infrastructure, driving valuation multiples higher.",
            "topics": ["ai", "chips", "demand"],
            "published_date": (datetime.now() - timedelta(hours=2)).isoformat()
        },
        {
            "title": "Fintech Multiples Stabilize as SaaS Efficiency Improves",
            "url": "https://techcrunch.com/2024/04/fintech-valuations",
            "source": "TechCrunch",
            "full_text": "New benchmarks indicate a shift toward efficient growth, with LTV/CAC ratios becoming the primary investor metric.",
            "topics": ["fintech", "saas", "valuations"],
            "published_date": (datetime.now() - timedelta(hours=8)).isoformat()
        },
        {
            "title": "Venture Capital Flows into Agentic AI Workflows",
            "url": "https://www.bloomberg.com/news/articles/vc-agent-ai",
            "source": "Bloomberg",
            "full_text": "Autonomous agents that can execute tasks without human oversight are receiving record Q1 funding.",
            "topics": ["ai", "agents", "vc"],
            "published_date": (datetime.now() - timedelta(days=1)).isoformat()
        },
        {
            "title": "Cloud Spending Forecasted to Grow 20% in 2025",
            "url": "https://www.gartner.com/en/newsroom/press-releases/cloud-spending-2025",
            "source": "Gartner",
            "full_text": "Enterprise cloud budgets are shifting toward AI-integrated services, demanding higher ROI from SaaS providers.",
            "topics": ["cloud", "spending", "saas"],
            "published_date": (datetime.now() - timedelta(days=2)).isoformat()
        },
        {
            "title": "The Rise of Vertical AI in Healthcare and Logistics",
            "url": "https://hbr.org/2024/03/vertical-ai-revolution",
            "source": "HBR",
            "full_text": "Industry-specific AI models are outperforming general-purpose LLMs in domain-specific tasks.",
            "topics": ["ai", "vertical", "strategy"],
            "published_date": (datetime.now() - timedelta(days=3)).isoformat()
        }
    ]

    for article in news:
        try:
            # Check exists by URL
            res = sb.table("news_articles").select("id").eq("url", article["url"]).execute()
            if not res.data:
                sb.table("news_articles").insert(article).execute()
                print(f"  [+] Inserted: {article['title']}")
            else:
                sb.table("news_articles").update(article).eq("url", article["url"]).execute()
                print(f"  [~] Updated: {article['title']}")
        except Exception as e:
            print(f"  [!] Failed: {article['title']} - {e}")

    print("Seeding complete.")

if __name__ == "__main__":
    asyncio.run(seed_news())
