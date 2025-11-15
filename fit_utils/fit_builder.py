import json
from datetime import datetime
from pathlib import Path
from typing import List

from fit_tool.fit_file_builder import FitFileBuilder
from fit_tool.profile.messages.activity_message import ActivityMessage
from fit_tool.profile.messages.event_message import EventMessage
from fit_tool.profile.messages.file_creator_message import FileCreatorMessage
from fit_tool.profile.messages.file_id_message import FileIdMessage
from fit_tool.profile.messages.lap_message import LapMessage
from fit_tool.profile.messages.record_message import RecordMessage
from fit_tool.profile.messages.session_message import SessionMessage
from fit_tool.profile.profile_type import (
    Event,
    EventType,
    FileType,
    GarminProduct,
    Intensity,
    Manufacturer,
    Sport,
    SubSport,
)
from pydantic import BaseModel, ConfigDict, Field, computed_field, model_validator


class ActivityData(BaseModel):
    """Model for MyWhoosh activity JSON data."""

    model_config = ConfigDict(
        extra="forbid",  # Forbid extra fields
        validate_assignment=True,  # Validate on attribute assignment
        str_to_lower=True,  # Convert strings to lowercase
        strict=True,  # Enforce strict type checking
    )

    # From activity metadata api
    name: str = Field(default_factory=str, alias="strava_activity_name")
    id: int = Field(..., alias="strava_activity_id")
    activity_distance: float
    moving_time: int
    elapsed_time: int
    total_elevation_gain: float
    type: str
    start_date: datetime | int
    start_date_local: datetime | int
    timezone: str
    utc_offset: float
    average_speed: float
    max_speed: float
    average_cadence: float
    average_watts: float
    max_watts: int
    weighted_average_watts: int
    kilojoules: float
    average_heartrate: float
    max_heartrate: float
    calories: float

    # From streams
    lat: List[float]
    long: List[float]
    watts: List[int]
    cadence: List[int]
    velocity_smooth: List[float]
    heartrate: List[int]
    time: List[int]
    heartrates: List[int]
    distance: List[float]
    grade_smooth: List[float] | None
    altitude: List[float] | None

    @model_validator(mode="after")
    def validate_streams(self) -> "ActivityData":
        """Validate that all stream lists have the same length and records exist."""
        # Collect all stream attributes that are lists
        stream_attrs = [
            "lat",
            "long",
            "watts",
            "cadence",
            "velocity_smooth",
            "heartrate",
            "time",
            "heartrates",
            "distance",
        ]
        # Optionally include nullable streams if present
        if self.grade_smooth is not None:
            stream_attrs.append("grade_smooth")
        if self.altitude is not None:
            stream_attrs.append("altitude")

        lengths = [
            len(getattr(self, attr))
            for attr in stream_attrs
            if getattr(self, attr) is not None
        ]
        if lengths and any(length != lengths[0] for length in lengths):
            raise ValueError("All stream lists must have the same length.")

        return self

    @property
    def stream_length(self) -> int:
        return len(self.time)

    @property
    def elapsed_time(self) -> int:
        """Get elapsed time in milliseconds."""
        return self.elapsed_time * 1000

    @classmethod
    def from_json_file(cls, json_file_path: str) -> "ActivityData":
        """Load and parse the JSON activity file into the model."""
        with open(json_file_path, "r") as f:
            raw_data = json.load(f)

        # Extract metadata and streams
        metadata = raw_data.get("metadata", {})
        streams = raw_data.get("streams", {})

        # Combine metadata fields with stream data
        combined_data = {
            # Metadata fields (activity summary)
            "strava_activity_name": metadata.get("name", ""),
            "strava_activity_id": metadata.get("id"),
            "activity_distance": metadata.get("distance"),
            "moving_time": metadata.get("moving_time"),
            "elapsed_time": metadata.get("elapsed_time"),
            "total_elevation_gain": metadata.get("total_elevation_gain"),
            "type": metadata.get("type"),
            "start_date": datetime.fromisoformat(metadata.get("start_date"))
            if metadata.get("start_date")
            else None,
            "start_date_local": datetime.fromisoformat(metadata.get("start_date_local"))
            if metadata.get("start_date_local")
            else None,
            "timezone": metadata.get("timezone"),
            "utc_offset": metadata.get("utc_offset"),
            "average_speed": metadata.get("average_speed"),
            "max_speed": metadata.get("max_speed"),
            "average_cadence": metadata.get("average_cadence"),
            "average_watts": metadata.get("average_watts"),
            "max_watts": metadata.get("max_watts"),
            "weighted_average_watts": metadata.get("weighted_average_watts"),
            "kilojoules": metadata.get("kilojoules"),
            "average_heartrate": metadata.get("average_heartrate"),
            "max_heartrate": metadata.get("max_heartrate"),
            "calories": metadata.get("calories"),
            # Stream data (time series)
            # Extract and separate lat/long from latlng pairs
            "lat": [],
            "long": [],
        }

        # Stream data (time series)
        # Extract and separate lat/long from latlng pairs
        latlng_data = streams.get("latlng", {}).get("data", [])
        if latlng_data:
            lat_values, long_values = zip(*latlng_data)
            combined_data["lat"] = list(lat_values)
            combined_data["long"] = list(long_values)
        else:
            combined_data["lat"] = []
            combined_data["long"] = []

        combined_data.update(
            {
                "watts": streams.get("watts", {}).get("data", []),
                "cadence": streams.get("cadence", {}).get("data", []),
                "velocity_smooth": streams.get("velocity_smooth", {}).get("data", []),
                "heartrate": streams.get("heartrate", {}).get("data", []),
                "time": streams.get("time", {}).get("data", []),
                "heartrates": streams.get("heartrate", {}).get("data", []),
                "distance": streams.get("distance", {}).get("data", []),
                "grade_smooth": streams.get("grade_smooth", {}).get("data"),
                "altitude": streams.get("altitude", {}).get("data"),
            }
        )

        return cls(**combined_data)

    @computed_field
    def max_cadence(self) -> int:
        return max(self.cadence) if self.cadence else 0

    @computed_field
    @property
    def start_ts_miliseconds(self) -> int:
        return round(self.start_date.timestamp()) * 1000


