#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import os
import json
import csv
import argparse
import re
from pprint import pprint as pp

from matchbox_api_utils import MatchData 

version = '3.0.0_072417'

def get_args():
    parser = argparse.ArgumentParser(
        formatter_class = lambda prog: argparse.HelpFormatter(prog, max_help_position=100, width=125),
        description=
        '''
        Input a MSN, BSN, or PSN, and return the other identifiers. Useful when trying to retrieve the 
        correct dataset and you only know one piece of information.

        Note: We are only working with internal BSN, MSN, and PSN numbers for now and can not return
        Outside Assay identifiers at this time. 
        '''
    )
    parser.add_argument('ids', metavar='<IDs>', nargs='?',
            help='MATCH IDs to query.  Can be single or comma separated list.  Must be used with PSN or MSN option.')
    parser.add_argument('-j', '--json', metavar='<mb_json_file>', default='sys_default',
            help='Load a MATCHBox JSON file derived from "matchbox_json_dump.py" instead '
                 'of a live query. By default will load the "sys_default" created during '
                 'package installation. If you wish to do a live query (i.e. not load a '
                 'previously downloaded JSON dump, set -j to "None".')
    parser.add_argument('-t', '--type', choices=['psn','msn','bsn'], required=True, type=str.lower,
            help='Type of query string input. Can be MSN, PSN, or BSN')
    parser.add_argument('-f', '--file', metavar="<input_file>", 
            help='Load a batch file of all MSNs or PSNs to proc')
    parser.add_argument('-v','--version',action='version', version = '%(prog)s  -  ' + version)
    args = parser.parse_args()

    # Kludy way to use a sys default for the API, while still allowing for live queries
    # if need be.  Probably a better way, but whatever!
    if args.json == 'None':
        args.json = None
    return args

def read_batchfile(input_file):
    with open(input_file) as fh:
        return [ line.rstrip('\n') for line in fh ]

def map_id(mb_data,id_list,qtype):
    """Call to MATCHBox and return PSN, MSN, or BSN data based on the qtype."""
    results = {}

    for pt in id_list:
        if qtype == 'psn':
            msn = mb_data.get_msn(psn=pt)
            bsn = mb_data.get_bsn(psn=pt)
            psn = 'PSN' + pt.lstrip('PSN')
            return_val = (psn,bsn,msn)
        elif qtype == 'msn':
            psn = mb_data.get_psn(msn=pt)
            bsn = mb_data.get_bsn(msn=pt)
            msn = 'MSN' + pt.lstrip('MSN')
            return_val = (psn,bsn,msn)

        elif qtype == 'bsn':
            psn = mb_data.get_psn(bsn=pt)
            msn = mb_data.get_msn(bsn=pt)
            return_val = (psn,pt,msn)

        print(','.join(return_val))

def validate_list(id_list,qtype):
    """
    Validate the ID string matches the query type, or skip this entry and print
    a warning. Can only work with normal MATCH samples right now and will not
    work with Outside Assays until I have some idea of the pattern needed.

    """
    valid_list = []
    type_regex = {
        'obsn' : re.compile(r'^(FMI|MDA|CARIS|MSKCC)-(.*?)$'),
        'bsn'  : re.compile(r'^(T-[0-9]{2}-[0-9]{6})$'),
        'msn'  : re.compile(r'^(?:MSN)?([0-9]+)$'),
        'psn'  : re.compile(r'^(?:PSN)?([0-9]+)$'),
    }

    for elem in id_list:
        try:
            trimmed = re.search(type_regex[qtype],elem).group(1)
            valid_list.append(trimmed)
        except AttributeError:
            sys.stdout.write("WARN: id '{}' is not valid. Skipping entry!\n".format(elem))
    return valid_list

if __name__=='__main__':
    args = vars(get_args())
    query_list = []

    if args['file']:
        query_list = read_batchfile(args['file'])
    else:
        query_list = args['ids'].split(',')

    valid_ids = validate_list(query_list,args['type'])
    if not valid_ids:
        sys.stderr.write("ERROR: No valid IDs input!\n")
        sys.exit(1)

    # Make a call to MATCHbox to get a JSON obj of data.
    if not args['json']:
        sys.stdout.write('Retrieving a live MATCHBox data object. This may take a few minutes...\n')
        sys.stdout.flush()

    data = MatchData(json_db=args['json'])
    sys.stdout.write('\n')

    print('Getting MSN / PSN mapping data...')
    map_id(data,valid_ids,args['type'])
