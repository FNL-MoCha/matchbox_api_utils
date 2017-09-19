#!/usr/bin/env python
import sys
import os
import csv
import argparse
from collections import defaultdict
from pprint import pprint as pp

from matchbox_api_utils import MatchData

version = '1.1.0'

def get_args():
    parser = argparse.ArgumentParser(
        description = 
        '''
        Generate a table indicating the aMOIs for a patient based on a patient list or an arm list.
        '''
    )
    parser.add_argument('-p', '--psn', metavar='<psn(s)>', help='Comma separated string of PSNs to search.')
    parser.add_argument('-a', '--arm', metavar='<ArmID>', help='Comma separated string of official MATCH '
        'Arm ID(s) if filtering by arm.')
    parser.add_argument('-f', '--file', metavar='<batchfile>', help='Get list of PSNs from a batch file with '
        'one PSN per line rather that inputting list on commandline.')
    parser.add_argument('-o', '--output', metavar='<outfile>', help='Write output to file instead of STDOUT.')
    parser.add_argument('-v', '--version', action='version', version='%(prog)s - ' + version)
    args = parser.parse_args()

    psn_list = []
    arms = []

    if args.psn:
        psn_list = args.psn.split(',')

    if args.file:
        psn_list = parse_batchfile(args.file)

    if args.arm:
        arms = args.arm.split(',')
        if any(not x.startswith('EAY131') for x in arms):
            sys.stderr.write('ERROR: not all input arms follow official MATCH naming: "EAY131-???"\n.')
            sys.stderr.write('Can not filter by arm.\n')
            arms = []

    if args.output:
        outfh = open(arg.output,'w')
    else:
        outfh = sys.stdout
    
    return(psn_list, arms, outfh)

def parse_batchfile(input_file):
    with open(input_file) as fh:
        return [line.rstrip('\n') for line in fh]

def get_measurement_and_gene(var_type,var_dict):
    if var_type == 'copyNumberVariants':
        return var_dict['copyNumber'],var_dict['gene'],'-'
    elif var_type == 'unifiedGeneFusions':
        return var_dict['driverReadCount'],var_dict['driverGene'],'-'
    else:
        return var_dict['alleleFrequency'],var_dict['gene'],var_dict['protein']

def make_hgvs(input_type,var_data):
    '''
    coding: tscript(gene):cds:aa
    genomic: g.(locus):ref>alt
    '''
    if input_type == 'snvs_indels':
    # if input_type == 'indels' or input_type == 'singleNucleotideVariants':
        return '{}({}):{}:{}'.format(var_data['transcript'], var_data['gene'], var_data['hgvs'], var_data['protein'])
    elif input_type == 'fusions':
    # elif input_type == 'unifiedGeneFusions':
        return var_data['identifier']
    elif input_type == 'cnvs':
    # elif input_type == 'copyNumberVariants':
        return var_data['gene'] + ':amp' 
    else:
        print('ERROR: input type "%s" is not valid.' % input_type)
        return None

def parse_var_report(var_report,armid):
    '''
    primary_amoi,other_amois = parse_var_report(var_report)
    '''
    primary_amois = secondary_amois = []
    # for var_type in ('indels','singleNucleotideVariants','copyNumberVariants','unifiedGeneFusions'):
        # if var_type in var_report:
            # for var in var_report[var_type]:
    for var_type in var_report:
        for var in var_report[var_type]:
            hgvs = make_hgvs(var['type'],var)
            measurement,gene,codon = get_measurement_and_gene(var['type'],var)
            # Here is good place to store MOIs if we want them.
            if var['amoi'] is None:
                continue
            elif armid in var['amoi']:
                print('var is amoi')
            else:
                pp(var['amoi'])
    return primary_amois,secondary_amois
                    
def get_data(mb_data,psn=None,msn=None):
    results = {}

    if msn:
        psn = mb_data.get_psn(msn=str(msn))

    psn = str(psn).lstrip('PSN')
    results['psn'] = 'PSN' + psn
    results['disease'] = data.get_patients_and_disease(psn=psn)[psn]
    results['msn'] = mb_data.get_msn(psn=psn)
    results['bsn'] = mb_data.get_bsn(psn=psn)
    results['mois'] = []
    results['arms'] = data.get_patient_ta_status(psn=psn)

    variant_data = mb_data.get_variant_report(psn=psn)
    if variant_data:
        for var_type in variant_data:
            for var in variant_data[var_type]:
                hgvs = make_hgvs(var['type'],var)
                if var['amoi'] is None:
                    amois = None
                else:
                    # for amoi in var['amoi']:

                    amois = ','.join(var['amoi'])

                measurement,gene,codon = get_measurement_and_gene(var['type'],var)
                results['mois'].append((gene,codon,measurement,hgvs,amois))
    return results 

def print_results(data,filename=None):
    if not filename:
        filename='output.csv'

    with open(filename, 'w') as outfh:
        writer = csv.writer(outfh, delimiter=',')

        header = ['PSN','BSN','MSN(s)','Disease','Num aMOIs','Gene','Codon','Measurement','HGVS','aMOI Arm(s)']
        writer.writerow(header)

        wanted = ['psn','bsn','msn','disease']

        for patient in data:
            num_amois = 0
            output = [data[patient][x] for x in wanted]
            if data[patient]['mois'] is not None:
                for var in data[patient]['mois']:
                    if var[4] is not None: #var[4] is None if not an aMOI (i.e. only a MOI).
                        output += list(var)
                        num_amois += 1

            if num_amois > 0:
                output.insert(4,num_amois)
                writer.writerow(output)

if __name__=='__main__':
    psn_query, arms, outfh = get_args()
    patients_list = []
    variant_results = {}

    data = MatchData()
    # get_data(data,psn=10837)
    # sys.exit()

    if not patients_list:
        print('No input file list passed. Retrieving data for all patients...')
        patients_list = data.get_patients_and_disease().keys()


    for pt in patients_list:
        # variant_results[patients_list[pt]] = get_data(data,psn=patients_list[pt])
        variant_results[pt] = get_data(data,psn=pt)
        # print('-'*50)

    get_variant_report_metrics(variant_results)
    print_results(variant_results)

