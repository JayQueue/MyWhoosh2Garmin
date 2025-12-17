"""
Strava API client for downloading virtual ride activities with 'MyWhoosh' in name.

Handles authentication, session management, and tracks downloaded activities in SQLite.
"""

import json
import os
import sqlite3
import requests
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional
from urllib.parse import parse_qs, urlparse

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from requests import Session


class StravaSettings(BaseSettings):
    """Configuration settings for Strava API client."""
    
    client_id: str = Field(..., validation_alias="CLIENT_ID")
    client_secret: str = Field(..., validation_alias="CLIENT_SECRET")
    token_url: str = "https://www.strava.com/oauth/token"
    auth_base_url: str = "https://www.strava.com/oauth/authorize"
    token_file: str = "strava_tokens.json"
    cookie_file: str = "cookie.json"
    activities_url: str = "https://www.strava.com/api/v3/athlete/activities"
    database_file: str = "strava.db"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


class TokenData(BaseModel):
    """Model for storing Strava API token data."""
    
    access_token: str
    refresh_token: str
    expires_at: datetime

    @classmethod
    def from_json(cls, data: dict):
        """Create TokenData instance from JSON response."""
        if isinstance(data.get("expires_at"), int):
            data["expires_at"] = datetime.fromtimestamp(data["expires_at"])
        return cls(**data)


class ActivityDetails(BaseModel):
    """Model representing Strava activity details."""
    
    id: int
    name: str
    start_date: datetime
    type: str


