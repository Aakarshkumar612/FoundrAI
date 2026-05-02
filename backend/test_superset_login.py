import httpx
import asyncio

async def test():
    async with httpx.AsyncClient() as client:
        try:
            r = await client.post(
                'http://localhost:8088/api/v1/security/login', 
                json={'username': 'admin', 'password': 'foundr-admin-123', 'provider': 'db'}
            )
            print(f"Status: {r.status_code}")
            print(f"Response: {r.text}")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test())
