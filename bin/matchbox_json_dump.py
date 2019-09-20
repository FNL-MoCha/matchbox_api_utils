#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Get parsed dataset from MATCHBox and dump as a JSON object that we can use 
later on to speed up development and periodic searching for data.  
"""
import sys
import argparse
from pprint import pprint as pp # noqa

#import matchbox_api_utils  # noqa
from matchbox_api_utils import MatchData
from matchbox_api_utils import TreatmentArms

version = '4.1.051719'

def get_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('matchbox', metavar='<matchbox>', help='Name of '
        'MATCHBox to which we make the file. Valid systems are: '
        '"adult", "adult-uat", "ped".')
    parser.add_argument('-d', '--data', metavar='<raw_mb_datafile.json>',
        help='Load a raw MATCHBox database file (usually after running with '
        'the -r option).')
    parser.add_argument('-r', '--raw', action='store_true',
        help='Generate a raw dump of MATCHbox for debugging and dev purposes.')
    parser.add_argument('-p', '--patient', metavar='<psn>', 
        help='Patient sequence number used to limit output for testing and dev '
        'purposes')
    parser.add_argument('-t', '--ta_json' , metavar='<ta_obj.json>',
        help='Treatment Arms obj JSON filename. DEFAULT: ta_obj_<datestring>.'
        'json')
    parser.add_argument('-a', '--amoi_json' , metavar='<amoi_obj.json>',
        help='aMOIs lookup filename. DEFAULT: "amois_lookup_<datestring>.'
        'json".')
    parser.add_argument('-m', '--mb_json', metavar='<mb_obj.json>', 
        help='Name of Match Data obj JSON file. DEFAULT: "mb_obj_<datestring>.'
        'json".')
    parser.add_argument('-c', '--connection', metavar='<connection_method>', 
        dest='method', choices=['api', 'mongo'], default='mongo', 
        help='Connection method used to access MATCHBox data. Choose from '
        'either "api" or "mongo". DEFAULT: %(default)s')

    parser.add_argument('-v', '--version', action='version', 
            version = '%(prog)s  -  ' + version)
    args = parser.parse_args()
    return args

def main(data, arms, mb_filename=None, ta_filename=None, amois_filename=None):
    sys.stdout.write('Dumping matchbox as a JSON file for easier and faster '
        'code testing...')
    sys.stdout.flush()
    data.matchbox_dump(filename=mb_filename)
    sys.stdout.write('Done!\n')

    sys.stdout.write('Dumping Treatment Arms as a JSON file for easier and '
        'faster code testing...')
    sys.stdout.flush()
    arms.ta_json_dump(amois_filename=amois_filename, ta_filename=ta_filename)
    sys.stdout.write("Done!\n")

if __name__=='__main__':
    args = get_args()

    if args.raw:
        sys.stdout.write('\n*** Making a raw dump of MATCHBox (%s) for dev and '
            'testing purposes ***\n' % args.matchbox)
        sys.stdout.flush()
        MatchData(matchbox=args.matchbox, method=args.method, json_db=None, 
            make_raw=True)
        sys.stdout.write('Done!\n')
        sys.exit()

    sys.stdout.write('\nRetrieving data from MATCHBox (%s)...' % args.matchbox)
    sys.stdout.flush()

    data = MatchData(matchbox=args.matchbox, method=args.method, json_db=None, 
        load_raw=args.data, patient=args.patient)
    if data is None:
        sys.exit(1)

    if getattr(data, '_matchbox') is None:
        sys.exit(1)
    arms = TreatmentArms(matchbox=args.matchbox, method=args.method, 
        json_db=None)
    sys.stdout.write('Done!\n')

    main(data, arms, args.mb_json, args.ta_json, args.amoi_json)
