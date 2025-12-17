#!/usr/bin/env python3
"""
Generate a test FIT file with sample data for testing purposes.
This creates a minimal FIT file with record messages, session messages,
and temperature data that can be used for testing.
"""
from pathlib import Path
from datetime import datetime, timedelta
import sys

# Add parent directory to path to import fit_tool
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from fit_tool.fit_file_builder import FitFileBuilder
    from fit_tool.profile.messages.record_message import RecordMessage
    from fit_tool.profile.messages.session_message import SessionMessage
    from fit_tool.profile.messages.lap_message import LapMessage
    from fit_tool.profile.messages.file_creator_message import FileCreatorMessage
    from fit_tool.profile.messages.record_message import RecordTemperatureField
except ImportError as e:
    print(f"Error importing fit_tool: {e}")
    print("Please install fit_tool: pip install fit_tool")
    sys.exit(1)


def create_test_fit_file(output_path: Path) -> None:
    """Create a test FIT file with sample data."""
    builder = FitFileBuilder()
    
    # Add file creator message
    file_creator = FileCreatorMessage()
    file_creator.software_version = 100
    builder.add(file_creator)
    
    # Create start time
    start_time = datetime.now() - timedelta(hours=1)
    
    # Add record messages with varying data
    # Simulate a 30-minute ride with data points every 5 seconds
    num_records = 360  # 30 minutes * 60 seconds / 5 seconds
    
    for i in range(num_records):
        record = RecordMessage()
        record.timestamp = start_time + timedelta(seconds=i * 5)
        
        # Vary the values to create realistic averages
        # Power: 150-250 watts average
        record.power = 200 + int(50 * (i % 20 - 10) / 10)
        
        # Heart rate: 140-160 bpm
        record.heart_rate = 150 + int(10 * (i % 15 - 7) / 7)
        
        # Cadence: 80-100 rpm
        record.cadence = 90 + int(10 * (i % 12 - 6) / 6)
        
        # Add temperature (this should be removed by cleanup)
        record.set_field(RecordTemperatureField.ID, 20 + int(i % 5))
        
        builder.add(record)
    
    # Add session message (without averages - they should be calculated)
    session = SessionMessage()
    session.timestamp = start_time + timedelta(minutes=30)
    session.start_time = start_time
    session.total_elapsed_time = 1800.0  # 30 minutes in seconds
    session.total_timer_time = 1800.0
    session.total_distance = 15000.0  # 15 km
    session.sport = "cycling"
    # Intentionally leave avg_power, avg_heart_rate, avg_cadence as None
    # to test the calculation logic
    builder.add(session)
    
    # Add a lap message
    lap = LapMessage()
    lap.timestamp = start_time + timedelta(minutes=15)
    lap.start_time = start_time
    lap.total_elapsed_time = 900.0
    lap.total_timer_time = 900.0
    lap.total_distance = 7500.0
    builder.add(lap)
    
    # Build and save the file
    fit_file = builder.build()
    fit_file.to_file(str(output_path))
    print(f"Created test FIT file: {output_path}")


if __name__ == "__main__":
    test_dir = Path(__file__).parent / "test_data"
    test_dir.mkdir(exist_ok=True)
    output_file = test_dir / "MyNewActivity-3.8.5.fit"
    create_test_fit_file(output_file)
    print(f"Test FIT file created at: {output_file}")

