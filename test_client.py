#!/usr/bin/env python

import json
import sys
import os


def main():
    """Simple test client for the Medicine Reminder MCP server."""
    # Load test payloads
    with open('test_payloads.json', 'r') as f:
        test_payloads = json.load(f)
    
    # Check if a specific test was requested
    if len(sys.argv) > 1 and sys.argv[1] in test_payloads:
        # Run specific test
        test_name = sys.argv[1]
        payload = test_payloads[test_name]
        print(f"Running test: {test_name}")
        print(json.dumps(payload))
        # In a real client, you would send this to the MCP server
        # For now, we just print it to stdout
    else:
        # List available tests
        print("Available tests:")
        for test_name in test_payloads.keys():
            print(f"  - {test_name}")
        print("\nUsage: python test_client.py [test_name]")


if __name__ == "__main__":
    main()