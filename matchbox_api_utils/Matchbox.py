import os
import sys
import requests
import json
import datetime
from collections import defaultdict
from pprint import pprint as pp

version = '0.9.14_060817'

class Matchbox(object):
    def __init__(self,url,creds):
        self.url = url
        self.creds = creds

    @staticmethod
    def __ascii_encode_dict(data):
        '''From SO9590382, a method to encode the JSON obj into ascii instead of unicode.'''
        ascii_encode = lambda x: x.encode('ascii') if isinstance(x,bytes) else x
        return dict(map(ascii_encode,pair) for pair in data.items())

    def api_call(self):
        print('requesting data from: %s' % self.url)
        request = requests.get(self.url,data=self.creds)
        try:
            request.raise_for_status()
        except requests.exceptions.HTTPError as error:
            sys.stderr.write('HTTP Error: {}'.format(error.message))
            sys.exit(1)
        json_data = request.json(object_hook=self.__ascii_encode_dict)
        return json_data

    def api_call2(self):
        '''Use os and system curl to get a much (much!!!!) quicker connection with MB'''
        request = os.popen("curl -s " + self.url).read()
        return json.loads(request)
        
    @staticmethod
    def __raw_dump(data,filename=None):
        '''Dump a raw, unprocessed matchbox for dev purposes'''
        if not filename:
            filename = 'raw_mb_dump.json'
        with open(filename,'w') as fh:
            json.dump(data,fh)

    def gen_patients_list(self,dump=None):
        patients = defaultdict(dict)
        # api_data = self.api_call()
        # use this system curl call rather than mess with requests library and huge (!!) overhead!
        api_data = self.api_call2()

        # For debugging purposes, we may want to dump the whole raw dataset out to see what keys / vals are availble.  
        # Only really for dev and debugging, though.
        today = datetime.date.today().strftime('%m%d%y')
        if dump: 
            self.__raw_dump(api_data,'raw_mb_dump_'+today+'.json')
            return

        for record in api_data:
            # Can have registered patient who have not yet be biopsied.  Let's pass over those for now, but maybe 
            # pick back up later if we want to be able to get a track record of registered vs tested.
            if len(record['biopsies']) < 1 or record['latestBiopsy'] == 'None':
                continue
            psn                          = record['patientSequenceNumber']       
            patients[psn]['source']      = record['patientTriggers'][0]['patientStatus']
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

            biopsy_data = record['latestBiopsy']

            if biopsy_data['failure'] == 'false': 
                continue 

            patients[psn]['bsn'] = biopsy_data['biopsySequenceNumber']
            patients[psn]['ihc'] = self.__get_ihc_results(biopsy_data['assayMessagesWithResult'])

            '''----------------------------------  OUTSIDE ASSSAY FLAWs HERE  ---------------------------'''
            #XXX
            msns = []
            for message in biopsy_data['mdAndersonMessages']:
                if message['message'] == 'NUCLEIC_ACID_SENDOUT':
                    msns.append(message['molecularSequenceNumber'])
            patients[psn]['msn'] = msns # Can have more than one in the case of re-extractions.

            # for e in patients[psn]:
                # print('{}: {}'.format(e,patients[psn][e]))
            # sys.exit()

            if 'OUTSIDE_ASSAY' in patients[psn]['source']:
                # TODO: Finish this later.  For now skip so that we can analyze patients....
                # outside_results =  self.__proc_outside_assay_entry(biopsy_data)

                patients[psn]['dna_bam_path'] = '---'
                patients[psn]['ir_runid']     = '---'
                patients[psn]['rna_bam_path'] = '---'
                patients[psn]['vcf_name']     = '---'
                patients[psn]['vcf_path']     = '---'
                patients[psn]['mois']         = '---'
            else:
                for result in biopsy_data['nextGenerationSequences']:
                    if result['status'] != 'CONFIRMED':  
                        continue 
                    patients[psn]['dna_bam_path'] = result['ionReporterResults']['dnaBamFilePath']
                    patients[psn]['ir_runid']     = result['ionReporterResults']['jobName']
                    patients[psn]['rna_bam_path'] = result['ionReporterResults']['rnaBamFilePath']
                    patients[psn]['vcf_name']     = os.path.basename(result['ionReporterResults']['vcfFilePath'])
                    patients[psn]['vcf_path']     = result['ionReporterResults']['vcfFilePath']

                    # Get and add MOI data to patient record
                    variant_report                = result['ionReporterResults']['variantReport']
                    patients[psn]['mois']         = self.__proc_ngs_data(variant_report)
        # pp(dict(patients))
        # sys.exit()
        return patients

    @staticmethod
    def __proc_outside_assay_entry(data):
        '''proc the biopsy data block for outside assays and return the following:
            msn: <site_mb_hash_val>
            dna_bam_path: '---'
            ir_runid:     '---'
            rna_bam_path: '---'
            vcf_name:     '---'
            vcf_path:     '---'
            mois:         ?? Can process through self.__proc_ngs_data() ??
        '''
        print("")
        for i in data:
            print(i)

        sys.exit()

    @staticmethod
    def __get_ihc_results(ihc_data):
        ihc_results = {result['biomarker'].rstrip('s').lstrip('ICC') : result['result'] for result in ihc_data}
        # Won't always get RB IHC; depends on if we have other qualifying genomic event.  Fill in data anyway.
        if 'RB' not in ihc_results:
            ihc_results['RB'] = 'ND'
        return ihc_results

    def __proc_ngs_data(self,ngs_results):
        '''Create and return a dict of variant call data that can be stored in the patient's obj'''
        variant_call_data = defaultdict(list)
        variant_list = ['singleNucleotideVariants', 'indels', 'copyNumberVariants', 'unifiedGeneFusions']

        for var_type in variant_list:
            for variant in ngs_results[var_type]:
                if variant['confirmed'] == 'false':
                    continue
                variant_call_data[var_type].append(self.__gen_variant_dict(variant,var_type))

        # Remap the driver / partner genes so that we know they're correct, and add a 'gene' field to use later on.
        if 'unifiedGeneFusions' in variant_call_data:
            variant_call_data['unifiedGeneFusions'] = self.__remap_fusion_genes(variant_call_data['unifiedGeneFusions'])

        # XXX
        # getting the proper obj out now.  We just need to figure out how to make sure we're filtering correctly.
        # print('got here')
        # pp(variant_call_data)
        # sys.exit()

        return variant_call_data

    @staticmethod
    def __gen_variant_dict(vardata,vartype):
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
                    'referenceAlleleObservations', 'transcript', 'protein', 'confirmed'], 
                'cnvs'        : ['chromosome', 'gene', 'confidenceInterval5percent', 'confidenceInterval95percent', 
                    'copyNumber','confirmed'],
                'fusions'     : ['annotation', 'identifier', 'driverReadCount', 'driverGene', 'partnerGene','confirmed']
        }
        data = dict((key, vardata[key]) for key in include_fields[meta_key])
        data['type'] = meta_key
        return data

    @staticmethod
    def __remap_fusion_genes(fusion_data):
        '''
        Fix the fusion driver / partner annotation since it is not always correct the way it's being parsed.  Also
        add in a 'gene' field so that it's easier to aggregate data later on (the rest of the elements use 'gene').
        '''
        drivers = ['ABL1','AKT3','ALK','AXL','BRAF','EGFR','ERBB2','ERG','ETV1','ETV1a','ETV1b','ETV4','ETV4a',
                   'ETV5','ETV5a','ETV5d','FGFR1','FGFR2','FGFR3','MET','NTRK1','NTRK2','NTRK3','PDGFRA','PPARG',
                   'RAF1','RET','ROS1']
        for fusion in fusion_data:
            gene1 = fusion['driverGene']
            gene2 = fusion['partnerGene']

            # handle intragenic fusions
            if gene1 in ['MET','EGFR']:
                driver = partner = gene1

            # figure out others.
            if gene1 in drivers:
                (driver,partner) = (gene1,gene2)
            elif gene2 in drivers:
                (driver,partner) = (gene2,gene1)
            else:
                partner = [gene1,gene2]
                driver = 'UNKNOWN'
            fusion['gene'] = fusion['driverGene'] = driver
            fusion['partnerGene'] = partner
        return fusion_data


