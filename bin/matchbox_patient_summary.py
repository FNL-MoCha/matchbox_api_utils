#!/usr/bin/env python
import sys
import os
import json
import argparse
import datetime
from pprint import pprint as pp

from matchbox_api_utils import MatchboxData

version = '0.10.1_071717'

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
        with open(config_file) as fh:
            data = json.load(fh)
        return data


def get_args():
    parser = argparse.ArgumentParser(
        formatter_class = lambda prog: argparse.HelpFormatter(prog, max_help_position=100, width=125),
        description=
        '''
        Get patient or disease summary statistics and data from the MATCH dataset.  
        '''
    )
    parser.add_argument('result_type', choices=['patient','disease'], 
            help='Type of data to output.')
    parser.add_argument('-j', '--json', metavar='<mb_json_file>',
            help='MATCHBox JSON file containing patient data, usually from matchbox_json_dump.py')
    parser.add_argument('-p', '--psn', metavar='PSN', 
            help='Filter patient summary to only these patients. Can be a comma separated list')
    parser.add_argument('-t', '--tumor', metavar='<tumor_type>', 
            help='Retrieve data for only these tumor types')
    parser.add_argument('-O','--Outside', action='store_true', 
            help='Include Outside Assay study data (DEFAULT: False).')
    parser.add_argument('-o', '--outfile', metavar='<results.txt>', 
            help='Name of output file. DEFAULT: STDOUT.')
    parser.add_argument('-v', '--version', action='version', version = '%(prog)s  -  ' + version)    
    args = parser.parse_args()
    return args

def gen_header(dtype,psns,biopsies):
    today = datetime.date.today().strftime('%m/%d/%Y')
    print(":::  MATCH {} Summary as of {} (Query PSNs: {}; Total Passed Biopsies: {})  :::\n".format(dtype,today,psns,biopsies))

def disease_summary(data):
    '''
    Generate a summary report of MATCH patients that have been biopsied and the counts for each disease type.
    '''
    total, diseases = data.get_disease_summary()
    print('Disease\tCount')
    for elem in sorted(diseases,key=diseases.get,reverse=True):
        print('\t'.join([elem,str(diseases[elem])]))

def print_line(x,y,z):
    print(','.join([x,y,z]))

def patient_summary(data,patients=None,outside=False):
    '''Print out a summary for each patient and their disease, excluding any that do not have disease data indicated'''
    biopsy_numbers = data.get_biopsy_numbers(has_biopsy=True)
    num_collected_biopsies = biopsy_numbers['passed_biopsy']

    results = {}
    if patients:
        for patient in patients:
            return_data = data.get_patients_and_disease(query_psn=patient)
            if return_data:
                results[patient] = return_data[patient]
    else:
        results = data.get_patients_and_disease(outside=outside)

    if results:
        gen_header('Patient', len(results), num_collected_biopsies)
        print('PSN,BSN,Disease')
        for res in sorted(results):
            bsn = data.get_bsn(psn=res)
            print_line(res,bsn,results[res])
    else:
        sys.stderr.write("ERROR: No data for input patient list!\n")
        sys.exit(1)
    return

if __name__=='__main__':
    config_file = os.path.join(os.environ['HOME'], '.mb_utils/config.json')
    if not os.path.isfile(config_file):
        config_file = os.path.join(os.getcwd(), 'config.json')

    try:
        config_data = Config.read_config(config_file)
    except IOError:
        print("ERROR: no configuration file found. Need to create a config file in the current directory or use system "
              "provided file in ~/.mb_utils")
        sys.exit(1)

    args = get_args()

    patients = []
    if args.psn:
        patients = args.psn.split(',')

    if not args.json:
        sys.stdout.write('WARN: No MATCHBox JSON dump obj loaded. Performing live queries can take a few minutes, and '
                         'be sped up by loading a JSON obj from `matchbox_json_dump.py` first.\n')
        sys.stdout.flush()

    data = MatchboxData(config_data['url'], config_data['creds'],dumped_data=args.json)

    if args.result_type == 'patient':
        patient_summary(data,patients,outside=args.Outside)
    elif args.result_type == 'disease':
        # TODO: Would be cool to add a filter here to, say, filter on only Breast Cancer or something
        disease_summary(data)
