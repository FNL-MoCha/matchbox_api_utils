#!/usr/bin/env python3
import sys
import os
import json
from pprint import pprint as pp

try:
    json_file = sys.argv[1]
    patient = sys.argv[2]
except IndexError:
    sys.stderr.write('ERROR: You must input the JSON file to be read!\n')
    sys.exit(1)

with open(json_file) as fh:
    data = json.load(fh)
    for p in data:
        if p == patient:
            pp(data[patient])


