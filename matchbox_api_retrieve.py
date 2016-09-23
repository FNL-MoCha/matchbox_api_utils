#!/usr/bin/python
#
# Python implementation of the ir_apl_retrieve.pl script that doesn't seem to be working due to
# some bugs in the LWP modules.  Re-wrote this to accomodate that as well as deal with SSL 
# issues that seem to be plaguing the perl version of the script across platforms.
#
# 4/1/2015 - D Sims
###############################################################################################
import sys
import os
import argparse
import requests
import time
import json
from pprint import pprint
from collections import defaultdict

version = '0.8.0_030216'
DEBUG = True

def get_args():
    parser = argparse.ArgumentParser(
        formatter_class = lambda prog: argparse.HelpFormatter(prog, max_help_position=100, width=150),
        description='''
        NCI-MATCHBox API retrieval utility. 
        ''',
        version = '%(prog)s  - ' + version,
        )
    parser.add_argument('-b','--batch', metavar='<batch_file>', 
            help='Batch file of experiment names to retrieve')
    parser.add_argument('analysis_id', nargs='?', help='Analysis ID to retrieve if not using a batchfile')
    cli_args = parser.parse_args()

    return cli_args

def _jprint(data):
    print json.dumps(data, indent=4, sort_keys=True)

def convert_time(millis):
    return time.strftime("%a, %d %b %Y %H:%M:%S", time.localtime(millis/1000.0))

def retrieve_json(url):
    '''Request data dump and return JSON result from MATCHBox API'''
    creds = {
        'username' : 'trametinib',
        'password' : 'COSM478K601E',
    }
    request = requests.get(url, data = creds)
    try:
        request.raise_for_status()
    except requests.exceptions.HTTPError as error:
        sys.stderr.write('HTTP Error: {}'.format(error.message))
        sys.exit(1)
    json_data = request.json()
    return json_data
    
def gen_patients_list(api_table):
    '''Load (very much!!!) abbreviated data table into a dict that we can query for data or summarize later'''
    patients = defaultdict(dict)

    for record in api_table:
        psn         = record['patientSequenceNumber']       

        # TODO: Remove this filter when ready
        # if psn != '10327': continue # This is example of a run with 2 biopsies, 1 MSN, and 1 sequencing result => SNVs and Indels only
        # if psn != '10385': continue # This is example of a run with ineligable aMOI => SNVs and Indels only
        # if psn != '10612': continue # This is example of a run with eligable aMOI   => SNVs and CNVs only
        # if psn != '10010': continue # This is example of a run with 1 biopsy, 1 MSN, and 2 sequencing runs.
        # if psn != '10607': continue # This is example of a run with 1 biopsy, 1 MSN, and 1 sequencing run.
        # if psn != '10528': continue # This is an example of a run with 1 biopsy, 1 MSN, 2 seq runs   => SNVs, Indels, adn Fusions.
        # if not psn.startswith('101'): continue  # get batch of these to play with.

        patients[psn]['psn']         = record['patientSequenceNumber']
        patients[psn]['concordance'] = record['concordance']
        patients[psn]['gender']      = record['gender']
        patients[psn]['id_field']    = record['id']
        patients[psn]['ethnicity']   = record['ethnicity']

        try:
            race = record['races'][0]
        except IndexError:
            race = '-'
        patients[psn]['race'] = race

        try:
            ctep_term   = record['diseases'][0]['ctepTerm']
        except IndexError:
            ctep_term = '-'
        patients[psn]['ctep_term'] = ctep_term

        try:
            medra_code  = record['diseases'][0]['medraCode']
        except IndexError:
            medra_code = '-'
        patients[psn]['medra_code'] = medra_code

        biopsies = record['biopsies']
        for biopsy in biopsies:
            if str(biopsy['failure']) == 'True': continue # Skip over failed biopsies.
            else:
                patients[psn]['bsn']              = biopsy['biopsySequenceNumber']
                # patients[psn]['pten']             = biopsy['ptenIhcResult']
                
                for result in biopsy['nextGenerationSequences']:
                    # For now just take only confirmed results.
                    if result['status'] != 'CONFIRMED': 
                        continue 

                    patients[psn]['dna_bam_path'] = result['ionReporterResults']['dnaBamFilePath']
                    patients[psn]['ir_runid']     = result['ionReporterResults']['jobName']
                    patients[psn]['msn']          = result['ionReporterResults']['molecularSequenceNumber']
                    patients[psn]['rna_bam_path'] = result['ionReporterResults']['rnaBamFilePath']
                    patients[psn]['vcf_name']     = os.path.basename(result['ionReporterResults']['vcfFilePath'])
                    patients[psn]['vcf_path']     = result['ionReporterResults']['vcfFilePath']

                    # Get and add MOI data to patient record
                    variant_report                = result['ionReporterResults']['variantReport']
                    patients[psn]['mois']         = proc_ngs_data(variant_report)
    return patients

