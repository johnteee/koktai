#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import json
import re

def process_entry(data):
    """
    Processes a list of dictionary entries to extract pronunciation
    from <rt> tags and create a new 'pronun_fang' field.
    
    This function recursively processes nested structures.
    """
    if isinstance(data, list):
        # If the data is a list, process each item in the list
        for item in data:
            process_entry(item)
    elif isinstance(data, dict):
        # If the data is a dictionary, look for the 'entry' key
        if 'entry' in data and isinstance(data['entry'], str):
            original_entry = data['entry']
            
            # Find all content within <rt>...</rt> tags
            # The re.findall function returns a list of all matches
            pronunciations = re.findall(r'<rt>(.*?)</rt>', original_entry)
            
            # Join the found pronunciations into a single string
            data['pronun_fang'] = "".join(pronunciations)
            
            # Remove the <rt>...</rt> tags from the original entry string
            # The re.sub function replaces the matched patterns with an empty string
            data['entry'] = re.sub(r'<rt>.*?</rt>', '', original_entry)

        # Recursively process any other dictionary values
        for key, value in data.items():
            if isinstance(value, (dict, list)):
                process_entry(value)

def main():
    """
    Main function to read from stdin, process the data,
    and print the result to stdout.
    """
    try:
        # Load the entire JSON input from standard input
        # data = json.load(sys.stdin)
        # Read raw bytes from stdin to handle file encodings correctly.
        raw_data = sys.stdin.buffer.read()
        
        # Decode as UTF-8 (the standard for JSON).
        decoded_data = raw_data.decode('utf-8')
        decoded_data = re.sub(r'<img src="(.*?)"\s*>', r'\1', decoded_data)

        data = json.loads(decoded_data)
        
        # Process the loaded data
        process_entry(data)
        
        # Dump the modified JSON data to standard output
        # ensure_ascii=False is crucial for correct UTF-8 output
        # indent=2 makes the output human-readable
        print(json.dumps(data, ensure_ascii=False, indent=2))

    except json.JSONDecodeError:
        sys.stderr.write("Error: Invalid JSON format provided.\n")
    except Exception as e:
        sys.stderr.write(f"An unexpected error occurred: {e}\n")

if __name__ == "__main__":
    main()
