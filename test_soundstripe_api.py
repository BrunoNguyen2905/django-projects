#!/usr/bin/env python3
"""
Simple test script to check Soundstripe API connectivity
"""

import sys
import django
from django.conf import settings

# Configure Django
if not settings.configured:
    from environs import Env
    env = Env()
    env.read_env()

    settings.configure(
        OPENAI_API_KEY=env.str("OPENAI_API_KEY", ""),
        SOUNDSTRIPE_API_KEY_DEVELOPMENT=env.str("SOUNDSTRIPE_API_KEY_DEVELOPMENT", ""),
        SECRET_KEY=env.str("SECRET_KEY", "test-key"),
        INSTALLED_APPS=['django.contrib.contenttypes'],
        USE_TZ=True,
    )
    django.setup()

from search_orchestration.clients.soundstripe_client import get_songs

def test_api_connectivity():
    """Test basic API connectivity with a simple query."""
    try:
        print("🔍 Testing Soundstripe API connectivity...")

        # Try a very simple query
        result = get_songs(q="test")

        print("✅ API call successful!")
        print(f"Response keys: {list(result.keys())}")

        if "data" in result:
            print(f"Data items: {len(result['data'])}")
            if result["data"]:
                print(f"First item keys: {list(result['data'][0].keys())}")
        else:
            print("❌ No 'data' key in response")

        return True

    except Exception as e:
        print(f"❌ API test failed: {e}")

        # Check if it's an auth error
        if "401" in str(e) or "unauthorized" in str(e).lower():
            print("   This appears to be an authentication error.")
            print("   Check your SOUNDSTRIPE_API_KEY_DEVELOPMENT in .env file")

        return False

if __name__ == "__main__":
    success = test_api_connectivity()
    sys.exit(0 if success else 1)