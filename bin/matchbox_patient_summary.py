#!/usr/bin/env python
import sys
import os
import json
import argparse
import datetime
from pprint import pprint as pp

from matchbox_api_utils.Matchbox import MatchboxData

version = '0.7.0_061217'

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
        formatter_class = lambda prog: argparse.HelpFormatter(prog, max_help_position=100, width=150),
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
    parser.add_argument('-o', '--outfile', metavar='<results.txt>', 
            help='Name of output file. DEFAULT: STDOUT.')
    parser.add_argument('-v', '--version', action='version', version = '%(prog)s  -  ' + version)    
    args = parser.parse_args()
    return args

def gen_header(dtype,total):
    today = datetime.date.today().strftime('%m/%d/%Y')
    print(":::  MATCH {} Summary as of {} (Total Screened: {})  :::\n".format(dtype,today,total))

def disease_summary(data):
    '''
    Generate a summary report of MATCH patients that have been biopsied and the counts for each disease type.
    '''
    total, diseases = data.get_disease_summary()
    print('Disease\tCount')
    for elem in sorted(diseases,key=diseases.get,reverse=True):
        print('\t'.join([elem,str(diseases[elem])]))

def patient_summary(data,patients=None):
    '''Print out a summary for each patient and their disease, excluding any that do not have disease data indicated'''
    filtered = data.get_patients_and_disease()
    total_screened = data.get_num_patients(has_biopsy=True)
    
    if patients:
        results = [','.join(patient) for patient in filtered if patient[1] != '-' and patient[0] in patients]
    else:
        results = [','.join(patient) for patient in filtered if patient[1] != '-']

    gen_header('Patient', '{}/{}'.format(len(results),total_screened))

    print('PSN,Disease')
    for i in results:
        print(i)
    return

if __name__=='__main__':
    try:
        config_file = (os.path.join(os.path.dirname(__file__), '../config.json'))
    except:
        config_file = os.path.join(os.environ['HOME'],'.mb_utils/config.json')

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
        patient_summary(data,patients)
    elif args.result_type == 'disease':
        # TODO: Would be cool to add a filter here to, say, filter on only Breast Cancer or something
        disease_summary(data)
