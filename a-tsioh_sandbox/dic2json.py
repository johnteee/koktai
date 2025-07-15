# -*- coding: utf8 -*-
"""
try to get as much data as possible from original .dic files
(cat-ed on stdin)
"""
import sys
import fileinput
from collections import defaultdict
import json

import analyse_word_entry
#import wsl_to_kaulo

def process_buffer(buf,list_of_results):
    entry = analyse_word_entry.parse_one("".join(buf))
    if entry:
        if len(list_of_results) > 0 and list_of_results[-1]['entry'] == entry['entry']:
            list_of_results[-1]['heteronyms'].append(entry)
        else:
            list_of_results.append({'entry':entry['entry'], 'heteronyms':[entry]})
    else:
        print("unanalyzed", "".join(buf).encode("utf8"))

def print_results(list_of_results):
    for entry in list_of_results:
        for h in entry['heteronyms']:
            print(analyse_word_entry.html_of_entry(h).encode("utf8"))

def main():
    """
    Main function to read the dictionary file, process it, and output JSON.
    The file processing logic is identical to dic2jade.py.
    """
    list_of_results = []
    
    i = 0
    buf = []
    inside_entry = False

    # Process lines from stdin, as dic2jade.py does with fileinput
    for line in fileinput.input():
        i += 1
        try:
            line = line.strip()

            # print("type", type(line), file=sys.stderr)
            # print("line", line, file=sys.stderr)
            
            if line.startswith('~t96;'):
                # This line marks a new word entry.
                # First, process the buffer for the previous word.
                if len(buf) > 0:
                    process_buffer(buf, list_of_results)
                
                # Start a new buffer for the new word.
                buf = [line]
                inside_entry = True
            elif line.startswith(u".本文"):
                # This line marks the end of a section.
                # Process the last buffer if it exists.
                if len(buf) > 0:
                    process_buffer(buf, list_of_results)
                
                # Clear the buffer and reset state.
                buf = []
                inside_entry = False
            elif inside_entry:
                # This is a continuation line for the current entry.
                buf.append(line)

        except UnicodeDecodeError:
            print("encoding error on line", i, file=sys.stderr)
    
    # Process the very last buffer in the file
    if len(buf) > 0:
        process_buffer(buf, list_of_results)

    # Output the final list of results as a JSON object
    print(json.dumps(list_of_results, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()