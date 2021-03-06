#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Input a list of genes by variant type and get back a table of NCI-MATCH hits 
that can be further analyzed in Excel. Can either input a patient (or comma 
separated list of patients) to query, or query the entire dataset.  Will limit
the patient set to the non-outside assay results only.
"""
import sys
import os
import json
import csv
import argparse
from pprint import pprint as pp

from matchbox_api_utils import MatchData

version = '2.0.101218'

def get_args():
    parser = argparse.ArgumentParser(description=__doc__,)
    parser.add_argument('matchbox', metavar='<matchbox>', help='Name of '
        'MATCHBox system to which the connection should be made.  Valid names '
        'are "adult", "ped", adult-uat".')
    parser.add_argument('-l', '--live', action='store_true',
        help='Get a live MATCHBox query instead of loading a local JSON file' 
        'derived from "matchbox_json_dump.py"')
    parser.add_argument('-p', '--psn', metavar='<PSN>', help='Only output data '
        'for a specific patient or comma separated list of patients')
    parser.add_argument('-s', '--snv', metavar='<gene_list>', 
        help='Comma separated list of SNVs to look up in MATCHBox data.')
    parser.add_argument('-c', '--cnv', metavar='<gene_list>',
        help='Comma separated list of CNVs to look up in MATCHBox data.')
    parser.add_argument('-f', '--fusion', metavar='<gene_list>', 
        help='Comma separated list of Fusions to look up in MATCHBox data.')
    parser.add_argument('-i', '--indel', metavar='<gene_list>', 
        help='Comma separated list of Fusions to look up in MATCHBox data.')
    parser.add_argument('-a', '--all', metavar='<all_types>', 
        help='Query variants across all variant types for a set of genes, '
        'rather than one by one.  Helpful if one wants to find any BRAF '
        'MOIs, no matter what type, for example.')
    parser.add_argument('--style', metavar='<pp,csv,tsv>', default='csv',
        help='Format for output. Can choose pretty print (pp), CSV, or TSV')
    parser.add_argument('-o', '--output', metavar='<output_file>',
        default='stdout', help='Output file to which to write data Default '
        'is stdout')
    parser.add_argument('-v', '--version', action='version', 
        version = '%(prog)s - ' + version)
    args = parser.parse_args()

    '''
    # TODO: Maybe....allow an option to print out all of the MOIs reported in
            MATCHBox in total.  I think this is not useful, and it's hard to
            know what to print as the find_variant_frequency() method does not
            have a way to handle this.  Maybe we can get some kind of large 
            gene list from somewhere to do this.  But, it's going to be such a
            rare request that I'm not sure it's worth it.
    if all(x == None for x in [args.snv, args.indel, args.cnv, args.fusion, 
        args.all]):
        sys.stderr.write('WARN: No SNV, Indel, CNV, or Fusion gene(s) added '
            'to query. Will output all MOIs.\n')
    '''

    return args

def parse_query_results(data,vartype):
    wanted_data = []
    if vartype == 'snv':
        wanted_data = ['identifier', 'gene', 'type', 'alleleFrequency', 
            'transcript', 'hgvs', 'protein', 'oncominevariantclass']
    elif vartype == 'cnv':
        wanted_data = ['gene', 'type', 'copyNumber']
    elif vartype == 'fusion':
        wanted_data = ['identifier', 'gene', 'type', 'driverReadCount']
    return map(data.get, wanted_data)

def print_results(query_data,outfile,fmt):
    if fmt == 'pp':
        print('ERROR: pretty print output is not yet configured. Choose TSV '
            'or CSV for now.')
        sys.exit(1)

    format_list = {
        'csv' : ',',
        'tsv' : '\t',
    }
    delimiter = format_list[fmt]

    csv_writer = ''
    if outfile != 'stdout':
        fh = open(outfile,'w')
        csv_writer = csv.writer(fh,delimiter=delimiter)
    else:
        csv_writer = csv.writer(sys.stdout,delimiter=delimiter)

    header = ['Patient', 'Disease', 'VarID', 'Gene', 'Type', 'Measurement',
            'Transcript', 'CDS', 'AA', 'Function']
    csv_writer.writerow(header)
    
    for patient in query_data:
        for moi in query_data[patient]['mois']:
            var_data = [
                query_data[patient]['psn'], 
                query_data[patient]['disease']
            ]
            if moi['type'] == 'snvs_indels':
                var_data += parse_query_results(moi,'snv')
            elif moi['type'] == 'cnvs':
                var_data += parse_query_results(moi,'cnv')
                var_data.insert(2,'.')
            elif moi['type'] == 'fusions':
                var_data += parse_query_results(moi,'fusion')
            csv_writer.writerow(var_data)

def split_genes(x):
    return [y.upper() for y in x.split(',')]

if __name__=='__main__':
    args = get_args()

    # Make a call to MATCHbox to get a JSON obj of data.
    json_db = 'sys_default'
    if args.live:
        sys.stdout.write('Retrieving MATCHBox data object.  This will take a '
            'few minutes...')
        sys.stdout.flush()

    data = MatchData(matchbox=args.matchbox, method='mongo', json_db=json_db, 
        quiet=True)
    sys.stdout.write('Database date: %s.\n' % data.db_date)

    query_list = {}
    if args.snv:
        query_list['snvs'] = split_genes(args.snv)
    if args.indel:
        query_list['indels'] = split_genes(args.indel)
    if args.cnv:
        query_list['cnvs'] = split_genes(args.cnv)
    if args.fusion:
        query_list['fusions'] = split_genes(args.fusion)
    if args.all:
        for vtype in ('snvs', 'indels', 'cnvs', 'fusions'):
            query_list[vtype] = split_genes(args.all)

    print("Variants to query: ")
    pp(query_list)

    patient_list = []
    if args.psn:
        patient_list = [str(x) for x in args.psn.split(',')]
    else:
        patient_list = None
    
    print("Patients to query: {}".format(patient_list))

    # Gen a query result
    query_data, patient_total, biopsy_total = data.find_variant_frequency(
            query_list, patient_list)
    print('Total patients queried: {}'.format(patient_total))
    print('Total biopsies queried: {}\n'.format(biopsy_total))
    print_results(query_data, args.output, args.style)
