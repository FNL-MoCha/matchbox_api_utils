#!/usr/bin/python
import sys
import os
import requests
import json
from collections import defaultdict
from pprint import pprint as pp

version = '0.5.1_092116'

class Matchbox(object):
    def __init__(self, url, creds):
        self.url = url
        self.creds = creds

    def __repr__(self):
        return "%s(%r)" % (self.__class__, self.__dict__)

    def _ascii_encode_dict(self,data):
        '''From SO9590382, a method to encode the JSON obj into ascii instead of unicode.'''
        ascii_encode = lambda x: x.encode('ascii') if isinstance(x,unicode) else x
        return dict(map(ascii_encode,pair) for pair in data.items())

    def api_call(self):
        request = requests.get(self.url,data = self.creds)
        try:
            request.raise_for_status()
        except requests.exceptions.HTTPError as error:
            sys.stderr.write('HTTP Error: {}'.format(error.message))
            sys.exit(1)
        json_data = request.json(object_hook=self._ascii_encode_dict)
        # json_data = request.json()
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
                        patients[psn]['mois']         = self.__proc_ngs_data(variant_report)
        return patients


    def __proc_ngs_data(self,ngs_results):
        '''Create and return a dict of variant call data that can be stored in the patient's obj'''
        variant_call_data = defaultdict(list)
        variant_list = ['singleNucleotideVariants', 'indels', 'copyNumberVariants', 'unifiedGeneFusions']

        for var_type in variant_list:
            for variant in ngs_results[var_type]:
                variant_call_data[var_type].append(self.__gen_variant_dict(variant,var_type))

        # Remap the driver / partner genes so that we know they're correct, and add a 'gene' field to use later on.
        if 'unifiedGeneFusions' in variant_call_data:
            variant_call_data['unifiedGeneFusions'] = self.__remap_fusion_genes(variant_call_data['unifiedGeneFusions'])
        return variant_call_data

    def __gen_variant_dict(self,vardata,vartype):
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

    def __remap_fusion_genes(self,fusion_data):
        '''
        Fix the fusion driver / partner annotation since it is not always correct the way it's being parsed.  Also
        add in a 'gene' field so that it's easier to aggregate data later on (the rest of the elements use 'gene').
        '''
        drivers = ['ABL1','AKT3','ALK','AXL','BRAF','EGFR','ERBB2','ERG','ETV1','ETV1a','ETV1b','ETV4','ETV4a',
                   'ETV5','ETV5a','ETV5d','FGFR1','FGFR2','FGFR3','MET','NTRK1','NTRK2','NTRK3','PDGFRA','PPARG',
                   'RAF1','RET','ROS1']
        driver = ''
        partner = ''
        for fusion in fusion_data:
            gene1 = fusion['driverGene']
            gene2 = fusion['partnerGene']

            # handle intragenic fusions
            if gene1 in ['MET','EGFR']:
                driver = partner = gene1

            # figure out others.
            if gene1 in drivers:
                driver = gene1
                partner = gene2
            elif gene2 in drivers:
                driver = gene2
                partner = gene1
            else:
                partner = [gene1,gene2]
                driver = 'UNKNOWN'
            fusion['gene'] = fusion['driverGene'] = driver
            fusion['partnerGene'] = partner
        return fusion_data

class MatchboxData(object):
    # TODO: fix this!
    def __init__(self,url,creds,dumped_data=None):
        if dumped_data:
            self.data = self.__load_dumped_json(dumped_data)
        else:
            self.matchbox = Matchbox(url,creds)
            self.data = self.matchbox.gen_patients_list()

    # def __init__(self,json_data):
        # self.data = self.__load_dumped_json(json_data)

    def __load_dumped_json(self,json_file):
        with open(json_file) as fh:
            return json.load(fh)

    def __repr__(self):
        return "%s(%r)" % (self.__class__, self.__dict__)

    def __getitem__(self,key):
        return self.data[key]

    def __iter__(self):
        return self.data.itervalues()

    def _matchbox_dump(self):
        '''Dump the whole DB as a JSON Obj'''
        with open('mb.json', 'w') as outfile:
            json.dump(self.data,outfile)

    def __get_var_data_by_gene(data,gene_list):
        return [elem for elem in data if elem['gene'] in gene_list ]

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
        print "query is:"
        pp(query)
        for patient in self.data:
            # print "testing patient: {}".format(patient)
            if patient == '10896':
                pp(self.data[patient])

            matches = []
            # if 'mois' in self.data[patient]:
                # input_data = dict(self.data[patient]['mois'])

                # if 'snvs' in query and 'singleNucleotideVariants' in input_data:
                    # matches = matches + self.__get_var_data_by_gene(input_data['singleNucleotideVariants'],query['snvs'])

                # if 'indels' in query and 'indels' in input_data:
                    # matches = matches + self.__get_var_data_by_gene(input_data['indels'],query['indels'])

                # if 'cnvs' in query and 'copyNumberVariants' in input_data:
                    # matches = matches + self.__get_var_data_by_gene(input_data['copyNumberVariants'],query['cnvs'])

                # if 'fusions' in query and 'unifiedGeneFusions' in input_data:
                    # matches = matches + self.__get_var_data_by_gene(input_data['unifiedGeneFusions'],query['fusions'])


            if matches:
                print '-'*50
                print "PSN{}:".format(patient)
                pp(matches)
                print '-'*50
                # results[patient] = {
                    # 'psn'     : self.data[patient]['psn'],
                    # 'disease' : self.data[patient]['ctep_term'],
                    # 'msn'     : self.data[patient]['msn'],
                    # 'mois'    : matches
                # }

        # pp(results)
        return


def dump_the_box(url,creds):
    '''
    Dump out the whole DB as a JSON file that I can import.
    '''
    print "Dumping matchbox into mb.json for easier code testing...",
    match_data = MatchboxData(url,creds)
    match_data._matchbox_dump()
    print "Done!"
    sys.exit()

if __name__=='__main__':
    url = 'https://matchbox.nci.nih.gov/match/common/rs/getPatients'
    creds = {
        'username' : 'trametinib',
        'password' : 'COSM478K601E',
    }

    ###################################################################
    # XXX: if we need to dump it!
    # dump_the_box(url,creds)
    # sys.exit()
    ##################################################################

    # match_data = MatchboxData(url,creds,'mb.json')
    match_data = MatchboxData(url,creds)

    # query_list = {'fusions' : ['MET'] }
    query_list = {'cnvs' : ['AR'] }
    # query_list = {
        # 'snvs' : ['KRAS', 'SMARCB1', 'FOO'],
        # 'indels' : ['CTNNB1', 'NOTCH1'],
    # }
    # query_list = {
        # 'indels'   : ['BRCA1', 'BRCA2', 'ATM'],
        # 'snvs'   : ['IDH1'],
        # 'cnvs'   : ['CCNE1', 'EGFR']
    # }
    match_data.find_variant_frequency(query_list)
