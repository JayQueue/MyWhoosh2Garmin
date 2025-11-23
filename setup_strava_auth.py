#!/usr/bin/env python3
"""
Strava Authentication Setup Script

This script helps you authenticate with Strava API and generate
the OAuth tokens needed for GitHub Actions.

Before running this script:
1. Create a Strava API application at https://www.strava.com/settings/api
2. Set the authorization callback domain to: localhost
3. Note your Client ID and Client Secret

Usage:
    python setup_strava_auth.py
"""

import json
import logging
from pathlib import Path

from strava.client import StravaAuth, StravaSettings

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def main():
    """Main function to set up Strava authentication."""
    print("=" * 70)
    print("🚴 Strava API Authentication Setup")
    print("=" * 70)
    print()
    print("📝 Before continuing, make sure you have:")
    print("   1. Created a Strava API application at:")
    print("      https://www.strava.com/settings/api")
    print("   2. Set authorization callback domain to: localhost")
    print()

    # Prompt for Client ID and Secret
    client_id = input("Enter your Strava Client ID: ").strip()
    client_secret = input("Enter your Strava Client Secret: ").strip()

    if not client_id or not client_secret:
        logger.error("❌ Client ID and Secret are required!")
        return

    # Create temporary settings with user input
    env_file = Path(__file__).parent / ".env"

    # Read existing .env or create from template
    env_content = {}
    if env_file.exists():
        with open(env_file, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    env_content[key] = value.strip("\"'")

    # Update with new credentials
    env_content["STRAVA_CLIENT_ID"] = client_id
    env_content["STRAVA_CLIENT_SECRET"] = client_secret

    # Write back to .env
    with open(env_file, "w") as f:
        f.write("# Strava API Configuration\n")
        for key, value in env_content.items():
            f.write(f'{key}="{value}"\n')

    print()
    print("🔐 Starting OAuth flow...")
    print()

    # Initialize settings which will now load from .env
    settings = StravaSettings()
    auth = StravaAuth(settings)

    # Perform OAuth flow
    auth._perform_oauth_flow()

    # Load the saved tokens
    token_file = Path(__file__).parent / "strava_tokens.json"
    if not token_file.exists():
        logger.error("❌ Token file not created. Authentication may have failed.")
        return

    with open(token_file, "r") as f:
        tokens = json.load(f)

    print()
    print("=" * 70)
    print("✅ Authentication Successful!")
    print("=" * 70)
    print()
    print("📋 Add these as GitHub Secrets in your repository:")
    print("   (Settings → Secrets and variables → Actions → New repository secret)")
    print()
    print("-" * 70)
    print("Secret: STRAVA_CLIENT_ID")
    print(f"Value:  {client_id}")
    print("-" * 70)
    print("Secret: STRAVA_CLIENT_SECRET")
    print(f"Value:  {client_secret}")
    print("-" * 70)
    print("Secret: STRAVA_ACCESS_TOKEN")
    print(f"Value:  {tokens.get('access_token', 'N/A')}")
    print("-" * 70)
    print("Secret: STRAVA_EXPIRES_AT")
    print(f"Value:  {tokens.get('expires_at', 'N/A')}")
    print("-" * 70)
    print("Secret: STRAVA_EXPIRES_IN")
    print(f"Value:  {tokens.get('expires_in', 'N/A')}")
    print("-" * 70)
    print("Secret: STRAVA_REFRESH_TOKEN")
    print(f"Value:  {tokens.get('refresh_token', 'N/A')}")
    print("-" * 70)
    print()
    print("⚠️  IMPORTANT: Keep these tokens secure! Don't share them publicly.")
    print()
    print("💾 Tokens have also been saved to: strava_tokens.json")
    print("   (This file is gitignored for your security)")
    print()


if __name__ == "__main__":
    main()
