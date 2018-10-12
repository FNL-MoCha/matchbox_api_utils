#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# TODO: We'll need to configure this for other MATCHBox systems once we get 
#       the all worked out.  For now, just take the MATCHBox arg as a 
#       "placeholder", and use it for live connections.  But later, need it to
#       figure out which JSON file to load.
"""
Input a MSN, BSN, or PSN, and return the other identifiers. Useful when trying 
to retrieve the correct dataset and you only know one piece of information.

Note: We are only working with internal BSN, MSN, and PSN numbers for now and 
can not return Outside Assay identifiers at this time. 
"""
import sys
import os
import json
import csv
import argparse
import re
from pprint import pprint as pp

from matchbox_api_utils import MatchData 

version = '4.0.101218'

def get_args():
    parser = argparse.ArgumentParser(description = __doc__)
    parser.add_argument('matchbox', metavar='<matchbox>', help='Name of '
        'MATCHBox to which we make the connection. Valid systems are: '
        '"adult", "adult-uat", "ped".')
    parser.add_argument('ids', metavar='<IDs>', nargs='?',
        help='MATCH IDs to query.  Can be single or comma separated list. '
        'Must be used with PSN or MSN option.')
    parser.add_argument('-t', '--type', choices=['psn','msn','bsn'], 
        required=True, type=str.lower, help='Type of query string input. Can '
        'be MSN, PSN, or BSN')
    parser.add_argument('-l', '--live', action='store_true', 
        help='Make a live call to MATCHbox instead of relying on local JSON '
        'database. This is especially helpful for newly sequenced patients '
        'since the last dump.')
    parser.add_argument('-f', '--file', metavar="<input_file>", 
        help='Load a batch file of all MSNs or PSNs to proc')
    parser.add_argument('-o', '--outfile', metavar='<outfile>', help='File to '
        'which output should be written. Default: STDOUT.')
    parser.add_argument('-v','--version', action='version', 
        version = '%(prog)s  -  ' + version)
    args = parser.parse_args()
    return args

def read_batchfile(input_file):
    with open(input_file) as fh:
        return [ line.rstrip('\n') for line in fh ]

def map_id(mb_data, id_list, qtype):
    """
    Call to MATCHBox and return PSN, MSN, or BSN data based on the qtype.
    """
    results = []

    # MSN and BSN results returns lists. Cat for easier str output.
    for pt in id_list:
        if qtype == 'psn':
            if pt not in mb_data.data.keys():
                sys.stderr.write('WARN: No such patient with ID: %s.\n' % pt)
                continue;
            bsn = mb_data.get_bsn(psn=pt)
            if bsn:
                bsn = cat_list(bsn)
                msn = mb_data.get_msn(psn=pt)
                if msn:
                    msn = cat_list(msn)
                else:
                    msn = '---'
                psn = 'PSN' + pt.lstrip('PSN')
                results.append((psn, bsn, msn))

        elif qtype == 'msn':
            psn = mb_data.get_psn(msn=pt)
            if psn:
                msn = 'MSN' + pt.lstrip('MSN')
                bsn = cat_list(mb_data.get_bsn(msn=pt))
                results.append((psn, bsn, msn))

        elif qtype == 'bsn':
            psn = mb_data.get_psn(bsn=pt)
            if psn:
                msn = mb_data.get_msn(bsn=pt)
                if msn:
                    msn = cat_list(msn)
                else:
                    msn = '---'
                results.append((psn, pt, msn))
    return results

def cat_list(l):
    return ';'.join(l)

def print_results(data, outfh):
    if data:
        sys.stdout.write('\n') # pad output from stderr msg if printing to stdout
        outfh.write(','.join(['PSN', 'BSN', 'MSN']))
        outfh.write('\n')
        for i in sorted(data, key = lambda x: x[1]):
            outfh.write(','.join(i))
            outfh.write('\n')

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
            sys.stdout.write("WARN: id '{}' is not valid. Skipping "
                "entry!\n".format(elem))
    return valid_list

if __name__=='__main__':
    args = vars(get_args())
    query_list = []

    if args['file']:
        query_list = read_batchfile(args['file'])
    else:
        query_list = args['ids'].split(',')

    valid_ids = validate_list(query_list, args['type'])
    if not valid_ids:
        sys.stderr.write("ERROR: No valid IDs input!\n")
        sys.exit(1)

    json_db = 'sys_default'
    # Make a call to MATCHbox to get a JSON obj of data.
    if args['live']:
        sys.stdout.write('Retrieving a live MATCHBox data object. This may '
            'take a few minutes...\n')
        sys.stdout.flush()
        json_db=None

    data = MatchData(matchbox=args['matchbox'], method='mongo', json_db=json_db,
        quiet=True)
    sys.stdout.write('\n')

    print('Getting MSN / PSN mapping data (Database date: %s)...' 
        % data.db_date)
    results = map_id(data, valid_ids, args['type'])

    if args['outfile']:
        sys.stderr.write("Writing output to %s.\n" % args['outfile'])
        outfh = open(args['outfile'], 'w')
    else:
        outfh = sys.stdout
    print_results(results, outfh)
