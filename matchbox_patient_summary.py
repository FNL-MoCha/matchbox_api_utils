#!/usr/local/bin/python3
import sys
import os
import json
import argparse
import datetime
from pprint import pprint as pp

def get_args():
    version = '0.0.1_111816'
    parser = argparse.ArgumentParser(
        formatter_class = lambda prog: argparse.HelpFormatter(prog, max_help_position=100, width=150),
        description=
        '''
        <description>
        '''
    )
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

def patient_summary(data):
    filtered = data.get_patients_and_disease()
    for patient in filtered:
        print(','.join(patient))

if __name__=='__main__':
    args = get_args()
    patients = args.psn.split(',')
    pp(patients)
    sys.exit()
    
    patient_summary(data)
