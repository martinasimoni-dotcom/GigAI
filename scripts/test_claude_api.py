"""
Test Claude API connection with both Haiku and Sonnet models.
Run: python scripts/test_claude_api.py
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from dotenv import load_dotenv
load_dotenv()

import asyncio
from integrations.claude_client import ClaudeClient

async def test():
    print("🧪 Testing Claude API...")
    client = ClaudeClient()

    # Test Haiku (normalization)
    print("\n1. Testing Claude Haiku (normalization)...")
    test_transcript = "Marco: We need to change the attic porthole windows from PVC to wood. There are 6 windows at €390 each."
    result = await client.extract_with_haiku(test_transcript)
    print(f"   ✅ Haiku extracted: {result}")

    # Test Sonnet (proposal generation)
    print("\n2. Testing Claude Sonnet (proposal generation)...")
    context = {
        "change": result,
        "project": {"name": "Sea house"},
        "meeting_title": "Design Review",
    }
    proposal = await client.generate_proposal_with_sonnet(context)
    print(f"   ✅ Sonnet generated proposal: {proposal.get('title', 'No title')}")
    print(f"   Cost: €{proposal.get('cost_analysis', {}).get('total_eur', 0):,}")
    print(f"   Actions: {len(proposal.get('actions', []))} queued")

    print("\n🎉 Claude API is working correctly!")

asyncio.run(test())
