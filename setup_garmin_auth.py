#!/usr/bin/env python3
"""
Garmin Authentication Setup Script

This script helps you authenticate with Garmin Connect and generate
the GARMIN_TOKENS secret needed for GitHub Actions.

Usage:
    python setup_garmin_auth.py
"""

import logging

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

    # Load settings from .env or prompt for credentials
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
    print("   Secret name: GARMIN_TOKENS")
    print()
    print("-" * 70)
    print(token_string)
    print("-" * 70)
    print()
    print("⚠️  IMPORTANT: Keep this token secure! Don't share it publicly.")
    print()
    print("🔗 Add it to GitHub:")
    print("   1. Go to your repository → Settings → Secrets and variables → Actions")
    print("   2. Click 'New repository secret'")
    print("   3. Name: GARMIN_TOKENS")
    print("   4. Value: Paste the token string above")
    print()


if __name__ == "__main__":
    main()
