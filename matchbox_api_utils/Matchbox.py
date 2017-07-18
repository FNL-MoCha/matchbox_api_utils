import os
import sys
import requests
import json
import datetime
from collections import defaultdict
from pprint import pprint as pp

class Matchbox(object):
    def __init__(self,url,creds,load_raw=None,make_raw=None):
        '''MATCHBox API class. Used for calling to the MATCHBox API, loading data
        and, creating a basic data structure. Can load a raw MATCHBox API dataset
        JSON file, or create one.  Requires credentials, generally acquired from
        the config file generated upon package setup.

        Args:
            url (str): API URL for MATCHbox. Generally only using one at the moment,
                       but possible to add others later.
            creds (dict): Username and Password credentials obtained from the config
                          file generated upon setup. Can also just input a dict in 
                          the form of:
                              'username' : <username>,
                              'password' : <password>

            load_raw (str): Raw, unprocessed MATCHBox API JSON file (generally obtained
                            from the "make_raw" option. For dev purposes only, and useful
                            when we can not get a live connection to MATCHbox for some 
                            reason.
            make_raw (bool): Make a raw, unprocessed MATCHBox API JSON file.

        Returns:
            MATCHBox API dataset, used in the MatchboxData class below.
        '''
        self.url   = url
        self.creds = creds

        if load_raw:
            self.api_data = load_raw
        else:
            self.api_data = self.__api_call()

        # For debugging purposes, we may want to dump the whole raw dataset out 
        # to see what keys / vals are availble.  Only really for dev and debugging,
        # though.
        if make_raw: 
            sys.stdout.write('Making a raw MATCHBox API dump that can be loaded for development '
                'purposes rather than a live call to MATCHBox prior to parsing and filtering.\n')
            today = get_today()
            self.__raw_dump(self.api_data,'raw_mb_dump_'+today+'.json')
            sys.exit()
            return

    @staticmethod
    def __ascii_encode_dict(data):
        ascii_encode = lambda x: x.encode('ascii') if isinstance(x,bytes) else x
        return dict(map(ascii_encode,pair) for pair in data.items())

    def __api_call(self):
        # Call to API  to get data using cURL rather than requests or the like.  Works
        # a ton (!!) faster!
        curl_cmd = 'curl -u {}:{} -s {}'.format(
            self.creds['username'],self.creds['password'],self.url
        )
        request = os.popen(curl_cmd).read()
        return json.loads(request)
        
    @staticmethod
    def __raw_dump(data,filename=None):
        # Dump a raw, unprocessed matchbox for dev purposes.
        if not filename:
            filename = 'raw_mb_dump.json'
        with open(filename,'w') as fh:
            json.dump(data,fh)

    #XXX
    def gen_patients_list(self):
        '''
        Process the MATCHBox API JSON data into a much more concise and easily
        parsable dict of data. This dict will be the main dataset used for later
        data analysis and queries.

        Returns:
            patients (dict): Dict of parsed MATCHBox API data.

        '''
        patients = defaultdict(dict)

        for record in self.api_data:
            psn = record['patientSequenceNumber']       

            patients[psn]['source']      = record['patientTriggers'][0]['patientStatus']
            patients[psn]['psn']         = record['patientSequenceNumber']
            patients[psn]['concordance'] = record['concordance']
            patients[psn]['gender']      = record['gender']
            patients[psn]['id_field']    = record['id']
            patients[psn]['ethnicity']   = record['ethnicity']

            patients[psn]['dna_bam_path'] = '---'
            patients[psn]['ir_runid']     = '---'
            patients[psn]['rna_bam_path'] = '---'
            patients[psn]['vcf_name']     = '---'
            patients[psn]['vcf_path']     = '---'
            patients[psn]['mois']         = '---'
            patients[psn]['bsn']          = '---'
            patients[psn]['ihc']          = '---'
            patients[psn]['msn']          = '---'

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

            if record['latestBiopsy'] == None:
                patients[psn]['biopsy'] = 'No Biopsy'
            elif record['latestBiopsy']['failure']:
                patients[psn]['biopsy'] = 'Failed Biopsy'
            else:
                patients[psn]['biopsy'] = 'Pass'
                biopsy_data = record['latestBiopsy']

                patients[psn]['bsn'] = biopsy_data['biopsySequenceNumber']
                patients[psn]['ihc'] = self.__get_ihc_results(biopsy_data['assayMessagesWithResult'])

                # Skip outside assays as the data is not useful yet.
                if 'OUTSIDE_ASSAY' in patients[psn]['source']: 
                    patients[psn]['biopsy'] = 'Outside'
                    continue

                msns = []
                for message in biopsy_data['mdAndersonMessages']:
                    if message['message'] == 'NUCLEIC_ACID_SENDOUT':
                        msns.append(message['molecularSequenceNumber'])
                patients[psn]['msn'] = msns # Can have more than one in the case of re-extractions.

                # if 'OUTSIDE_ASSAY' not in patients[psn]['source']: # Skip outside assays as the data is not useful yet.
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
    def __get_ihc_results(ihc_data):
        ihc_results = {result['biomarker'].rstrip('s').lstrip('ICC') : result['result'] for result in ihc_data}
        # Won't always get RB IHC; depends on if we have other qualifying genomic event.  Fill in data anyway.
        if 'RB' not in ihc_results:
            ihc_results['RB'] = 'ND'
        return ihc_results

    def __proc_ngs_data(self,ngs_results):
        # Create and return a dict of variant call data that can be stored in the patient's obj
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
        # Fix the fusion driver / partner annotation since it is not always correct the way it's being parsed.  Also
        # add in a 'gene' field so that it's easier to aggregate data later on (the rest of the elements use 'gene').
        drivers = ['ABL1','AKT2','AKT3','ALK','AR','AXL','BRAF','BRCA1','BRCA2','CDKN2A','EGFR','ERBB2','ERBB4','ERG',
                   'ETV1','ETV1a','ETV1b','ETV4','ETV4a','ETV5','ETV5a','ETV5d','FGFR1','FGFR2','FGFR3','FGR','FLT3',
                   'JAK2','KRAS','MDM4','MET','MYB','MYBL1','NF1','NOTCH1','NOTCH4','NRG1','NTRK1','NTRK2','NTRK3',
                   'NUTM1','PDGFRA','PDGFRB','PIK3CA','PPARG','PRKACA','PRKACB','PTEN','RAD51B','RAF1','RB1','RELA',
                   'RET','ROS1','RSPO2','RSPO3','TERT']

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
    '''MatchboxData class'''
    def __init__(self,url,creds,patient=None,dumped_data=None,load_raw=None,make_raw=None):
        '''
           Generate a MATCHBox data object that can be parsed and queried 
           downstream with some methods. Entry points can be  either the live 
           MATCHBox instance or a JSON file containing:
               url         : MATCHBox URL to use; usually from creds in config file.
               creds       : MATCHBox credentials to use; usually from creds in 
                             config file.
               dumped_data : MATCHbox JSON file containing the whole dataset.
               raw_dump    : After reading MATCHBox in, dump out the whole thing 
                             as a raw JSON file.  This can be used as an entry 
                             point.
              make_raw     : Make a raw MATCHBox dataset.
        '''
        if patient:
            url = url + '?patientId=%s' % patient

        # Starting from processed MB JSON obj.
        if dumped_data:
            print('\n  ->  Starting from a processed MB JSON Obj')
            self.data = load_dumped_json(dumped_data)
            if patient:
                print('filtering on patient: %s\n' % patient)
                self.data = self.__filter_by_patient(self.data,patient)
        # Starting from raw MB JSON obj.
        elif load_raw:
            print('\n  ->  Starting from a raw MB JSON Obj')
            mb_raw_data = load_dumped_json(load_raw)
            self.matchbox = Matchbox(url,creds,load_raw=mb_raw_data)
            self.data = self.matchbox.gen_patients_list()
        # Starting from a live instance, and possibly making a raw dump
        else:
            print('\n  ->  Starting from a live MB instance')
            self.matchbox = Matchbox(url,creds,make_raw=make_raw)
            self.data = self.matchbox.gen_patients_list()

    @staticmethod
    def __filter_by_patient(json,patient):
        return json[patient]

    @staticmethod
    def __get_var_data_by_gene(data,gene_list):
        return [elem for elem in data if elem['gene'] in gene_list ]

    def __str__(self):
        return json.dumps(self.data,sort_keys=True,indent=4)

    def __getitem__(self,key):
        return self.data[key]

    def __iter__(self):
        return self.data.itervalues()

    def get_biopsy_numbers(self,has_biopsy=None,has_msn=None,has_seqdata=None):
        '''Return number of patients registered in MATCHBox with biopsy and sequencing
        information. Categories returned are total PSNs (excluding outside assay
        patients), total passed biopsies, total failed biopsies, total MSNs (
        not including multiple MSNs / patient) as a method of figuring out how
        many NAs were prepared, and total with sequencing data.
        '''
        count = {
            'psn'           : 0,
            'passed_biopsy' : 0,
            'failed_biopsy' : 0,
            'no_biopsy'     : 0,
            'msn'           : 0,
            'sequenced'     : 0,
            'outside'       : 0,
        }

        for p in self.data:
            count['psn'] += 1
            biopsy_flag = self.data[p]['biopsy']
            if biopsy_flag == 'No Biopsy':
                count['no_biopsy'] += 1
            elif biopsy_flag == 'Failed Biopsy':
                count['failed_biopsy'] += 1 
            elif biopsy_flag == 'Outside':
                count['outside'] += 1
            elif biopsy_flag == 'Pass':
                count['passed_biopsy'] += 1 
                if 'msn' in self.data[p] and self.data[p]['msn'] > 0:
                    count['msn'] += 1
                # TODO: verfiy that this is the best way to count "sequenced" samples
                if 'mois' in self.data[p]:
                    count['sequenced'] += 1
        return count

    def get_bsn(self,psn=None,msn=None):
        '''
        Retrieve a patient BSN from either an input PSN or MSN.
        Args:
            psn (str): A PSN number to query.  Must be a string.
            msn (str): A MSN number to query.  Must be a string.

        Returns:
            bsn (str): A BSN that maps to the PSN or MSN input.

        >>> print(get_bsn(psn='14420'))
        T-17-000550
        '''
        if psn and psn in self.data:
            return self.data[psn]['bsn']
        elif msn:
            for p in self.data:
                if self.data[p]['msn'] == msn:
                    return self.data[p]['bsn']
    
    def _matchbox_dump(self,filename=None):
        '''Dump a parsed MATCHBox dataset (not the raw total API dataset) as a 
        JSON file that can later be loaded in, rather than making an API call
        and reprocessing. Useful for quicker look ups as the API call can be 
        very, very slow with such a large DB.

        Args:
            filename (str): Filename to use for output. Default filename is:
            'mb_<date_generated>.json'
        '''
        formatted_date = get_today()
        if not filename:
            filename = 'mb_' + formatted_date + '.json'
        with open(filename, 'w') as outfile:
            json.dump(self.data,outfile,sort_keys=True,indent=4)

    def map_msn_psn(self,pt_id,id_type):
        '''
        Given a patient ID (either MSN or PSN) and a type val, output corresponding 
        MSN / PSN mapping. 

        .. note::
           If requesting an MSN as output, you will recieve an array of data since
           there can be more than one MSN / PSN.  When requesting a PSN from an 
           MSN, you will recieve only one value.

        Args:
            pt_id (str): Patient ID as either a MSN or PSN
            id_type (str): Type of ID input ('msn' | 'psn').

        Returns
            result (str): Corresponding MSN or PSN that maps to the input MSN or PSN.

        >>> print(map_msn_psn('14420','psn'))
        [u'MSN44180']

                 map_msn_psn(<id_string>, <'msn'|'psn'>)
        '''
        result = ''
        if id_type == 'psn':
            result = self.data[pt_id]['msn']
        elif id_type == 'msn':
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
        '''
        Return a summary of registered diseases and counts.
        '''
        total_patients = 0
        diseases = defaultdict(int)
        for psn in self.data:
            # Skip the registered but not yet biopsied patients.
            if self.data[psn]['medra_code'] == '-': continue
            total_patients += 1
            diseases[self.data[psn]['ctep_term']] += 1
        return total_patients, diseases

    def get_patients_and_disease(self,outside=None,query_psn=None):
        '''
        Return dict of PSN:Disease for valid biopsies.  Valid biopsies can 
        are defined as being only Passed and can not be Failed, No Biopsy or
        outside assay biopsies at this time.

        :param name: get_patients_and_disease
        :param str outside: Return outside assay results or filter them out.
        :param str query_psn: Optional PSN to filter data on.  
        :return: Dict of PSN : Disease mappings
        :rtype dict
        '''
        psn_list = []
        if query_psn:
            psn_list.append(query_psn)
        else:
            psn_list = self.data.keys()

        output_data = {}
        for psn in psn_list:
            try:
                biopsy = self.data[psn]['biopsy']
            except KeyError:
                sys.stderr.write("WARN: Can not find data for PSN%s in dataset! Skipping.\n" % psn)
                continue

            if self.data[psn]['bsn'] == '---':
                continue
            # Capture and remove "No Biopsy" and "Failed Biopsy" entries
            elif 'Biopsy' in biopsy: 
                continue
            elif biopsy == 'Outside' and not outside:
                continue
            output_data[psn] = self.data[psn]['ctep_term']
        return output_data

    def find_variant_frequency(self,query,query_patients=None):
        '''
        Based on an input query, generate a dict of patient data that can be 
        further filtered.  Input required is a dict query data in the form:
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
                # input_data = dict(self.data[patient]['mois'])
                input_data = self.data[patient]['mois']

                # We might want to just print out all MOIs for a patient rather than having to 
                # absolutely print out by MOIs.  Maybe there is a better way...write a new function?
                if len(query) < 1:
                    for var_type in input_data.keys():
                        for var in input_data[var_type]:
                            matches.append(var)
                else:
                    if 'snvs' in query and 'singleNucleotideVariants' in input_data:
                        matches = matches + self.__get_var_data_by_gene(
                            input_data['singleNucleotideVariants'],query['snvs']
                        )

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
        '''
        .. note: 
           THIS METHOD IS NOT YET IMPLEMENTED AND IS JUST A PLACEHOLDER.

        Get path of VCF file from MB Obj and return the VCF file from either the MB mirror or the source.
        '''
        return

def load_dumped_json(json_file):
    with open(json_file) as fh:
        return json.load(fh)

def get_today():
    return datetime.date.today().strftime('%m%d%y')

