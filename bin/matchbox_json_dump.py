#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import os
import json
import argparse
from pprint import pprint as pp

import matchbox_api_utils
from matchbox_api_utils import MatchData
from matchbox_api_utils import TreatmentArms

version = '3.0.0_080917'

def get_args():
    parser = argparse.ArgumentParser(
        formatter_class = lambda prog: 
            argparse.HelpFormatter(prog, max_help_position=100, width=125),
        description=
        '''
        Get parsed dataset from MATCHBox and dump as a JSON object that we can use 
        later on to speed up development and periodic searching for data.  
        '''
    )
    # TODO: get rid of this?
    parser.add_argument('-d', '--data', metavar='<raw_mb_datafile.json>',
        help='Load a raw MATCHBox database file (usually after running with the -r option).')
    parser.add_argument('-r', '--raw', action='store_true',
        help='Generate a raw dump of MATCHbox for debugging and dev purposes.')
    parser.add_argument('-p', '--patient', metavar='<psn>', 
        help='Patient sequence number used to limit output for testing and dev purposes')
    # TODO: get rid of this?

    parser.add_argument('-t', '--ta_json' , metavar='<ta_obj.json>',
        help='Treatment Arms obj JSON filename. DEFAULT: ta_obj_<datestring>.json')
    parser.add_argument('-a', '--amoi_json' , metavar='<amoi_obj.json>',
        help='aMOIs lookup filename. DEFAULT: "amois_lookup_<datestring>.json".')
    parser.add_argument('-m', '--mb_json', metavar='<mb_obj.json>', 
        help='Name of Match Data obj JSON file. DEFAULT: "mb_obj_<datestring>.json".')

    parser.add_argument('-v', '--version', action='version', 
            version = '%(prog)s  -  ' + version)
    args = parser.parse_args()
    return args

def main(data,arms,mb_filename=None,ta_filename=None,amois_filename=None):
    sys.stdout.write('Dumping matchbox as a JSON file for easier and faster code testing...')
    sys.stdout.flush()
    data.matchbox_dump(filename=mb_filename)
    sys.stdout.write('Done!\n')

    sys.stdout.write('Dumping Treatment Arms as a JSON file for easier and faster code testing...')
    sys.stdout.flush()
    arms.ta_json_dump(amois_filename=amois_filename,ta_filename=ta_filename)
    sys.stdout.write("Done!\n")

if __name__=='__main__':
    args = get_args()

    if args.raw:
        sys.stdout.write('\n*** Making a raw dump of MATCHBox for dev / testing purposes ***\n')
        sys.stdout.flush()
        MatchData(make_raw=True)
        sys.stdout.write('Done!\n')
        sys.exit()

    sys.stdout.write('Retrieving data from MATCHBox...')
    sys.stdout.flush()
    data = MatchData(dumped_data=None,load_raw=args.data,patient=args.patient)
    arms = TreatmentArms(json_db=None)
    sys.stdout.write('Done!\n')

    main(data,arms,args.mb_json,args.ta_json,args.amoi_json)
