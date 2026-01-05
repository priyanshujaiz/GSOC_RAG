"""
Test GitHub streaming connector.
This will run for 2 poll cycles and then stop.
"""

import pathway as pw
from backend.connectors.github_connector import create_github_stream
from backend.core.logger import setup_logging
import time

# Setup logging
setup_logging()

def test_connector():
    """Test the GitHub connector with a small repository."""
    
    print("\n" + "="*60)
    print("Testing GitHub Streaming Connector")
    print("="*60 + "\n")
    
    # Test with a small, active repository
    repositories = [
        "pathwaycom/pathway",  # The framework we're using
    ]
    
    print(f"Tracking repositories: {repositories}")
    print(f"Poll interval: 30 seconds")
    print(f"Lookback: 24 hours")
    print("\nStarting connector... (will run for 2 poll cycles)")
    print("-" * 60)
    
    # Create the stream
    events_table = create_github_stream(
        repositories=repositories,
        poll_interval=30,  # 30 seconds
        lookback_hours=24,  # Look back 24 hours
    )
    
    # Print events as they come in
    pw.io.jsonlines.write(events_table, "output_events.jsonl")
    
    print("\n✅ Connector is running!")
    print("   Events are being written to: output_events.jsonl")
    print("   Press Ctrl+C to stop\n")
    
    # Run the Pathway computation
    try:
        pw.run()
    except KeyboardInterrupt:
        print("\n\n✅ Connector stopped by user")
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        raise

if __name__ == "__main__":
    test_connector()