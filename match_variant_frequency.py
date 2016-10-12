#!/usr/bin/python
# Input a set of variants and output a hitrate  for NCI-MATCH
import sys
import os
import json
import csv
import argparse
from pprint import pprint as pp

from Matchbox import *

version = '0.7.0_100716'

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
        ''',
        version = '%(prog)s  -  ' + version,
    )
    parser.add_argument('-j', '--json', metavar='<mb_json_file>', 
            help='Load a MATCHBox JSON file derived from "matchbox_json_dump.py" instead of a live query')
    parser.add_argument('-p', '--psn', metavar='<PSN>', 
            help='Only output data for a specific patient or comma separated list of patients')
    parser.add_argument('-s', '--snv', metavar='<gene_list>', 
            help='Comma separated list of SNVs to look up in MATCHBox data.')
    parser.add_argument('-c', '--cnv', metavar='<gene_list>',
            help='Comma separated list of CNVs to look up in MATCHBox data.')
    parser.add_argument('-f', '--fusion', metavar='<gene_list>', 
            help='Comma separated list of Fusions to look up in MATCHBox data.')
    parser.add_argument('-i', '--indel', metavar='<gene_list>', 
            help='Comma separated list of Fusions to look up in MATCHBox data.')
    parser.add_argument('--style', metavar='<pp,csv,tsv>', default='csv',
            help='Format for output. Can choose pretty print (pp), CSV, or TSV')
    parser.add_argument('-o', '--output', metavar='<output_file>', default='stdout',
            help='Output file to which to write data. Default is stdout')
    args = parser.parse_args()

    if args.snv == args.indel == args.cnv == args.fusion == None:
        sys.stderr.write('ERROR: No SNV, Indel, CNV, or Fusion gene(s) added to query. You must select at least one type to search!\n')
        sys.exit(1)
    return args

def parse_query_results(data,vartype):
    wanted_data = []
    if vartype == 'snv':
        wanted_data = ['identifier','gene','type','alleleFrequency','transcript','hgvs','protein','oncominevariantclass']
    elif vartype == 'cnv':
        wanted_data = ['gene','type','copyNumber']
    elif vartype == 'fusion':
        wanted_data = ['gene','type','driverReadCount']
    return map(data.get,wanted_data)

def print_results(query_data,outfile,fmt):
    # TODO: Need to add differential format code
    # pp(query_data)
    if fmt == 'pp':
        print('ERROR: pretty print output is not yet configured. Choose TSV or CSV for now')
        sys.exit(1)

    format_list = {
        'csv' : ',',
        'tsv' : '\t',
    }
    # print('format is: %s' % fmt)
    delimiter = format_list[fmt]

    csv_writer = ''
    if outfile != 'stdout':
        fh = open(outfile,'w')
        csv_writer = csv.writer(fh,delimiter=delimiter)
    else:
        csv_writer = csv.writer(sys.stdout,delimiter=delimiter)

    header = ['Patient','Disease','VarID','Gene','Type','Measurement','Transcript','CDS','AA','Function']
    csv_writer.writerow(header)
    
    for patient in query_data:
        for moi in query_data[patient]['mois']:
            var_data = [query_data[patient]['psn'],query_data[patient]['disease']]
            if moi['type'] == 'snvs_indels':
                var_data += parse_query_results(moi,'snv')
            elif moi['type'] == 'cnvs':
                var_data += parse_query_results(moi,'cnv')
                var_data.insert(2,'.')
            elif moi['type'] == 'fusions':
                var_data += parse_query_results(moi,'fusion')
                var_data.insert(2,'.')
            csv_writer.writerow(var_data)

def split_genes(x):
    return [y.upper() for y in x.split(',')]

if __name__=='__main__':
    config_file = 'config.json'
    config_data = Config.read_config(config_file)
    args = get_args()

    query_list = {}
    if args.snv:
        query_list['snvs'] = split_genes(args.snv)
    if args.indel:
        query_list['indels'] = split_genes(args.indel)
    if args.cnv:
        query_list['cnvs'] = split_genes(args.cnv)
    if args.fusion:
        query_list['fusions'] = split_genes(args.fusion)

    print("variants to query: ")
    pp(query_list)
    patient_list = []
    if args.psn:
        patient_list = [str(x) for x in args.psn.split(',')]
    else:
        patient_list = None

    print("patients to query: ")
    pp(patient_list)
    # Make a call to MATCHbox to get a JSON obj of data.
    if not args.json:
        sys.stdout.write('Retrieving MATCHBox data object.  This will take a few minutes...')
    # TODO: Fix the patient filter.  this is not quite working right
    #    - The filter is actually not pulling the correct data from the MB obj.
    #    - The filter only works on the intial call to the MB OBJ. So a mb.json file, for example, will not yield
    #      the correct result for example since it already has all patients filtered in!
    data = MatchboxData(config_data['url'],config_data['creds'],args.json,patient_list)
    sys.stdout.write('Done!\n')

    # Gen a query result
    query_data,total = data.find_variant_frequency(query_list)
    print('total patients queried: {}\n'.format(total))
    print_results(query_data,args.output,args.style)
