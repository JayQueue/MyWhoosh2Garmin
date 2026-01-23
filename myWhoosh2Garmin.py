import logging
from pathlib import Path

from fit_utils.fit_builder import MyWhooshFitBuilder
from garmin.utils import (
    authenticate_to_garmin,
    list_virtual_cycling_activities,
    upload_fit_file_to_garmin,
)
from strava.client import StravaClientBuilder
from strava.utils import sanitize_filename

SCRIPT_DIR = Path(__file__).resolve().parent
log_file_path = SCRIPT_DIR / "myWhoosh2Garmin.log"
RAW_FIT_FILE_PATH = SCRIPT_DIR / "data" / "raw"
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
file_handler = logging.FileHandler(log_file_path)
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)


def main():
    authenticate_to_garmin()
    client_builder = StravaClientBuilder()
    client = client_builder.with_auth().with_cookies().build()

    strava_retrieved_activities = client.get_filtered_activities()
    names, start_times = list_virtual_cycling_activities(last_n_days=7)

    def strip_timezone(dt):
        if dt.tzinfo is not None:
            return dt.replace(tzinfo=None)
        return dt

    start_times_no_tz = {strip_timezone(dt) for dt in start_times}

    new_activities = [
        activity
        for activity in strava_retrieved_activities
        if strip_timezone(activity.start_date_local) not in start_times_no_tz
    ]
    logger.info(
        f"Found {len(new_activities)} new virtual cycling activities to upload to Garmin."  # noqa: E501
    )

    for activity in new_activities:
        client.downloader.download_activity(activity.id)
        safe_name = sanitize_filename(activity.name)
        file_name = f"{safe_name}.json"
        input_path = RAW_FIT_FILE_PATH / file_name
        output_path = RAW_FIT_FILE_PATH.parent / "processed" / f"{safe_name}.fit"
        builder = MyWhooshFitBuilder(input_path)
        builder.build(output_path)
        upload_fit_file_to_garmin(output_path)
        try:
            output_path.unlink()
            logger.info(f"Deleted file: {output_path}")
        except Exception as e:
            logger.error(f"Failed to delete file {output_path}: {e}")


if __name__ == "__main__":
    main()
