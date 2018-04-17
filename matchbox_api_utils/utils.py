# -*- coding:utf-8 -*-
# Set of functions that I am commonly using across all classes.
import os
import sys
import re
import json
import datetime

from termcolor import colored, cprint
from pprint import pprint as pp

from matchbox_api_utils import matchbox_conf


def load_dumped_json(json_file):
    # Load in a JSON DB file (raw or proc) and return JSON obj and file ctime.
    try:
        date_string = re.search(r'.*?([0-9]+).json$',json_file).group(1)
        formatted_date=datetime.datetime.strptime(
            date_string,'%m%d%y').strftime('%m/%d/%Y')
    except (AttributeError,ValueError):
        creation_date = os.path.getctime(json_file)
        formatted_date=datetime.datetime.fromtimestamp(
                creation_date).strftime('%m/%d/%Y')
    with open(json_file) as fh:
        return formatted_date,json.load(fh)

def get_today(outtype):
    if outtype == 'long':
        # return datetime.date.today().strftime('%m/%d/%Y')
        return datetime.date.today().strftime('%Y-%m-%d')
    elif outtype == 'short':
        return datetime.date.today().strftime('%m%d%y')

def epoch_to_hr_date(epoch_date):
    return datetime.datetime.fromtimestamp(epoch_date).strftime('%Y-%m-%d')

def get_vals(d, *v):
    # return a value or list of values
    return [d.get(i, '---') for i in v]

def make_json(*, outfile, data, sort=True):
    with open(outfile, 'w') as fh:
        json.dump(data, fh, sort_keys=sort, indent=4)

def print_json(data):
    return json.dumps(data, sort_keys=True, indent=4)

def read_json(json_file):
    with open(json_file) as fh:
        return json.load(fh)

def __exit__(line, msg=None):
    output = ('Script stopped at line: {} with message: "{}".'.format(line, msg))
    sys.stderr.write('\n')
    cprint(output, 'white', 'on_green', attrs=['bold'], file=sys.stderr)
    sys.exit()