class MatchboxData(object):
    def __init__(self,url,creds,dumped_data=None,patient=None,raw_dump=None):
        if dumped_data:
            self.data = self.__load_dumped_json(dumped_data)
            if patient:
                self.data = self.__filter_by_patient(self.data,patient)
        else:
            if patient:
                url = url + '?patientId=%s' % patient
            self.matchbox = Matchbox(url,creds)
            self.data = self.matchbox.gen_patients_list(raw_dump)

    @staticmethod
    def __filter_by_patient(json,patient):
        return json[patient]

    @staticmethod
    def __load_dumped_json(json_file):
        with open(json_file) as fh:
            return json.load(fh)

    @staticmethod
    def __get_var_data_by_gene(data,gene_list):
        return [elem for elem in data if elem['gene'] in gene_list ]

    def __str__(self):
        return json.dumps(self.data)

    def __getitem__(self,key):
        return self.data[key]

    def __iter__(self):
        return self.data.itervalues()

    def _matchbox_dump(self,filename=None):
        '''Dump the whole DB as a JSON Obj'''
        # with open('mb.json', 'w') as outfile:
        today = datetime.date.today()
        formatted_date = today.strftime('%m%d%y')
        if not filename:
            filename = 'mb_' + formatted_date + '.json'
        with open(filename, 'w') as outfile:
            json.dump(self.data,outfile,sort_keys=True,indent=4)

    def map_msn_psn(self,pt_id,id_type):
        '''Given a patient ID (either MSN or PSN) and a type val, output corresponding MSN / PSN mapping. 
                 map_msn_psn(<id_string>,'msn' | 'psn')
        '''
        result = ''
        if id_type == 'psn':
            result = self.data[pt_id]['msn']
        elif id_type == 'msn':
            print('getting psn for msn %s' % pt_id)
            result = self.__return_key_by_val(pt_id)

        if not result:
            print('No result found for id %s' % pt_id)
            return None
        return result

    def __return_key_by_val(self,msn_id):
        msn_id = 'MSN'+msn_id
        for p in self.data:
            if msn_id in self.data[p]['msn']:
                return p

    def get_disease_summary(self):
        total_patients = 0
        diseases = defaultdict(int)
        for psn in self.data:
            # Skip the registered but not yet biopsied patients.
            if self.data[psn]['medra_code'] == '-': continue
            total_patients += 1
            diseases[self.data[psn]['ctep_term']] += 1
        return total_patients, diseases

    def __get_patient_disease(self,psn):
        return (psn,self.data[psn]['ctep_term'])

    def get_patients_and_disease(self,query_psn=None):
        '''
        Print out a list of patients and their disease. Can either input a single psn to query, or can input
        a list of PSNs.
        '''
        output_data = []
        psn_list = []
        if query_psn:
            psn_list.append(query_psn)
        else:
            psn_list = self.data.keys()

        for psn in psn_list:
            output_data.append(self.__get_patient_disease(psn))
        return output_data

    def find_variant_frequency(self,query,query_patients=None):
        '''
        Based on an input query, generate a dict of patient data that can be further filtered.  Input required is a dict
        query data in the form:
            {'snvs' : ['GENE1','GENE2',etc.],
             'indels' : ['GENE1', 'GENE2', etc.],
                     .
                     .
                     .
            }
            and so on
        Will return a dict of matching data with disease and MOI information
        '''
        results = {} 
        count = 0
        for patient in self.data:
            if query_patients and patient not in query_patients:
                continue
            if 'msn' in self.data[patient]: 
                count += 1
            matches = []
            if 'mois' in self.data[patient]:
                input_data = dict(self.data[patient]['mois'])
                if 'snvs' in query and 'singleNucleotideVariants' in input_data:
                    matches = matches + self.__get_var_data_by_gene(input_data['singleNucleotideVariants'],query['snvs'])

                if 'indels' in query and 'indels' in input_data:
                    matches = matches + self.__get_var_data_by_gene(input_data['indels'],query['indels'])

                if 'cnvs' in query and 'copyNumberVariants' in input_data:
                    matches = matches + self.__get_var_data_by_gene(input_data['copyNumberVariants'],query['cnvs'])

                if 'fusions' in query and 'unifiedGeneFusions' in input_data:
                    # input_data['unifiedGeneFusions'] is a list
                    filtered_fusions = []
                    for fusion in input_data['unifiedGeneFusions']:
                        if fusion['identifier'].endswith('Novel') or fusion['identifier'].endswith('Non-Targeted'): 
                            continue
                        else:
                            filtered_fusions.append(fusion)
                    matches = matches + self.__get_var_data_by_gene(filtered_fusions,query['fusions'])

            if matches:
                results[patient] = {
                    'psn'     : self.data[patient]['psn'],
                    'disease' : self.data[patient]['ctep_term'],
                    'msn'     : self.data[patient]['msn'],
                    'mois'    : matches
                }
        return results,count

    def get_vcf(self,msn=None):
        '''Get path of VCF file from MB Obj and return the VCF file from either the MB mirror or the source.'''
        return
