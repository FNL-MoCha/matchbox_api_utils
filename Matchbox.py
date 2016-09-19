#!/usr/bin/python
import sys
import os
import requests
import json
from collections import defaultdict
from pprint import pprint as pp

version = '0.4.0_091916'

class Matchbox(object):
    def __init__(self, url, creds):
        self.url = url
        self.creds = creds

    def __repr__(self):
        return "%s(%r)" % (self.__class__, self.__dict__)

    def api_call(self):
        request = requests.get(self.url,data = self.creds)
        try:
            request.raise_for_status()
        except requests.exceptions.HTTPError as error:
            sys.stderr.write('HTTP Error: {}'.format(error.message))
            sys.exit(1)
        json_data = request.json()
        return json_data

    def gen_patients_list(self):
        patients = defaultdict(dict)
        api_data = self.api_call()

        for record in api_data:
            psn                          = record['patientSequenceNumber']       
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
                    # TODO: Add other IHC assay data in here.
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
            'snvs_indels' :  ['alleleFrequency', 'alternative', 'alternativeAlleleObservationCount', 'chromosome', 
                'exon', 'flowAlternativeAlleleObservationCount', 'flowReferenceAlleleObservations', 'function', 
                'gene', 'hgvs', 'identifier', 'oncominevariantclass', 'position', 'readDepth', 'reference', 
                'referenceAlleleObservations', 'transcript'], 
            'cnvs'        : ['chromosome', 'gene', 'confidenceInterval5percent', 'confidenceInterval95percent', 
                'copyNumber'],
            'fusions'     : ['annotation', 'identifier', 'driverReadCount', 'driverGene', 'partnerGene']
    }
    return dict((key, vardata[key]) for key in include_fields[meta_key])

class MatchboxData(object):
    def __init__(self,url,creds):
        self.matchbox = Matchbox(url,creds)
        self.data = self.matchbox.gen_patients_list()

    def __repr__(self):
        return "%s(%r)" % (self.__class__, self.__dict__)

    def __getitem__(self,key):
        return self.data[key]

    def __iter__(self):
        return self.data.itervalues()

    def get_patients_and_disease(self,query_psn=None):
        '''Print out a list of patients and their disease.'''
        # print "Checking listing patient data..."
        output_data = []
        if query_psn:
            return (query_psn,self.data[query_psn]['ctep_term'])
        else:
            for psn in self.data:
                output_data.append((psn,self.data[psn]['ctep_term']))
        return output_data

    def find_variant_frequency(self,query):
        results = {}
        for patient in self.data:
            try:
                input_data = dict(self.data[patient]['mois'])
                if query['snvs']:
                    for gene in query['snvs'][gene]:
                        if input_data['singlenucleotidevariants']['gene'] == gene:
                            pp(input_data)
                # if query['indels']:
                    # for gene in query['indels'][gene]:
                        # if input_data['indels']['gene'] == gene:
                            # pp(input_data)
                # if query['cnvs']:
                    # for gene in query['cnvs'][gene]:
                        # if input_data['copyNumberVariants']['gene'] == gene:
                            # pp(input_data)
                # if query['fusions']:
                    # for gene in query['fusions'][gene]:
                        # if input_data['unifiedGeneFusions']['gene'] == gene:
                            # pp(input_data)
                    pass
            except KeyError:
                # No MOIs in report; skip
                continue

        return

    # def __gen_variant_entry()

if __name__=='__main__':
    main()
