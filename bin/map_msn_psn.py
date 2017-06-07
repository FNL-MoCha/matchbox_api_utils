#!/usr/bin/env python
# Input a set of variants and output a hitrate  for NCI-MATCH
import sys
import os
import json
import csv
import argparse
import re
from pprint import pprint as pp

from matchbox_api_utils.Matchbox import *

version = '1.1.0_060717'

class Config(object):
    def __init__(self,config_file):
        self.config_file = config_file
        self.config_data = Config.read_config(self.config_file)

    def __repr__(self):
        return '%s:%s' % (self.__class__,self.__dict__)

    def __getitem__(self,key):
        return self.config_data[key]

    def __iter__(self):
        return self.config_data.itervalues()

    @classmethod
    def read_config(cls,config_file):
        '''Read in a config file of params to use in this program'''
        with open(config_file) as fh:
            data = json.load(fh)
        return data


def get_args():
    parser = argparse.ArgumentParser(
        formatter_class = lambda prog: argparse.HelpFormatter(prog, max_help_position=100, width=150),
        description=
        '''
        Input a list of genes by variant type and get back a table of NCI-MATCH hits that can be further 
        analyzed in Excel.  
        '''
    )
    parser.add_argument('ids', metavar='<IDs>', nargs='?',
            help='MATCH IDs to query.  Can be single or comma separated list.  Must be used with PSN or MSN option.')
    parser.add_argument('-j', '--json', metavar='<mb_json_file>', 
            help='Load a MATCHBox JSON file derived from "matchbox_json_dump.py" instead of a live query')
    parser.add_argument('-p', '--psn', action='store_true', help='Input is a PSN to be translated to a MSN')
    parser.add_argument('-m', '--msn', action='store_true', help='Input is a MSN to be translated to a PSN')
    parser.add_argument('-b', '--batch', metavar="<input_file>", help='Load a batch file of all MSNs or PSNs to proc')
    parser.add_argument('-v','--version',action='version', version = '%(prog)s  -  ' + version)
    args = parser.parse_args()

    if not args.psn and not args.msn:
        sys.stderr.write("ERROR: you must indicate whether PSNs or MSNs are being loaded!\n")
        sys.exit(1)

    return args

def read_batchfile(input_file):
    with open(input_file) as fh:
        return [line.rstrip('\n') for line in fh ]

def map_id(mb_data,id_list,psn,msn):
    results = {}
    id_type = ''

    if psn:
        id_type = 'psn'
    elif msn:
        id_type = 'msn'

    for pt in id_list:
        return_val = mb_data.map_msn_psn(pt,id_type)
        if return_val:
            results[pt] = return_val
    print_results(results,id_type)

def validate_list(id_list):
    '''String off leading PSN or MSN if it was added and validate that the rest of the strings input
    are real MSNs or PSNs and not some other random string.  Print warning if there is an issue with
    any inputs.'''
    valid_list = []
    for elem in id_list:
        try:
            trimmed = re.search('^([PM]SN)?(\d+)$',elem).group(2)
            valid_list.append(trimmed)
        except:
            sys.stdout.write("WARN: id '{}' is not valid.  Skipping entry!\n".format(elem))
    return valid_list

def print_results(data,id_type):
    '''since we either get a PSN result or a list of MSNs, handle printing accordingly'''
    if id_type == 'psn':
        for k in data:
            print('{},{}'.format('PSN'+k, ','.join(data[k])))
    else: 
        for k in data:
            print('{},{}'.format('PSN'+data[k],'MSN'+k))

if __name__=='__main__':
    if os.path.isfile(os.path.join(os.getcwd(),'/config.json')):
        config_file = os.path.join(os.getcwd(), '/config.json')
    else:
        config_file = os.path.join(os.environ['HOME'],'.mb_utils/config.json')

    try:
        config_data = Config.read_config(config_file)
    except IOError:
        print("ERROR: no configuration file found. Need to create a config file in the current directory or use system "
              "provided file in ~/.mb_utils")
        sys.exit(1)
    args = get_args()

    # Make a call to MATCHbox to get a JSON obj of data.
    if not args.json:
        sys.stdout.write('Retrieving MATCHBox data object.  This will take a few minutes...')
        sys.stdout.flush()
    data = MatchboxData(config_data['url'],config_data['creds'],args.json)
    sys.stdout.write('\n')

    query_list = []
    if args.batch:
        query_list = read_batchfile(args.batch)
    else:
        query_list = args.ids.split(',')

    valid_ids = validate_list(query_list)
    print('Getting MSN / PSN mapping data...')
    map_id(data,valid_ids,args.psn,args.msn)

