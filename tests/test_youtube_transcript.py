"""
Test script for YouTube transcript extraction.
Run with: python -m tests.test_youtube_transcript
"""

import sys
import os
import json

# Add the parent directory to sys.path to allow importing from utils
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.network import get_youtube_transcript

def test_youtube_transcript():
    """Test the YouTube transcript extraction functionality."""
    # Test with a popular video that has captions
    video_id = "dQw4w9WgXcQ"  # Rick Astley - Never Gonna Give You Up
    
    print(f"Testing transcript extraction for video ID: {video_id}")
    result = get_youtube_transcript(video_id)
    
    if "error" in result:
        print(f"Error: {result['error']}")
        return False
    
    print(f"Success! Retrieved transcript with {result['segment_count']} segments")
    print(f"Video title: {result['video_title']}")
    print(f"Language: {result['language']}")
    
    # Print first few segments as example
    print("\nSample segments:")
    for segment in result['transcript_segments'][:3]:
        print(f"{segment.get('formatted_timestamp', segment.get('start'))}: {segment['text']}")
    
    return True

if __name__ == "__main__":
    test_youtube_transcript()
