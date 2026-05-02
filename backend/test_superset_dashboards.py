import httpx
import asyncio

async def test():
    token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJmcmVzaCI6dHJ1ZSwiaWF0IjoxNzc3NzU2ODc5LCJqdGkiOiI1M2Y0OGE1Mi0zNDNiLTQ1MDQtYTNiYy03Y2QyYTQ0NDFjNmMiLCJ0eXBlIjoiYWNjZXNzIiwic3ViIjoxLCJuYmYiOjE3Nzc3NTY4NzksImV4cCI6MTc3Nzc1Nzc3OX0.uf6COASYvD2cPXq_MyNrnyhDmyLBI4lfP4vnSipEpRE"
    async with httpx.AsyncClient() as client:
        try:
            r = await client.get(
                'http://localhost:8088/api/v1/dashboard/', 
                headers={'Authorization': f'Bearer {token}'}
            )
            print(f"Status: {r.status_code}")
            print(f"Response: {r.text}")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test())
