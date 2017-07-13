#!/usr/bin/env python
# Input a set of variants and output a hitrate  for NCI-MATCH
import sys
import os
import json
import csv
import argparse
from pprint import pprint as pp

from matchbox_api_utils.Matchbox import MatchboxData

version = '0.10.1_071317'

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
    parser.add_argument('-v', '--version', action='version', version = '%(prog)s - ' + version)
    args = parser.parse_args()

    #if args.snv == args.indel == args.cnv == args.fusion == None:
    if all(x == None for x in [args.snv,args.indel,args.cnv,args.fusion]):
        sys.stderr.write('WARN: No SNV, Indel, CNV, or Fusion gene(s) added to query. Will output all MOIs.\n')
        #sys.exit(1)
    return args

def parse_query_results(data,vartype):
    wanted_data = []
    if vartype == 'snv':
        wanted_data = ['identifier','gene','type','alleleFrequency','transcript','hgvs','protein','oncominevariantclass']
    elif vartype == 'cnv':
        wanted_data = ['gene','type','copyNumber']
    elif vartype == 'fusion':
        wanted_data = ['identifier','gene','type','driverReadCount']
    return map(data.get,wanted_data)

def print_results(query_data,outfile,fmt):
    if fmt == 'pp':
        print('ERROR: pretty print output is not yet configured. Choose TSV or CSV for now')
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
            csv_writer.writerow(var_data)

def split_genes(x):
    return [y.upper() for y in x.split(',')]

if __name__=='__main__':
    config_file = os.path.join(os.environ['HOME'], '.mb_utils/config.json')
    if not os.path.isfile(config_file):
        config_file = os.path.join(os.getcwd(), 'config.json')

    try:
        config_data = Config.read_config(config_file)
    except IOError:
        sys.stderr.write('ERROR: No configuration file found! Need to create a '
            'config file in the current directory or use the system provided one '
            'in ~/.mb_utils/config.json (preferred).\n')
        sys.exit(1)

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
    if query_list:
        pp(query_list)
    else:
        sys.stdout.write("\t-> Output all MOIs\n")
    patient_list = []

    if args.psn:
        patient_list = [str(x) for x in args.psn.split(',')]
    else:
        patient_list = None
    print("patients to query: {}".format(args.psn))

    # Make a call to MATCHbox to get a JSON obj of data.
    if not args.json:
        sys.stdout.write('Retrieving MATCHBox data object.  This will take a few minutes...')
        sys.stdout.flush()
    data = MatchboxData(config_data['url'],config_data['creds'],dumped_data=args.json)
    sys.stdout.write('\n')

    # Gen a query result
    query_data,total = data.find_variant_frequency(query_list,patient_list)
    print('total patients queried: {}\n'.format(total))
    print_results(query_data,args.output,args.style)