def proc_ngs_data(ngs_results):
    '''Create and return a dict of variant call data that can be stored in the patient's obj'''
    variant_call_data = defaultdict(list)
    variant_list = ['singleNucleotideVariants', 'indels', 'copyNumberVariants', 'unifiedGeneFusions']

    for var_type in variant_list:
        for variant in ngs_results[var_type]:
            variant_call_data[var_type].append(gen_variant_dict(variant,var_type))
    return variant_call_data

def gen_variant_dict(vardata,vartype):
    if vartype == 'singleNucleotideVariants' or vartype == 'indels':
        meta_key = 'snvs_indels'
    elif vartype == 'copyNumberVariants':
        meta_key = 'cnvs'
    elif vartype == 'unifiedGeneFusions':
        meta_key = 'fusions'

    include_fields = { 
            'snvs_indels' :  ['alleleFrequency', 'alternative', 'alternativeAlleleObservationCount', 'chromosome', 'exon', 'flowAlternativeAlleleObservationCount',
                              'flowReferenceAlleleObservations', 'function', 'gene', 'hgvs', 'identifier', 'oncominevariantclass', 'position', 'readDepth', 'reference', 
                              'referenceAlleleObservations', 'transcript'], 
            'cnvs'        : ['chromosome', 'gene', 'confidenceInterval5percent', 'confidenceInterval95percent', 'copyNumber'],
            'fusions'     : ['annotation', 'identifier', 'driverReadCount', 'driverGene', 'partnerGene']
    }
    return dict((key, vardata[key]) for key in include_fields[meta_key])

def main():
    cli_args = get_args()

    server_url= 'https://matchbox.nci.nih.gov/match/common/rs/'  # Keep separate so that we have flexibility to query multiple servers (FFP server?)
    api_url = server_url + 'getPatients'

    # Get whole dataset as big JSON that we can munge
    json_data = retrieve_json(api_url)
    _jprint(json_data)
    sys.exit()

    # Get very short poignant dataset from API for downstream queries
    patients = gen_patients_list(json_data)

    # TODO: Seems that the data structure and query all work well.  Need to make some query functions for the data now.  Would love to figure out how to make a class object for this with some real methods!
    # Simple summary table output
    desired_fields = ('psn', 'race', 'gender', 'ctep_term', 'medra_code', 'pten', 'bsn', 'msn', 'vcf_name')
    template = '{:9}{:35}{:9}{:55}{:12}{:10}{:15}{:11}{}'

    # desired_fields = ('psn', 'race', 'gender', 'ctep_term', 'medra_code', 'pten', 'bsn', 'msn', 'vcf_path')
    # template = '{:9}{:35}{:9}{:55}{:12}{:10}{:15}{:11}{}'
    # print template.format(*desired_fields)

    for patient in sorted(patients):
        results = []
        try:
            msn = patients[patient]['msn']
            for elem in desired_fields:
                results.append(patients[patient][elem])
        except KeyError: 
            continue
        print template.format(*results)

if __name__ == '__main__':
    main()
