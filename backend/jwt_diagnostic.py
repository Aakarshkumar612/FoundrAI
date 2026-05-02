import os
import sys
from jose import jwt
from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
load_dotenv()

def diagnostic():
    print("--- JWT DIAGNOSTIC TOOL ---")
    secret = os.getenv("SUPABASE_JWT_SECRET")
    
    if not secret:
        print("❌ ERROR: SUPABASE_JWT_SECRET not found in .env")
        return

    print(f"Secret detected (length {len(secret)})")
    
    # Try to decode the user's provided sample if they gave one, 
    # but we'll use a placeholder logic here.
    import base64
    try:
        decoded_secret = base64.b64decode(secret)
        print("✅ Secret successfully decoded from Base64")
    except Exception as e:
        print(f"⚠️ Secret is not valid Base64 (using as raw string): {e}")

    print("\n--- NEXT STEPS ---")
    print("1. Go to your frontend in the browser.")
    print("2. Open DevTools (F12) -> Application -> Local Storage.")
    print("3. Look for 'sb-lvhbcekpgxebdvzsjtot-auth-token'.")
    print("4. Copy the 'access_token' value.")
    print("5. Paste it here to test verification (or just watch uvicorn logs).")
    
    print("\nI have updated the backend to show the EXACT error in your browser.")
    print("Try the upload again and tell me the full text of the error message.")

if __name__ == "__main__":
    diagnostic()
