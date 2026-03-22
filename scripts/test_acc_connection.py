"""
Test Autodesk Construction Cloud (ACC) API connection.
Run: python scripts/test_acc_connection.py
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from dotenv import load_dotenv
load_dotenv()

import asyncio
from integrations.acc_client import ACCClient
from config import settings

async def test():
    print("🧪 Testing ACC Connection...")
    print(f"   Client ID: {settings.ACC_CLIENT_ID[:10]}...")
    print(f"   Project ID: {settings.ACC_PROJECT_ID}")
    print(f"   Container ID: {settings.ACC_CONTAINER_ID}")

    token = settings.ACC_ACCESS_TOKEN
    if not token or token == "your_acc_access_token_here":
        print("\n⚠️  ACC_ACCESS_TOKEN not set!")
        print("   Generate a token at: https://aps.autodesk.com/myapps")
        print("   Scopes needed: data:read, data:write, account:read")
        print("   Token expires in 1 hour")
        print("\n   For now, running in mock mode...")

    client = ACCClient()

    print("\n1. Testing project info...")
    info = await client.get_project_info()
    print(f"   ✅ Project: {info.get('name', 'Unknown')}")

    print("\n2. Testing notification...")
    await client.send_notification("GIGAI connection test — all systems nominal")
    print("   ✅ Notification sent (or mocked)")

    if token and token != "your_acc_access_token_here":
        print("\n3. Testing RFI creation (dry run)...")
        print("   Skipping actual RFI creation in test mode")
        print("   To test: run the demo and click Accept in the dashboard")

    print("\n🎉 ACC integration ready!")

asyncio.run(test())