class MyWhooshFitBuilder:
    """Convert MyWhoosh activity JSON to FIT file format."""

    def __init__(self, json_file_path: str):
        """Initialize with path to MyWhoosh JSON file."""
        self.json_path = json_file_path
        self.activity_data = ActivityData.from_json_file(json_file_path)
        self.builder = FitFileBuilder(auto_define=True)
        self.end_date_fit_ts = (
            self.activity_data.start_ts_miliseconds
            + 1000 * self.activity_data.stream_length
        )

    def _add_file_id(self):
        """Add file_id message."""
        file_id = FileIdMessage()
        file_id.type = FileType.ACTIVITY
        file_id.manufacturer = Manufacturer.GARMIN.value
        file_id.product = GarminProduct.EDGE_530.value
        file_id.serial_number = 3313379353
        file_id.time_created = self.activity_data.start_ts_miliseconds
        self.builder.add(file_id)

    def _add_file_creator(self):
        """Add file creator message."""
        file_creator = FileCreatorMessage()
        file_creator.software_version = 29
        self.builder.add(file_creator)

    def _add_event(self, timestamp: int, event: Event, event_type: EventType):
        """Add event message."""
        event_msg = EventMessage()
        event_msg.timestamp = timestamp
        event_msg.event = event
        event_msg.event_type = event_type
        self.builder.add(event_msg)

    def _add_records(self):
        """Add all record messages from the activity data."""
        if not self.activity_data or self.activity_data.stream_length == 0:
            return

        for i in range(self.activity_data.stream_length):
            record = RecordMessage()

            # Timestamp - time[i] est en secondes, on convertit en millisecondes
            record.timestamp = self.activity_data.start_ts_miliseconds + (
                self.activity_data.time[i] * 1000
            )

            # Position (lat/long en degrés)
            record.position_lat = self.activity_data.lat[i]
            record.position_long = self.activity_data.long[i]

            # Heart rate
            record.heart_rate = self.activity_data.heartrate[i]

            # Cadence
            record.cadence = self.activity_data.cadence[i]

            # Distance (meters)
            record.distance = self.activity_data.distance[i]

            # Altitude (meters) - optional
            if self.activity_data.altitude is not None:
                record.altitude = self.activity_data.altitude[i]

            # Power (watts)
            record.power = self.activity_data.watts[i]

            # Speed (m/s)
            record.speed = self.activity_data.velocity_smooth[i]

            self.builder.add(record)

    def _add_lap(self):
        """Add lap message."""
        lap = LapMessage()

        lap.timestamp = (
            self.activity_data.start_ts_miliseconds + self.activity_data.elapsed_time
        )
        lap.start_time = self.activity_data.start_ts_miliseconds
        lap.total_elapsed_time = self.activity_data.elapsed_time
        lap.total_timer_time = self.activity_data.elapsed_time
        lap.intensity = Intensity.ACTIVE
        lap.total_distance = self.activity_data.activity_distance
        lap.avg_heart_rate = int(self.activity_data.average_heartrate)
        lap.max_heart_rate = int(self.activity_data.max_heartrate)

        lap.avg_cadence = int(self.activity_data.average_cadence)
        lap.max_cadence = int(self.activity_data.max_cadence)

        lap.avg_power = int(self.activity_data.average_watts)
        lap.max_power = int(self.activity_data.max_watts)

        lap.avg_speed = self.activity_data.average_speed
        lap.max_speed = self.activity_data.max_speed

        lap.total_calories = int(self.activity_data.calories)
        lap.sport = Sport.CYCLING
        lap.sub_sport = SubSport.VIRTUAL_ACTIVITY

        self.builder.add(lap)

    def _add_session(self):
        """Add session message."""
        session = SessionMessage()

        session.timestamp = self.end_date_fit_ts
        session.start_time = self.activity_data.start_ts_miliseconds
        session.total_elapsed_time = self.activity_data.elapsed_time
        session.total_timer_time = self.activity_data.elapsed_time
        session.total_distance = self.activity_data.activity_distance

        session.avg_heart_rate = int(self.activity_data.average_heartrate)
        session.max_heart_rate = int(self.activity_data.max_heartrate)

        session.avg_cadence = int(self.activity_data.average_cadence)
        session.max_cadence = int(self.activity_data.max_cadence)

        session.avg_power = int(self.activity_data.average_watts)
        session.max_power = int(self.activity_data.max_watts)

        session.avg_speed = self.activity_data.average_speed
        session.max_speed = self.activity_data.max_speed

        session.total_calories = int(self.activity_data.calories)
        session.sport = Sport.CYCLING
        session.sub_sport = SubSport.VIRTUAL_ACTIVITY
        session.first_lap_index = 0
        session.num_laps = 1

        self.builder.add(session)

    def _add_activity(self):
        """Add activity message."""
        activity = ActivityMessage()
        activity.timestamp = self.end_date_fit_ts
        activity.total_timer_time = self.activity_data.elapsed_time
        activity.num_sessions = 1
        activity.type = 0
        activity.event = Event.ACTIVITY
        activity.event_type = EventType.STOP
        activity.local_timestamp = round(self.activity_data.start_date.timestamp())
        self.builder.add(activity)

    def build(self, output_path: str = None):
        """Build and write the FIT file."""
        if not output_path:
            raise ValueError("output_path is required for build.")

        # Add messages in order
        self._add_file_id()
        self._add_file_creator()

        # Timer start event
        self._add_event(
            self.activity_data.start_ts_miliseconds, Event.TIMER, EventType.START
        )

        # Add all record points
        self._add_records()

        # Add lap
        self._add_lap()

        # Timer stop event
        self._add_event(self.end_date_fit_ts, Event.SESSION, EventType.STOP_DISABLE_ALL)

        # Add session and activity
        self._add_session()
        self._add_activity()

        # Build FIT file and write to disk
        fit_file = self.builder.build()

        # Ensure the output directory exists
        output_dir = Path(output_path).parent
        output_dir.mkdir(parents=True, exist_ok=True)

        fit_file.to_file(output_path)

        print(f"FIT file saved to: {output_path}")


# Example usage
if __name__ == "__main__":
    # # Example usage
    data_dir = Path(__file__).parent.parent / "data"
    input_file = str(
        data_dir / "raw" / "MyWhoosh - The Seven Gems_2025-11-13_combined.json"
    )
    output_file = str(
        data_dir / "processed" / "MyWhoosh - The Seven Gems_2025-11-13_combined.fit"
    )

    data = ActivityData.from_json_file(input_file)

    # Create builder and generate FIT file
    builder = MyWhooshFitBuilder(input_file)
    builder.build(output_file)

    # print("FIT file created successfully!")

# What I need to retrieve from the json :