class ActivityDatabase:
    """Database handler for tracking downloaded activities."""
    
    def __init__(self, db_file: str):
        self.db_file = db_file
        self.conn = sqlite3.connect(db_file)
        self._create_table()

    def _create_table(self):
        """Create database table if it doesn't exist."""
        query = """
        CREATE TABLE IF NOT EXISTS downloaded_activities (
            activity_id INTEGER PRIMARY KEY,
            downloaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
        self.conn.execute(query)
        self.conn.commit()

    def is_downloaded(self, activity_id: int) -> bool:
        """Check if activity is already downloaded."""
        cursor = self.conn.execute(
            "SELECT 1 FROM downloaded_activities WHERE activity_id = ?",
            (activity_id,)
        )
        return bool(cursor.fetchone())

    def mark_downloaded(self, activity_id: int):
        """Mark an activity as downloaded."""
        self.conn.execute(
            "INSERT OR IGNORE INTO downloaded_activities (activity_id) VALUES (?)",
            (activity_id,)
        )
        self.conn.commit()

    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


class StravaAuth:
    """Handles Strava OAuth2 authentication and token management."""
    
    def __init__(self, settings: StravaSettings):
        self.settings = settings
        self.token_data: Optional[TokenData] = None
        self.session = Session()
        self._initialize_session()

    def _initialize_session(self):
        """Initialize requests session with valid token."""
        if self._load_tokens() and self._is_token_valid():
            self.session.headers.update({
                "Authorization": f"Bearer {self.token_data.access_token}"
            })

    def _is_token_valid(self) -> bool:
        """Check if access token is still valid."""
        if not self.token_data:
            return False

        if isinstance(self.token_data.expires_at, int):
            self.token_data.expires_at = datetime.fromtimestamp(
                self.token_data.expires_at
            )

        return datetime.now() < self.token_data.expires_at - timedelta(minutes=5)

    def authenticate(self) -> None:
        """Main authentication flow with automatic token refresh."""
        if not self._is_token_valid():
            if self.token_data and self.token_data.refresh_token:
                try:
                    self.refresh_token()
                except requests.HTTPError as e:
                    if e.response.status_code == 400:
                        print("Refresh token expired, re-authenticating...")
                        self._perform_oauth_flow()
                    else:
                        raise
            else:
                self._perform_oauth_flow()

    def _perform_oauth_flow(self) -> None:
        """Perform OAuth2 authorization code flow."""
        auth_url = (
            f"{self.settings.auth_base_url}?"
            f"client_id={self.settings.client_id}&"
            "response_type=code&"
            "redirect_uri=http://localhost/exchange_token&"
            "scope=activity:read_all"
        )
        print(f"🔗 Authorize here: {auth_url}")
        redirect_url = input("🔄 Paste callback URL: ")
        self._fetch_token(redirect_url)

    def _fetch_token(self, redirect_url: str) -> None:
        """Exchange authorization code for access token."""
        code = parse_qs(urlparse(redirect_url).query).get("code")
        if not code:
            raise ValueError("Authorization code missing")

        response = requests.post(
            self.settings.token_url,
            data={
                "client_id": self.settings.client_id,
                "client_secret": self.settings.client_secret,
                "code": code[0],
                "grant_type": "authorization_code",
            },
        )
        response.raise_for_status()
        self._save_tokens(response.json())

    def _save_tokens(self, token_data: dict) -> None:
        """Save tokens to file and update session."""
        with open(self.settings.token_file, "w") as f:
            json.dump(token_data, f)
        self.token_data = TokenData.from_json(token_data)
        self._initialize_session()

    def _load_tokens(self) -> bool:
        """Load tokens from storage file."""
        if os.path.exists(self.settings.token_file):
            with open(self.settings.token_file, "r") as f:
                raw_data = json.load(f)
            self.token_data = TokenData.from_json(raw_data)
            return True
        return False

    def refresh_token(self) -> None:
        """Refresh access token using refresh token."""
        if not self.token_data or not self.token_data.refresh_token:
            raise ValueError("No refresh token available")

        response = requests.post(
            self.settings.token_url,
            data={
                "client_id": self.settings.client_id,
                "client_secret": self.settings.client_secret,
                "grant_type": "refresh_token",
                "refresh_token": self.token_data.refresh_token,
            },
        )
        response.raise_for_status()
        self._save_tokens(response.json())


class CookieManager:
    """Manages HTTP cookies for persistent session."""
    
    def __init__(self, cookie_file: str):
        self.cookie_file = cookie_file
        self.session = Session()

    def load_cookies(self) -> None:
        """Load cookies from storage file."""
        if os.path.exists(self.cookie_file):
            with open(self.cookie_file, "r") as f:
                cookies = json.load(f)
            for name, value in cookies.items():
                self.session.cookies.set(name, value)


class ActivityDownloader:
    """Handles activity file downloads with Chrome-like headers."""
    
    CHROME_HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/119.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,"
                  "image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1"
    }

    def __init__(
        self, 
        session: Session, 
        database: ActivityDatabase,
        auth: Optional["StravaAuth"] = None
    ):
        self.session = session
        self.db = database
        self.auth = auth

    def download_activity(self, activity_id: int) -> bool:
        """Download activity file with retry logic."""
        try:
            return self._download_attempt(activity_id)
        except requests.HTTPError as e:
            if e.response.status_code == 401 and self.auth:
                print("Token expired during download, refreshing...")
                try:
                    self.auth.refresh_token()
                    return self._download_attempt(activity_id)
                except requests.HTTPError as refresh_error:
                    if refresh_error.response.status_code == 400:
                        print("Refresh token expired, re-authenticating...")
                        self.auth._perform_oauth_flow()
                        return self._download_attempt(activity_id)
                    raise
            raise

    def _download_attempt(self, activity_id: int) -> bool:
        """Perform single download attempt for an activity."""
        if self.db.is_downloaded(activity_id):
            return False

        response = self.session.get(
            f"https://www.strava.com/activities/{activity_id}/export_original",
            stream=True,
            headers=self.CHROME_HEADERS
        )
        response.raise_for_status()

        filename = f"activity_{activity_id}_original.fit"
        with open(filename, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        self.db.mark_downloaded(activity_id)
        print(f"✅ Downloaded {filename}")
        return True


class StravaClient:
    """Main client for interacting with Strava API."""
    
    def __init__(self, auth: StravaAuth, downloader: ActivityDownloader):
        self.auth = auth
        self.downloader = downloader

    def get_filtered_activities(self) -> List[ActivityDetails]:
        """Retrieve filtered list of activities."""
        self.auth.authenticate()

        try:
            response = self.auth.session.get(
                self.auth.settings.activities_url,
                params={"per_page": 100}
            )
            response.raise_for_status()

        except requests.HTTPError as e:
            if e.response.status_code == 401:
                print("Token expired during request, refreshing...")
                self.auth.refresh_token()
                return self.get_filtered_activities()
            raise

        return [
            ActivityDetails(**activity)
            for activity in response.json()
            if activity.get("type") == "VirtualRide"
            and "MyWhoosh" in activity.get("name", "")
        ]


class StravaClientBuilder:
    """Builder pattern implementation for StravaClient."""
    
    def __init__(self):
        self.settings = StravaSettings()
        self.auth = StravaAuth(self.settings)
        self.cookie_manager = CookieManager(self.settings.cookie_file)
        self.database = ActivityDatabase(self.settings.database_file)

    def with_auth(self) -> "StravaClientBuilder":
        """Authenticate with Strava API."""
        self.auth.authenticate()
        return self

    def with_cookies(self) -> "StravaClientBuilder":
        """Load stored cookies."""
        self.cookie_manager.load_cookies()
        return self

    def build(self) -> StravaClient:
        """Build configured StravaClient instance."""
        downloader = ActivityDownloader(
            self.auth.session,
            self.database,
            self.auth
        )
        return StravaClient(self.auth, downloader)

    def cleanup(self):
        """Cleanup resources."""
        if hasattr(self, 'database') and self.database:
            self.database.close()


if __name__ == "__main__":
    client_builder = None
    try:
        client_builder = StravaClientBuilder()
        client = client_builder.with_auth().with_cookies().build()

        all_activities = client.get_filtered_activities()
        new_activities = [
            a for a in all_activities
            if not client.downloader.db.is_downloaded(a.id)
        ]

        if not new_activities:
            print("No new activities found")
            exit(0)

        print("\n🏆 New Virtual Rides with 'MyWhoosh' in name:")
        for activity in new_activities:
            date_str = activity.start_date.strftime("%Y-%m-%d %H:%M")
            print(f"📅 {date_str} - {activity.name} (ID: {activity.id})")

        new_downloads = 0
        for activity in new_activities:
            if client.downloader.download_activity(activity.id):
                new_downloads += 1

        print("\nDownload summary:")
        print(f"• New activities downloaded: {new_downloads}")
        print(f"• Already existed: {len(all_activities) - len(new_activities)}")
        print(f"• Total processed: {len(all_activities)}")

    except KeyboardInterrupt:
        print("\n⚠️  Interrupted by user")
        exit(1)
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        exit(1)
    finally:
        if client_builder:
            client_builder.cleanup()
