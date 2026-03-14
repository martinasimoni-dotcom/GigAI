#!/usr/bin/env python3
"""Fetches the ACC Issues container ID for the configured project."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

import os
import requests

CLIENT_ID = os.environ["ACC_CLIENT_ID"]
CLIENT_SECRET = os.environ["ACC_CLIENT_SECRET"]
ACCOUNT_ID = os.environ["ACC_ACCOUNT_ID"]
PROJECT_ID = os.environ["ACC_PROJECT_ID"]


def get_token():
    resp = requests.post(
        "https://developer.api.autodesk.com/authentication/v2/token",
        data={
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "grant_type": "client_credentials",
            "scope": "data:read data:write account:read account:write",
        },
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def main():
    token = get_token()
    headers = {"Authorization": f"Bearer {token}"}
    print(f"Token OK\n")

    # BIM360 Admin API — get project details including Issues container
    print("=== Fetching project details via BIM360 Admin API ===")
    resp = requests.get(
        f"https://developer.api.autodesk.com/hq/v1/accounts/{ACCOUNT_ID}/projects/{PROJECT_ID}",
        headers=headers,
    )
    print(f"Status: {resp.status_code}")

    if resp.status_code == 200:
        data = resp.json()
        # Issues container is in relationships
        relationships = data.get("relationships", {})
        issues = relationships.get("issues", {}).get("data", {})
        container_id = issues.get("id")
        if container_id:
            print(f"\nFound it!")
            print(f"ACC_ISSUES_CONTAINER_ID={container_id}")
            return
        else:
            print("Project found but no Issues container. Issues module may not be activated.")
            print("Go to your ACC project -> Project Admin -> Services -> activate Issues.")
    else:
        print(f"Response: {resp.text[:500]}")

    # Fallback: try ACC Admin v2
    print("\n=== Trying ACC Admin v2 ===")
    resp2 = requests.get(
        f"https://developer.api.autodesk.com/construction/admin/v1/projects/{PROJECT_ID}",
        headers=headers,
    )
    print(f"Status: {resp2.status_code}")
    if resp2.status_code == 200:
        import json
        print(json.dumps(resp2.json(), indent=2)[:1000])
    else:
        print(f"Response: {resp2.text[:300]}")


if __name__ == "__main__":
    main()
