#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import os
import json
import argparse
from pprint import pprint as pp

from matchbox_api_utils import MatchData

version = '2.0.0_071917'

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
    parser.add_argument('-d', '--data', metavar='<raw_mb_datafile.json>',
            help='Load a raw MATCHBox database file (usually after running with '
                 'the -r option).')
    parser.add_argument('-r', '--raw', action='store_true',
        help='Generate a raw dump of MATCHbox so that we can see the raw data '
             'structure available for debugging and dev purposes.')
    parser.add_argument('-p', '--patient', metavar='<psn>', 
            help='Patient sequence number used to limit output for testing and '
                 'dev purposes')
    parser.add_argument('-o', '--outfile', metavar='<out.json>', 
            help='Name of output JSON file. DEFAULT: "mb_obj_<datestring>.json"')
    parser.add_argument('-v', '--version', action='version', 
            version = '%(prog)s  -  ' + version)
    args = parser.parse_args()
    return args

def main(data,outfile=None):
    data._matchbox_dump(outfile)
    sys.stdout.write("Done!\n")

if __name__=='__main__':
    args = get_args()

    if args.raw:
        sys.stdout.write('\n*** Making a raw dump of MATCHBox for dev / testing '
            'purposes ***\n')
        sys.stdout.flush()
        MatchData(make_raw=True)
        sys.stdout.write('Done!\n')
        sys.exit()

    sys.stdout.write("Dumping matchbox as a JSON file for easier and faster code "
        "testing...")
    sys.stdout.flush()

    data = MatchData(dumped_data=None,load_raw=args.data, patient=args.patient)

    outfile = args.outfile
    main(data,outfile)
