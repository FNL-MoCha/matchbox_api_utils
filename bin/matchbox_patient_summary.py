#!/usr/bin/env python
import sys
import os
import json
import argparse
import datetime
from pprint import pprint as pp

# Dirty hack for right now to see if we can figure out how call this as an external script
# TODO: Fix this once we make a real package.
# bin_path = os.path.dirname(os.path.realpath(__file__)).rstrip('/bin')
# sys.path.append(bin_path)
from matchbox_api_utils.Matchbox import MatchboxData

version = '0.7.0_061217'

def get_args():
    parser = argparse.ArgumentParser(
        formatter_class = lambda prog: argparse.HelpFormatter(prog, max_help_position=100, width=150),
        description=
        '''
        <description>
        '''
    )
    parser.add_argument('data', help='MATCHBox JSON file containing patient data, usually from matchbox_json_dump.py')
    parser.add_argument('-p', '--psn', metavar='PSN', 
            help='Filter patient summary to only these patients. Can be a comma separated list')
    parser.add_argument('-v', '--version', action='version', version = '%(prog)s  -  ' + version)
    parser.add_argument('-o', '--outfile', metavar='<out.json>', 
            help='Name of output file. DEFAULT: STDOUT.')
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
    if patients:
        results = [','.join(patient) for patient in filtered if patient[1] != '-' and patient[0] in patients]
    else:
        results = [','.join(patient) for patient in filtered if patient[1] != '-']

    gen_header('Patient',len(results))
    print('PSN,Disease')
    for i in results:
        print(i)
    return

if __name__=='__main__':
    '''If running standalone.  Can only start with MB JSON file'''
    args = get_args()
    patients = []
    if args.psn:
        patients = args.psn.split(',')
    data = MatchboxData(None,None,args.data)
    patient_summary(data,patients)
