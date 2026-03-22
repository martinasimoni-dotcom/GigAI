"""
Run the porthole window demo scenario.
Triggers the full GIGAI pipeline via the Fireflies webhook endpoint.
Run: python scripts/run_demo.py
"""
import asyncio
import json
import httpx
import sys
import os

BACKEND_URL = "http://localhost:8000"

async def trigger_demo():
    # Load scenario from file
    scenario_path = os.path.join(
        os.path.dirname(__file__), '..', 'backend', 'data', 'demo', 'porthole_scenario.json'
    )
    with open(scenario_path) as f:
        scenario = json.load(f)

    print("🚀 GIGAI Demo — Porthole Window Scenario")
    print("=" * 50)
    print(f"Meeting: {scenario['title']}")
    print(f"Participants: {', '.join(scenario['participants'])}")
    print()
    print("📤 Sending transcript to GIGAI backend...")

    async with httpx.AsyncClient(timeout=10) as client:
        # Check backend is running
        try:
            health = await client.get(f"{BACKEND_URL}/health")
            if health.status_code != 200:
                raise Exception("Backend not healthy")
            print("✅ Backend is running")
        except Exception as e:
            print(f"❌ Backend not reachable: {e}")
            print(f"   Start it with: cd backend && python main.py")
            sys.exit(1)

        # Trigger webhook
        response = await client.post(
            f"{BACKEND_URL}/webhooks/fireflies",
            json={
                "transcript": scenario["transcript"],
                "title": scenario["title"],
                "participants": scenario["participants"],
                "meeting_id": scenario["meeting_id"],
            }
        )
        print(f"✅ Webhook response: {response.json()}")

    print()
    print("⏳ Processing in background (Claude Haiku → Sonnet → DB → WebSocket)...")
    print("   This takes ~10-15 seconds")
    print()
    print("📱 Open your dashboard: http://localhost:5173")
    print("   Or on phone: http://YOUR_IP:5173")
    print()
    print("Expected result:")
    expected = scenario["expected_extraction"]
    print(f"  Material: {expected['material_from']} → {expected['material_to']}")
    print(f"  Quantity: {expected['quantity']} porthole windows")
    print(f"  Cost: €{expected['cost_estimate']:,}")
    print(f"  Confidence: ~{int(scenario['expected_confidence'] * 100)}%")

asyncio.run(trigger_demo())
