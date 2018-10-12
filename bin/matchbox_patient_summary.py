#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Get patient or disease summary statistics and data from the MATCH dataset. 

Choosing the ``patient`` option will allow one to get a listing of patients in
the study and their respective disease. One can also filter that list down by 
specifying a PSN (or comma separated list of PSNs) of interest

Choosing the ``disease`` option will give a summary of the types and counts of
each disease in the study.  Similar to the patients query, one can filter the 
list down by inputting MEDDRA codes or tumor hisologies.  Note that you must 
quote tumor names with spaces in them, and they must exactly match the string
indicated in MATCHBox.  The use of MEDDRA codes is recommended and preferred.
"""
import sys
import os
import json
import argparse
import datetime
import csv

from operator import itemgetter
from pprint import pprint as pp

from matchbox_api_utils import MatchData

version = '3.0.101218'

def get_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        'matchbox', 
        metavar='<matchbox>', 
        help='Name of MATCHBox system to which the connection will be made. '
        'Valid systems are "adult", "ped", "adult-uat".'
    )
    parser.add_argument(
        'result_type', 
        choices=['patient','disease'], 
        help='Category of data to output. Can either be patient or disease '
            'level.'
    )
    parser.add_argument(
        '-l', '--live', 
        action='store_true',
        help='Make a live call to MATCHBox rather than loading a local JSON '
            'containing patient data, usually from matchbox_json_dump.py'
    )
    parser.add_argument(
        '-p', '--psn', 
        metavar='PSN', 
        help='Filter patient summary to only these patients. Can be a comma '
            'separated list'
    )
    parser.add_argument(
        '-t', '--tumor', 
        metavar='<tumor_type>', 
        help='Retrieve data for only this tumor type or comma separate '
            'list of tumors. Note that you must quote tumors with names '
            'containing spaces.'
    )
    parser.add_argument(
        '-m', '--meddra', 
        metavar='<meddra_code>', 
        help='MEDDRA Code or comma separated list of codes to search.'
    )
    parser.add_argument(
        '-O','--Outside',
        action='store_true',
        help='Include Outside Assay study data (DEFAULT: False).'
    )
    parser.add_argument(
        '-o', '--outfile', 
        metavar='<output csv>', 
        help='Name of output file. Output will be in CSV format. DEFAULT: '
        'STDOUT.'
    )
    parser.add_argument(
        '-v', '--version', 
        action='version', 
        version = '%(prog)s - v' + version
    )
    args = parser.parse_args()
    return args

def disease_summary(data, outfh, ctep_term=None, meddra=None):
    '''
    Generate a summary report of MATCH patients that have been biopsied and the
    counts for each disease type. Data coming in from get_disease_summary() will
    be a dict of tuples.
    '''
    total = 0
    disease_counts = data.get_disease_summary(query_disease=ctep_term, 
            query_meddra=meddra)

    outfh.writerow(['MEDDRA_Code', 'Count', 'Disease'])
    for elem, val in sorted(
        disease_counts.items(),
        key=lambda vals: itemgetter(1)(vals[1]), reverse=True
    ):
        outfh.writerow([elem, str(val[1]), val[0]])
        total += val[1]

    print('\n:::  Total cases: {}  :::'.format(total))

def patient_summary(data, outfh, patients=None, outside=False):
    '''
    Print out a summary for each patient and their disease, excluding any that
    do not have disease data indicated
    '''

    # Get total number of biopsies collected that had a "PASS" status.
    num_collected_biopsies = data.get_biopsy_summary(category='pass')['pass']

    results = {}
    if patients:
        for patient in patients:
            return_data = data.get_histology(psn=patient)
            if return_data:
                # have to correct entry if we do not add PSN to the front.
                patient = 'PSN' + patient.lstrip('PSN')
                results[patient] = return_data[patient]
    else:
        results = data.get_histology(outside=outside, no_disease=False)

    if results:
        today = datetime.date.today().strftime('%m/%d/%Y')
        
        sys.stderr.write(
            ":::  MATCH {} Summary as of {} (Query PSNs: {}; Total Passed "
            "Biopsies: {})  :::\n".format('Patient', today, len(results), 
             num_collected_biopsies)
        )

        outfh.writerow(['PSN','BSN','MSN','Disease'])
        for res in sorted(results.keys()):
            # just take latest biopsy; don't need all.
            try:
                bsn = data.get_bsn(psn=res)[-1] 
            except IndexError:
                # If we got here, then there is no passed biopsy for this 
                # patient and we can skip the result
                continue
            msn = data.get_msn(psn=res)
            # If we got no MSN, that means we didn't get a successful 
            # sequencing run, and the data is not going to be so useful. Skip 
            # those.
            if len(msn) < 1:
                continue
            outfh.writerow([res, bsn, '|'.join(msn), results[res]])
    else:
        sys.stderr.write("ERROR: No data for input patient list!\n")
        sys.exit(1)
    return

if __name__=='__main__':
    args = get_args()

    patients = []
    if args.psn:
        patients = args.psn.split(',')

    json_db='sys_default'
    if args.live:
        sys.stdout.write('Retrieving a live MATCHBox data object. This may '
            'take a few minutes...\n')
        sys.stdout.flush()
        json_db = None

    data = MatchData(matchbox=args.matchbox, method='mongo', json_db=json_db,
        quiet=True)
    sys.stdout.write('Database date: %s.\n' % data.db_date)

    if args.outfile:
        sys.stdout.write('Writing results to %s.\n' % args.outfile)
        outfh = csv.writer(open(args.outfile, 'w'))
    else:
        outfh = csv.writer(sys.stdout)

    if args.result_type == 'patient':
        patient_summary(data, outfh, patients, outside=args.Outside)

    elif args.result_type == 'disease':
        if args.tumor:
            tumor_list = args.tumor.split(',')
            disease_summary(data, outfh, ctep_term=tumor_list)
        elif args.meddra:
            meddra_list = args.meddra.split(',')
            disease_summary(data, outfh, meddra=meddra_list)
        else:
            disease_summary(data, outfh)
