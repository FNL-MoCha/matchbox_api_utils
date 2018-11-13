#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Input a valid NCI-MATCH Arm ID and get a list of patients and trial status 
information. Output intended to be similar to Treatment arms page of MATCHbox.
"""
import sys
import os
import argparse
import csv

from pprint import pprint as pp

from matchbox_api_utils import *

version = '1.0.111318'

def get_args():
    parser = argparse.ArgumentParser(description = __doc__)
    parser.add_argument(
        'armid', 
        metavar='<ARM ID>',
        help='Valid NCI-MATCH study arm, or comma separated list of study arms, '
            'in the format of EAY131-*.'
    )
    parser.add_argument(
        '-a', '--all', 
        action = 'store_true',
        help='Output "all" patients and do not filter out those that received '
            'compassionate care or other outcomes. Only output patients that '
            'were enrolled.'
    )
    parser.add_argument(
        '-O', '--Outside', 
        action = 'store_true',
        dest = 'outside', 
        help = 'Include "Outside Assays" results in output.  This may cause some '
            'problems with mapping and whatnot as the data are a bit scattershot. '
            'You have been warned!'
    )
    parser.add_argument(
        '-o', '--outfile', 
        metavar = '<outfile>', 
        help = 'Write results to a file instead of stdout.'
    )
    parser.add_argument(
        '-v', '--version', 
        action = 'version', 
        version = '%(prog)s - v' + version
    )
    args = parser.parse_args()
    return args

def filter_data(data):
    """
    If we don't want to output all patients that would have qualified for an 
    arm solely based on aMOIs, including those that received Compassionate
    Care, then filter those out.
    """
    wanted_terms = ('ON_TREATMENT_ARM', 'FORMERLY_ON_ARM_OFF_TRIAL', 
        'FORMERLY_ON_ARM_PROGRESSED')
    filtered = {}
    for patient in data:
        if data[patient]['status'] in wanted_terms:
            filtered[patient] = data[patient]
    return filtered

def print_data(results, outfile):
    header = ['ArmID', 'PSN', 'MSN', 'Histology', 'Status', 'Source']
    outfile.writerow(header)
    for record in results:
        outfile.writerow([
            results[record]['arm'],
            results[record]['psn'],
            results[record]['msn'],
            results[record]['hist'],
            results[record]['status'],
            results[record]['source']
        ])

def main(match_data, armids, output_all, outside, outfile):
    results = {}

    for arm in armids:
        arm_results = match_data.get_patients_by_arm(arm=arm, outside=outside)
        if len(arm_results) < 1:
            sys.stderr.write('No results for MATCH arm %s.\n' % armid)
        else:
            for rec in arm_results:
                try:
                    # Might not get an MSN for outside assays.
                    msn = match_data.get_msn(psn=rec[0])[0] # Just take first one
                except IndexError:
                    msn = 'unknown'

                histology = match_data.get_histology(psn=rec[0], outside=outside)
                source = match_data.get_patient_demographics(psn=rec[0])['source']

                results['%s|%s' %(arm, rec[0])] = {
                    'psn' : rec[0],
                    'arm' : rec[1],
                    'status' : rec[2],
                    'msn' : msn,
                    'hist' : histology['PSN%s' % rec[0]],
                    'source' : source
                }

    if output_all:
        print_data(results, outfile)
    else:
        filtered = filter_data(results)
        print_data(filtered, outfile)

if __name__ == '__main__':
    args = get_args()
    if args.outfile:
        sys.stderr.write('Writing results to file %s.\n' % args.outfile)
        fh = open(args.outfile, 'w')
        csv_fh = csv.writer(fh, lineterminator='\n')
    else:
        csv_fh = csv.writer(sys.stdout, lineterminator='\n')

    arms = args.armid.split(',')
    match_data = MatchData(quiet=True)

    main(match_data, arms, args.all, args.outside, csv_fh)
