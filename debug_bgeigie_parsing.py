#!/usr/bin/env python3
"""
Debug bGeigie log parsing to identify why measurements aren't being created
"""
import re
from datetime import datetime

# Current regex pattern from the processor
BGEIGIE_DATA_PATTERN = re.compile(
    r'^\$BNRDD,(\d+),(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z),(\d+),(\d+),(\d+),'
    r'([NSEW\d\.\-]+),([NSEW\d\.\-]+),([AVD]),(\d+\.?\d*),([NSEW]),(\d+\.?\d*),([NSEW]),'
    r'(\d+\.?\d*),([NSEW]),(\d+\.?\d*),([NSEW]),(\d+\.?\d*),(\d+\.?\d*),(\d+\.?\d*)'
)

# Sample bGeigie log lines (common formats)
sample_lines = [
    "$BNRDD,300,2011-01-15T00:00:01Z,0,0,0,A,2200,V*35",
    "$BNRDD,301,2011-01-15T00:00:02Z,35.6894,139.6917,32,A,2300,A*6E",
    "$BNRDD,302,2011-01-15T00:00:03Z,3568.94,N,13941.52,E,32,A,2400,A*6F",
    "$BNRDD,303,2011-01-15T00:00:04Z,100,200,300,3568.95,N,13941.53,E,33,A,2500,A*70",
    "$BNRDD,304,2011-01-15T00:00:05Z,150,250,350,3568.96,N,13941.54,E,34,A,2600,A,12.5,45.2,1013.2*71"
]

def test_parsing():
    print("🔍 Testing bGeigie Log Parsing")
    print("=" * 50)
    
    for i, line in enumerate(sample_lines, 1):
        print(f"\nLine {i}: {line}")
        match = BGEIGIE_DATA_PATTERN.match(line.strip())
        
        if match:
            groups = match.groups()
            print(f"✅ MATCHED - Groups: {len(groups)}")
            for j, group in enumerate(groups):
                print(f"   Group {j}: '{group}'")
        else:
            print("❌ NO MATCH")
            
            # Try simpler patterns to debug
            simple_pattern = re.compile(r'^\$BNRDD,(.+)')
            simple_match = simple_pattern.match(line.strip())
            if simple_match:
                parts = simple_match.group(1).split(',')
                print(f"   Parts count: {len(parts)}")
                print(f"   Parts: {parts[:10]}...")  # Show first 10 parts
    
    print(f"\n🧪 Testing improved regex pattern...")
    
    # More flexible pattern that handles variable field counts
    improved_pattern = re.compile(
        r'^\$BNRDD,(\d+),(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z),(.+)'
    )
    
    for i, line in enumerate(sample_lines, 1):
        print(f"\nImproved test - Line {i}:")
        match = improved_pattern.match(line.strip())
        if match:
            device_id, timestamp, rest = match.groups()
            parts = rest.split(',')
            print(f"✅ Device: {device_id}, Time: {timestamp}")
            print(f"   Remaining parts: {len(parts)} - {parts}")
        else:
            print("❌ Still no match")

if __name__ == "__main__":
    test_parsing()
