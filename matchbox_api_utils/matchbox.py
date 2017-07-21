# -*- coding: utf-8 -*-
# TODO:
#    - get_disease(psn,bsn,msn): Return disease type.
import os
import sys
import requests
import json
import datetime
from collections import defaultdict
from pprint import pprint as pp

import matchbox_conf

class Matchbox(object):

    """
    MATCHBox API Connector Class.

    Basic connector class to make a call to the API and load the raw data. From
    here we can filter and pass data to MatchboxData class, or we can dump the 
    raw API to a file in order to develop and test.

    """

    def __init__(self,url,creds,load_raw=None,make_raw=None):
        """MATCHBox API class. 
        
        Used for calling to the MATCHBox API, loading data and, creating a basic 
        data structure. Can load a raw MATCHBox API dataset JSON file, or create 
        one.  Requires credentials, generally acquired from the config file generated 
        upon package setup.

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

        """
        self.url   = url
        self.creds = creds

        if load_raw:
            self.api_data = load_raw
        else:
            self.api_data = self.__api_call()

        # For debugging purposes, we may want to dump the whole raw dataset out 
        # to see what keys / vals are availble.  
        if make_raw: 
            sys.stdout.write('Making a raw MATCHBox API dump that can be loaded for development '
                'purposes rather than a live call to MATCHBox prior to parsing and filtering.\n')
            today = get_today()
            self.__raw_dump(self.api_data,'raw_mb_dump_'+today+'.json')
            sys.exit()
            return

    @staticmethod
    def __ascii_encode_dict(data):
        """Encode return JSON as ASCII rather than unicode."""
        ascii_encode = lambda x: x.encode('ascii') if isinstance(x,bytes) else x
        return dict(map(ascii_encode,pair) for pair in data.items())

    def __api_call(self):
        """Call to API to retrienve data. Using cURL rather than requests since requests
        takes bloody forever!
        """
        curl_cmd = 'curl -u {}:{} -s {}'.format(
            self.creds['username'],self.creds['password'],self.url
        )
        request = os.popen(curl_cmd).read()
        return json.loads(request)
        
    @staticmethod
    def __raw_dump(data,filename=None):
        """Dump a raw, unprocessed matchbox for dev purposes."""
        if not filename:
            filename = 'raw_mb_dump.json'
        with open(filename,'w') as fh:
            json.dump(data,fh)

    def gen_patients_list(self):
        """Process the MATCHBox API data.

        Process the MATCHBox API data (usually in JSON format from MongoDB) into 
        a much more concise and easily parsable dict of data. This dict will be 
        the main dataset used for later data analysis and queries and is the main 
        structure for the MatchboxData class below.

        Returns:
            patients (dict): Dict of parsed MATCHBox API data.

        """
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

                for result in biopsy_data['nextGenerationSequences']:
                    # Skip all Failed and Pending reports.
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
        """Get and load IHC results from dataset."""
        ihc_results = {result['biomarker'].rstrip('s').lstrip('ICC') : result['result'] for result in ihc_data}
        # Won't always get RB IHC; depends on if we have other qualifying genomic event.  Fill in data anyway.
        if 'RB' not in ihc_results:
            ihc_results['RB'] = 'ND'
        return ihc_results

    def __proc_ngs_data(self,ngs_results):
        """Create and return a dict of variant call data that can be stored in the patient's obj."""
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
        """Based on input variant call data, return a dict of variant type and wanted fields"""
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
        """
        Fix the fusion driver / partner annotation since it is not always correct the way it's being parsed.  Also
        add in a 'gene' field so that it's easier to aggregate data later on (the rest of the elements use 'gene').

        """
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

    """MatchboxData class

    Parsed MATCHBox Data from the API as collected from the Matchbox class above. This 
    class has methods to generate queries, further filtering, and heuristics on the 
    dataset.

    """

    def __init__(self,config_file=None,url=None,creds=None,patient=None,dumped_data='sys_default',load_raw=None,make_raw=None):
        """Generate a MATCHBox data object that can be parsed and queried 
        downstream with some methods. 
        
         Can instantiate with either a config JSON file (generated from the 
         package configuration) or by loading required args below. Can do a 
         live query, or load a MATCHBox JSON file (derived from 
         matchbox_json_dump.py in the package).

         Args:
               config_file (file): Custom config file to use if not using system 
                                   default.
               url (str):          MATCHBox API URL to use.
               creds (dict):       MATCHBox credentials to use. Needs to be in the 
                                   form of:

                            {'username':<username>,'password':<password>}

               patient (str):      Limit data to a specific PSN.
               dumped_data (file): MATCHbox processed JSON file containing the 
                                   whole dataset. This is usually generated from 
                                   'matchbox_json_dump.py'. The default value is 
                                   'sys_default' which loads the default package 
                                   data. If you wish you get a live call, set this
                                   variable to "None".
               load_raw (file):    Load a raw API dataset rather than making a fresh
                                   call to the API. This is intended for dev purpose
                                   only and will be disabled.
               make_raw (bool):    Make a raw API JSON dataset for dev purposes only
                                   .

          URL and credentials can be manually applied to API or (preferred!) 
          obtained from the default config file in $HOME/.mb_utils/config.json. 
          The Config class in matchbox_conf will load up the data.

        """
        self._url = url
        self._creds = creds
        self._patient = patient
        self._dumped_data = dumped_data
        self._load_raw = load_raw
        self._make_raw = make_raw
        self._config_file = config_file

        if not self._url:
            self._url = self.__get_config_data('url')

        if self._patient:
            self._url += '?patientId=%s' % patient

        if not self._creds:
            self._creds = self.__get_config_data('creds')

        if self._dumped_data == 'sys_default':
            self._dumped_data = self.__get_config_data('mb_json_data')

        if self._dumped_data:
            print('\n  ->  Starting from a processed MB JSON Obj')
            self.data = load_dumped_json(self._dumped_data)
            if self._patient:
                print('filtering on patient: %s\n' % self._patient)
                self.data = self.__filter_by_patient(self.data,self._patient)
        # Starting from raw MB JSON obj.
        elif self._load_raw:
            print('\n  ->  Starting from a raw MB JSON Obj')
            mb_raw_data = load_dumped_json(self._load_raw)
            self.matchbox = Matchbox(self._url,self._creds,load_raw=mb_raw_data)
            self.data = self.matchbox.gen_patients_list()
        # Starting from a live instance, and possibly making a raw dump
        else:
            print('\n  ->  Starting from a live MB instance')
            self.matchbox = Matchbox(self._url,self._creds,make_raw=self._make_raw)
            self.data = self.matchbox.gen_patients_list()

    def __str__(self):
        return json.dumps(self.data,sort_keys=True,indent=4)

    def __getitem__(self,key):
        return self.data[key]

    def __iter__(self):
        return self.data.itervalues()
        # Starting from processed MB JSON obj.

    @staticmethod
    def __filter_by_patient(json,patient):
        return json[patient]

    @staticmethod
    def __get_var_data_by_gene(data,gene_list):
        return [elem for elem in data if elem['gene'] in gene_list ]

    def __get_config_data(self,item):
        config_data = matchbox_conf.Config(self._config_file)
        return config_data[item]


    def get_biopsy_numbers(self,category=None):
        """Return dict of patients registered in MATCHBox with biopsy and sequencing
        information. 
        
        Categories returned are total PSNs issued (including outside 
        assay patients), total passed biopsies, total failed biopsies (per MDACC 
        message), total MSNs (only counting latest MSN if more than one issued to
        a biopsy due to a failure) as a method of figuring out how many NAs were 
        prepared, and total with sequencing data.

        Can filter output based on any one criteria by leveraging the "category" 
        variable

        Args:
            catetory (str): biopsy category to return

        Returns:
            dict: whole set of category:count or single category:count data.

        """
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
                # From above, everything will get a default '---' val, but only CONFIRMED
                # results actually get data.
                if self.data[p]['mois'] != '---':
                    count['sequenced'] += 1
        if category and category in count:
            return {category:count[category]}
        else:
            return count
    
    def _matchbox_dump(self,filename=None):
        """Dump a parsed MATCHBox dataset.
        
        Call to the API and make a JSON file that can later be loaded in, rather 
        than making an API call and reprocessing. Useful for quicker look ups as 
        the API call can be very, very slow with such a large DB.

        .. note:: This is a different dataset than the raw dump.

        Args:
            filename (str): Filename to use for output. Default filename is:
            'mb_obj_<date_generated>.json'

        Returns:
            file: MATCHBox API JSON file.

        """
        formatted_date = get_today()
        if not filename:
            filename = 'mb_obj_' + formatted_date + '.json'
        with open(filename, 'w') as outfile:
            json.dump(self.data,outfile,sort_keys=True,indent=4)

    def map_msn_psn(self,pt_id,id_type):
        """Map a MSN to PSN or PSN to MSN

        NOTE: This function is deprecated in favor of individual get_bsn, get_psn,
        get_msn class of functions. 
        Given a patient ID (either MSN or PSN) and a type val, output corresponding 
        MSN / PSN mapping. 

        Note:
           If requesting an MSN as output, you will recieve an array of data since
           there can be more than one MSN / PSN.  When requesting a PSN from an 
           MSN, you will recieve only one value.

        Args:
            pt_id (str): Patient ID as either a MSN or PSN
            id_type (str): Type of ID input ('msn' | 'psn').

        Returns:
            result (str): Corresponding MSN or PSN that maps to the input MSN or PSN.

        >>> print(map_msn_psn('14420','psn'))
        [u'MSN44180']

        """
        result = ''
        if id_type == 'psn':
            result = self.data[pt_id]['msn']
        elif id_type == 'msn':
            for p in self.data:
                if pt_id in self.data[p]['msn']:
                    result = p
            result = self.__return_key_by_val(pt_id)

        if not result:
            print('No result found for id %s' % pt_id)
            return None
        return result

    def __return_key_by_val(self):
        """
        TODO: remove this function '''

        """
        msn_id = 'MSN'+msn_id
        for p in self.data:
            if msn_id in self.data[p]['msn']:
                return p

    def __search_for_value(self,key,val,retval):
        """
        Input a key and return a value or None
        Ex __search_for_value(key=psn,val=14420,retval=msn)
          => search for PSN14420 in dataset and return MSN<whatever>

        Ex __search_for_value(key=psn,val=14420,retval=bsn)
          => serach for PSN14420 in datasert and return BSN<whatever>

        """
        result = ''
        val = str(val)
        for p in self.data:
            if key == 'msn' and val in self.data[p]['msn']:
                if retval == 'psn':
                    result = p
                elif retval == 'bsn':
                    result = self.data[p]['bsn']
            if key == 'psn' and p == val:
                if retval == 'msn':
                    result = ','.join(self.data[p]['msn'])
                elif retval == 'bsn':
                    result = self.data[p]['bsn']
            if key == 'bsn' and self.data[p]['bsn'] == val:
                if retval == 'psn':
                    result = p
                elif retval == 'msn':
                    result = ','.join(self.data[p]['msn'])
        if result:
            return result
        else:
            sys.stderr.write('No result for id %s: %s\n' % (key.upper(),val))
            return None

    def get_psn(self,msn=None,bsn=None):
        """
        Retrieve a patient PSN from either an input MSN or BSN.

        Args:
            msn (str): A MSN number to query. 
            bsn (str): A BSN number to query.

        Returns:
            psn (str): A PSN that maps to the MSN or BSN input.

        >>> print(get_psn(bsn='T-17-000550'))
        14420

        """

        if msn:
            if not msn.startswith('MSN'):
                msn = 'MSN'+msn
            return self.__search_for_value(key='msn',val=msn,retval='psn')
        elif bsn:
            return self.__search_for_value(key='bsn',val=bsn,retval='psn')
        else:
            sys.stderr.write('ERROR: No MSN or BSN entered!\n')
            return None

    def get_msn(self,psn=None,bsn=None):
        """
        Retrieve a patient BSN from either an input PSN or MSN.

        Args:
            psn (str): A MSN number to query. 
            bsn (str): A BSN number to query.

        Returns:
            msn (str): A string of comma separated MSNs that map to an input BSN or PSN.

        >>> print(get_msn(bsn='T-17-000550'))
        MSN44180

        """
        if psn:
            return self.__search_for_value(key='psn',val=psn,retval='msn')
        elif bsn:
            return self.__search_for_value(key='bsn',val=bsn,retval='msn')
        else:
            sys.stderr.write('ERROR: No PSN or BSN entered!\n')
            return None

    def get_bsn(self,psn=None,msn=None):
        """
        Retrieve a patient BSN from either an input PSN or MSN.

        Args:
            psn (str): A PSN number to query. 
            msn (str): A MSN number to query.

        Returns:
            bsn (str): A BSN that maps to the PSN or MSN input.

        >>> print(get_bsn(psn='14420'))
        T-17-000550

        """
        if msn:
            if not msn.startswith('MSN'):
                msn = 'MSN'+msn
            return self.__search_for_value(key='msn',val=msn,retval='bsn')
        elif psn:
            return self.__search_for_value(key='psn',val=psn,retval='bsn')
        else:
            sys.stderr.write('ERROR: No PSN or MSN entered!\n')
            return None

    def get_disease_summary(self):
        """Return a summary of registered diseases and counts."""
        total_patients = 0
        diseases = defaultdict(int)
        for psn in self.data:
            # Skip the registered but not yet biopsied patients.
            if self.data[psn]['medra_code'] == '-': continue
            total_patients += 1
            diseases[self.data[psn]['ctep_term']] += 1
        return total_patients, diseases

    def get_patients_and_disease(self,outside=None,query_psn=None):
        """
        #TODO: strip PSN string from input. 
        Return dict of PSN:Disease for valid biopsies.  Valid biopsies can 
        are defined as being only Passed and can not be Failed, No Biopsy or
        outside assay biopsies at this time.

        .. py:function:: get_patients_and_disease([outside=None],[query_psn=None])

        Return PSN and Disease for valid biopsies.

        :param name: get_patients_and_disease
        :param str outside: Return outside assay results or filter them out.
        :param str query_psn: Optional PSN to filter data on.  
        :return: Dict of PSN : Disease mappings
        :rtype: dict
        
        """
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
        """
        TODO: Update docs
              Add aMOI designator (also arm?)
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
        """
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
        """
        .. note: 
           THIS METHOD IS NOT YET IMPLEMENTED AND IS JUST A PLACEHOLDER.

        Get path of VCF file from MB Obj and return the VCF file from either the MB mirror or the source.
        """
        return

def load_dumped_json(json_file):
    date_string = os.path.basename(json_file).lstrip('mb_obj_').rstrip('.json')
    try:
        formatted_date=datetime.datetime.strptime(date_string,'%M%d%y').strftime('%M/%d/%Y')
    except ValueError:
        creation_date = os.path.getctime(json_file)
        formatted_date=datetime.datetime.fromtimestamp(creation_date).strftime('%M/%d/%Y')
    sys.stderr.write('Loading MATCHBox JSON file created on: %s\n' % formatted_date)
    with open(json_file) as fh:
        return json.load(fh)

def get_today():
    return datetime.date.today().strftime('%m%d%y')

