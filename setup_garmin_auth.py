#!/usr/bin/env python3
"""
Garmin Authentication Setup Script

This script helps you authenticate with Garmin Connect and generate
the GARMIN_TOKENS secret needed for GitHub Actions.

Usage:
    python setup_garmin_auth.py
"""

import logging
from pathlib import Path

import garth

from garmin.utils import GarminSettings, get_credentials_for_garmin

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def main():
    """Main function to set up Garmin authentication."""
    print("=" * 70)
    print("🏃 Garmin Connect Authentication Setup")
    print("=" * 70)
    print()

    # Prompt for Garmin credentials
    username = input("Enter your Garmin Connect Username (Email): ").strip()
    password = input("Enter your Garmin Connect Password: ").strip()

    if not username or not password:
        logger.error("❌ Username and Password are required!")
        return

    # Create/update .env file with credentials
    env_file = Path(__file__).parent / ".env"
    env_content = {}
    if env_file.exists():
        with open(env_file, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    env_content[key.strip()] = value.strip("\"'")

    env_content["GARMIN_USERNAME"] = username
    env_content["GARMIN_PASSWORD"] = password

    with open(env_file, "w") as f:
        for key, value in env_content.items():
            f.write(f'{key}="{value}"\n')

    print()
    print("🔐 Starting authentication...")
    print()

    # Load settings from .env
    settings = GarminSettings()

    # Authenticate and save tokens
    get_credentials_for_garmin(settings)

    # Dump tokens as string for GitHub secrets
    token_string = garth.client.dumps()

    print()
    print("=" * 70)
    print("✅ Authentication Successful!")
    print("=" * 70)
    print()
    print("📋 Copy the following token string and save it as a GitHub Secret:")
    print("   This is the recommended way to authenticate in CI/CD environments.")
    print()
    print("-" * 70)
    print("Secret: GARMIN_TOKENS")
    print(token_string)
    print("-" * 70)
    print()
    print("Alternatively, you can use your username and password as secrets:")
    print("Secret: GARMIN_USERNAME")
    print(f"Value:  {username}")
    print("Secret: GARMIN_PASSWORD")
    print(f"Value:  {password}")
    print()
    print("⚠️  IMPORTANT: Keep these tokens and credentials secure!")
    print()
    print("🔗 Add it to GitHub:")
    print("   1. Go to your repository → Settings → Secrets and variables → Actions")
    print("   2. Click 'New repository secret'")
    print("   3. Name: GARMIN_TOKENS")
    print("   4. Value: Paste the token string above")
    print()


if __name__ == "__main__":
    main()
