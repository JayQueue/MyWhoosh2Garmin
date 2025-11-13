import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Tuple

import garth
from garth.exc import GarthException, GarthHTTPError
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class GarminSettings(BaseSettings):
    """Configuration settings for Garmin API client."""

    garmin_username: str = Field(..., validation_alias="GARMIN_USERNAME")
    garmin_password: str = Field(..., validation_alias="GARMIN_PASSWORD")
    garmin_tokens_path: Path = Field(
        default=Path(__file__).parent.parent / ".garth",
    )

    model_config = SettingsConfigDict(
        env_file=Path(__file__).parent.parent / ".env", extra="ignore"
    )


def get_credentials_for_garmin(garmin_settings: GarminSettings = GarminSettings()):
    """
    Prompt the user for Garmin credentials and authenticate using Garth.

    Returns:
        None

    Exits:
        Exits with status 1 if authentication fails.
    """
    logger.info("Authenticating...")
    try:
        garth.login(
            garmin_settings.garmin_username,
            garmin_settings.garmin_password,
            prompt_mfa=lambda: input("Enter MFA code: "),
        )
        garth.save(garmin_settings.garmin_tokens_path)
        print()
        logger.info("Successfully authenticated!")
    except GarthHTTPError:
        logger.info("Wrong credentials. Please check username and password.")
        sys.exit(1)


def authenticate_to_garmin(garmin_settings: GarminSettings = GarminSettings()):
    """
    Authenticate the user to Garmin by checking for existing tokens and
    resuming the session, or prompting for credentials if no session
    exists or the session is expired.

    Returns:
        None

    Exits:
        Exits with status 1 if authentication fails.
    """
    try:
        if garmin_settings.garmin_tokens_path.exists():
            garth.resume(garmin_settings.garmin_tokens_path)
            try:
                logger.info(f"Authenticated as: {garth.client.username}")
            except GarthException:
                logger.info("Session expired. Re-authenticating...")
                get_credentials_for_garmin(garmin_settings)
        else:
            logger.info("No existing session. Please log in.")
            get_credentials_for_garmin(garmin_settings)
    except GarthException as e:
        logger.info(f"Authentication error: {e}")
        sys.exit(1)


def upload_fit_file_to_garmin(new_file_path: Path):
    """
    Upload a .fit file to Garmin using the Garth client.

    Args:
        new_file_path (Path): The path to the .fit file to upload.

    Returns:
        None
    """
    try:
        if new_file_path and new_file_path.exists():
            with open(new_file_path, "rb") as f:
                uploaded = garth.client.upload(f)
                logger.debug(uploaded)
        else:
            logger.info(f"Invalid file path: {new_file_path}.")
    except GarthHTTPError:
        logger.info("Duplicate activity found on Garmin Connect.")


def list_virtual_cycling_activities(
    last_n_days: int = 30,
) -> Tuple[List[str], List[datetime]]:
    """Return two lists: activity names and start times of virtual cycling activities from Garmin Connect."""
    logger.info(
        f"Retrieving virtual cycling activities from the last {last_n_days} days..."
    )
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=last_n_days)
    activities = garth.connectapi(
        "/activitylist-service/activities/search/activities",
        params={
            "startDate": start_date.strftime("%Y-%m-%d"),
            "endDate": end_date.strftime("%Y-%m-%d"),
        },
    )
    names, start_times = [], []
    for activity in activities:
        if activity.get("activityType", {}).get("typeKey") == "virtual_ride":
            names.append(activity["activityName"])
            start_time_str = activity.get("startTimeLocal", "")
            try:
                start_time = datetime.strptime(start_time_str, "%Y-%m-%d %H:%M:%S")
            except (ValueError, TypeError):
                start_time = None
            start_times.append(start_time)
            logger.debug(
                f"Found virtual cycling activity: {activity['activityName']} at {activity.get('startTimeLocal', '')} with elapsed time {activity.get('elapsedTime', '')}."
            )
    return names, start_times


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    authenticate_to_garmin()
    # Example usage:
    list_virtual_cycling_activities()
