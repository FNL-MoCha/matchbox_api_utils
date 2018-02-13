#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Get patient or disease summary statistics and data from the MATCH dataset.  
"""
import sys
import os
import json
import argparse
import datetime
from operator import itemgetter
from pprint import pprint as pp

from matchbox_api_utils import MatchData

version = '2.1.020518'

def get_args():
    parser = argparse.ArgumentParser(
        formatter_class = lambda prog: argparse.HelpFormatter(prog, 
            max_help_position=100, width=125),
        description=__doc__
    )
    parser.add_argument('result_type', choices=['patient','disease'], 
            help='Category of data to output. Can either be patient or disease level.')
    parser.add_argument('-j', '--json', metavar='<mb_json_file>', default='sys_default',
            help='MATCHBox JSON file containing patient data, usually from matchbox_json_dump.py')
    parser.add_argument('-p', '--psn', metavar='PSN', 
            help='Filter patient summary to only these patients. Can be a comma separated list')
    parser.add_argument('-t', '--tumor', metavar='<tumor_type>', 
            help='Retrieve data for only this tumor type or comma separate list of tumors. Note '
                'that you must quote tumors with names containing spaces.')
    parser.add_argument('-m', '--medra', metavar='<medra_code>', 
            help='MEDRA Code or comma separated list of codes to search.')
    parser.add_argument('-O','--Outside', action='store_true', 
            help='Include Outside Assay study data (DEFAULT: False).')
    parser.add_argument('-o', '--outfile', metavar='<results.txt>', 
            help='Name of output file. DEFAULT: STDOUT.')
    parser.add_argument('-v', '--version', action='version', version = '%(prog)s  -  ' + version)    
    args = parser.parse_args()

    if args.json == 'None':
        args.json = None

    return args

def disease_summary(data, ctep_term=None, medra=None):
    '''
    Generate a summary report of MATCH patients that have been biopsied and the
    counts for each disease type. Data coming in from get_disease_summary() will
    be a dict of tuples.
    '''
    total = 0
    disease_counts = data.get_disease_summary(query_disease=ctep_term, query_medra=medra)

    print('MEDRA_Code\tCount\tDisease')
    for elem, val in sorted(disease_counts.iteritems(), 
            key=lambda (k,v): itemgetter(1)(v), reverse=True):
        print('\t'.join([elem, str(val[1]), val[0]]))
        total += val[1]

    # print('\n:::  Total cases: {}  :::'.format(total))

def print_line(x,y,z):
    print(','.join([x,y,z]))

def patient_summary(data,outfh,patients=None,outside=False,):
    '''
    Print out a summary for each patient and their disease, excluding any that
    do not have disease data indicated
    '''

    # Get total number of biopsies collected that had a "PASS" status.
    num_collected_biopsies = data.get_biopsy_summary(category='pass').values()[0]

    results = {}
    if patients:
        for patient in patients:
            return_data = data.get_histology(psn=patient)
            # TODO: Get patient last status here
            # status = data.get_patient
            if return_data:
                # have to correct entry if we do not add PSN to the front.
                patient = 'PSN' + patient.lstrip('PSN')
                results[patient] = return_data[patient]
    else:
        results = data.get_histology(outside=outside,no_disease=False)

    if results:
        today = datetime.date.today().strftime('%m/%d/%Y')
        
        outfh.write(":::  MATCH {} Summary as of {} (Query PSNs: {}; Total Passed "
                "Biopsies: {})  :::\n".format('Patient', today, len(results), 
                    num_collected_biopsies))

        outfh.write('PSN,BSN,MSN,Disease\n')
        for res in sorted(results.keys()):
            bsn = data.get_bsn(psn=res)[-1] # just take last biopsy; don't need all.
            msn = data.get_msn(psn=res)
            # If we got no MSN, that means we didn't get a successful sequencing run, 
            # and the data is not going to be so useful. Skip those.
            if len(msn) < 1:
                continue
            outfh.write(','.join([res, bsn, '|'.join(msn), results[res]]))
            outfh.write('\n')
    else:
        sys.stderr.write("ERROR: No data for input patient list!\n")
        sys.exit(1)
    return

if __name__=='__main__':
    args = get_args()

    if args.outfile:
        sys.stdout.write('Writing results to %s.\n' % args.outfile)
        outfh = open(args.outfile, 'w')
    else:
        outfh = sys.stdout

    patients = []
    if args.psn:
        patients = args.psn.split(',')

    if not args.json:
        sys.stdout.write('WARN: No MATCHBox JSON dump obj loaded. Performing live '
            'queries can take a few minutes, and be sped up by loading a JSON obj '
            'from `matchbox_json_dump.py` first.\n')
        sys.stdout.flush()

    data = MatchData(json_db=args.json)

    if args.result_type == 'patient':
        patient_summary(data, outfh, patients, outside=args.Outside)
    elif args.result_type == 'disease':
        if args.tumor:
            tumor_list = args.tumor.split(',')
            disease_summary(data, ctep_term=tumor_list)
        elif args.medra:
            medra_list = args.medra.split(',')
            disease_summary(data, medra=medra_list)
        else:
            disease_summary(data)
