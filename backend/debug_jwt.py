import os
from jose import jwt
from dotenv import load_dotenv

load_dotenv()

def debug_jwt():
    secret = os.getenv("SUPABASE_JWT_SECRET")
    # This is an example token from the user's frontend .env (eyJhbGci...)
    # But that's an ANON key. We need an AUTH token.
    # The user is logged in, so their browser has a token.
    
    print(f"Secret: {secret[:5]}...{secret[-5:]}")
    print(f"Secret length: {len(secret) if secret else 0}")

if __name__ == "__main__":
    debug_jwt()
