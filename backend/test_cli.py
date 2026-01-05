"""Test GitHub client authentication and basic functionality."""

import asyncio
from backend.core.github_client import GitHubClient
from backend.core.logger import setup_logging

# Setup logging
setup_logging()

async def test_client():
    """Test GitHub client."""
    print("Testing GitHub Client...")
    
    # Initialize client
    client = GitHubClient()
    
    # Test authentication
    print("\n1. Testing authentication...")
    try:
        await client.check_authentication()
        print("✅ Authentication successful!")
    except Exception as e:
        print(f"❌ Authentication failed: {e}")
        return
    
    # Check rate limit status
    print("\n2. Checking rate limit status...")
    status = client.rate_limit_status
    print(f"✅ Rate limit: {status['remaining']} remaining")
    print(f"   Reset at: {status['reset_at']}")
    
    print("\n✅ All GitHub client tests passed!")

if __name__ == "__main__":
    asyncio.run(test_client())