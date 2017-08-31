#!/usr/bin/env python
# TODO:
#    1. Add a argparse function and make more flexible.  
import sys
import os
import csv
from collections import defaultdict
from pprint import pprint as pp

from matchbox_api_utils import *

version = '1.0'

def make_hgvs(input_type,var_data):
    '''
    coding: tscript(gene):cds:aa
    genomic: g.(locus):ref>alt
    '''
    if input_type == 'snv_indel':
        return '{}({}):{}:{}'.format(var_data['transcript'], var_data['gene'], var_data['hgvs'], var_data['protein'])
    elif input_type == 'fusion':
        return var_data['identifier']
    elif input_type == 'cnv':
        return var_data['gene'] + ':amp' 
    else:
        print('ERROR: input type "%s" is not valid.')
        return None

def get_data(mb_data,psn=None,msn=None):
    var_types = {
        'indels' : 'snv_indel', 
        'singleNucleotideVariants' : 'snv_indel', 
        'copyNumberVariants' : 'cnv',
        'unifiedGeneFusions' : 'fusion'
    }
    results = {}

    if msn:
        psn = mb_data.get_psn(msn=str(msn))

    psn = str(psn).lstrip('PSN')
    results['psn'] = 'PSN' + psn
    results['disease'] = data.get_patients_and_disease(psn=psn)[psn]
    results['msn'] = mb_data.get_msn(psn=psn)
    results['bsn'] = mb_data.get_bsn(psn=psn)
    results['mois'] = None

    variant_data = mb_data.get_variant_report(psn=psn)
    # pp(variant_data)
    # sys.exit()

    if variant_data:
        results['mois'] = []

        for var_type in ('indels','singleNucleotideVariants','copyNumberVariants','unifiedGeneFusions'):
            if var_type in variant_data:
                for var in variant_data[var_type]:
                    hgvs = make_hgvs(var_types[var_type],var)
                    if var['amoi'] is None:
                        amois = None
                    else:
                        amois = ','.join(var['amoi'])
                    measurement,gene,codon = get_measurement_and_gene(var_type,var)
                    results['mois'].append((gene,codon,measurement,hgvs,amois))
                    # print('{},{}'.format(make_hgvs('snv_indel',var),var['amoi']))
    # print(psn) 
    # pp(results)
    # sys.exit()
    return results 

def get_measurement_and_gene(var_type,var_dict):
    if var_type == 'copyNumberVariants':
        return var_dict['copyNumber'],var_dict['gene'],'-'
    elif var_type == 'unifiedGeneFusions':
        return var_dict['driverReadCount'],var_dict['driverGene'],'-'
    else:
        return var_dict['alleleFrequency'],var_dict['gene'],var_dict['protein']

def get_variant_report_metrics(data):
    """
    Get a count of number of MOIs for each patient, and number of aMOIs for each patient
    in aggregate and store in a dict. Then we can do some filtering to get a list of 
    patients with more than 1 aMOI for example.

    We'll either get data[patient]['mois'] == None or a list of tuples with the MOI being 
    in position one and the arms (i.e. it's an aMOI) being position 2.
    """
    # TODO: Fix this summary table.  
    patient_type_summary =  defaultdict(list)
    type_summary = {
        'no_mois' : 0,
        'one_moi' : 0,
        'one_amoi' : 0,
        'multi_mois' : 0,
        'multi_amois' : 0,
    }
    for patient in data:
        if not data[patient]['mois']:
            type_summary['no_mois'] += 1
            patient_type_summary['no_mois'].append(patient)
        else:
            amoi_flags = []
            for var in data[patient]['mois']:
                amoi_flags.append(amoi_check(var))

            mois = amoi_flags.count('moi')
            amois = amoi_flags.count('amoi')

            if amois > 1:
                type_summary['multi_amois'] += 1
                patient_type_summary['multi_amois'].append(patient)
            elif amois == 1:
                patient_type_summary['single_amoi'].append(patient)
                type_summary['one_amoi'] += 1

            if mois > 1:
                type_summary['multi_mois'] += 1
                patient_type_summary['multi_mois'].append(patient)
            elif mois == 1:
                type_summary['one_moi'] += 1
                patient_type_summary['single_moi'].append(patient)

    # pp(type_summary)
    # pp(patient_type_summary['multi_amois'])
    # XXX
    print('total patients with more than one aMOI: {}'.format(len(patient_type_summary['multi_amois'])))
    # for i,pt in enumerate(patient_type_summary['multi_amois']):
        # print('{},{}'.format(i+1,pt))
    return
                    
def amoi_check(var):
    if var[1] is None:
        return 'moi'
    else:
        return 'amoi'

def print_results(data,filename=None):
    # pp(data)
    # sys.exit()

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

def read_list(input_file):
    with open(input_file) as fh:
        return [x.rstrip('\n') for x in fh]

'''
patients_list = {
    'pt1' : '15454', # has KRAS hotspot
    'pt2' : '15596', # has ERBB2 CNV
    'pt3' : '10461', # has ALK Fusion.
    'pt4' : '10309', # has EGFR positional non-hs *and* EML4-ALK
    'pt5' : '13050', # has KIT positional non-hs
    'pt6' : '10123', # has PTEN Deleterious
    'pt7' : '15586', # has variants that have been rejected, including fusion isoforms.

}
'''

data = MatchData()
patients_list = []
try:
    input_file = sys.argv[1]
    patients_list = read_list(input_file)
except IndexError:
    print('No input file list passed. Retrieving data for all patients...')
    patients_list = data.get_patients_and_disease().keys()
    # pp(patients_list)

variant_results = {}

for pt in patients_list:
    # variant_results[patients_list[pt]] = get_data(data,psn=patients_list[pt])
    variant_results[pt] = get_data(data,psn=pt)
    # print('-'*50)

get_variant_report_metrics(variant_results)
print_results(variant_results)
