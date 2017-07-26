# -*- coding: utf-8 -*-
import os
import sys
import json
import datetime
from collections import defaultdict
from pprint import pprint as pp

import matchbox_conf
from matchbox import Matchbox

class MatchData(object):

    """
    MatchboxData class

    Parsed MATCHBox Data from the API as collected from the Matchbox class above. This 
    class has methods to generate queries, further filtering, and heuristics on the 
    dataset.

    """

    def __init__(self,config_file=None,url=None,creds=None,patient=None,dumped_data='sys_default',load_raw=None,make_raw=None):
        """
        Generate a MATCHBox data object that can be parsed and queried downstream with some methods. 
        
        Can instantiate with either a config JSON file, which contains the url, username, and password information
        needed to access the resource, or by supplying the individual arguments to make the connection.  This class
        will call the Matchbox class in order to make the connection and deploy the data.

        Can do a live query to get data in real time, or load a MATCHBox JSON file derived from the 
        matchbox_json_dump.py script that is a part of the package. Since data in MATCHBox is relatively static 
        these days, it's preferred to use an existing JSON DB and only periodically update the DB with a 
        call to the aforementioned script.

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
               make_raw (bool):    Make a raw API JSON dataset for dev purposes only.

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

        if not self._creds:
            self._creds = self.__get_config_data('creds')

        if self._patient:
            self._url += '?patientId=%s' % patient

        # If dumped_data is 'sys_default', get json file from matchbox_conf.Config, which is from 
        # matchbox_api_util.__init__.mb_json_data.  Otherwise use the passed arg; if it's None, do
        # a live call below, and if it's a custom file, load that.
        if self._dumped_data == 'sys_default':
            self._dumped_data = self.__get_config_data('mb_json_data')

        if self._load_raw:
            # print('\n  ->  Starting from a raw MB JSON Obj')
            self.matchbox_data = self.__load_dumped_json(self._load_raw)
            self.data = self.gen_patients_list()
        elif self._dumped_data:
            # print('\n  ->  Starting from a processed MB JSON Obj')
            self.data = self.__load_dumped_json(self._dumped_data)
            if self._patient:
                print('filtering on patient: %s\n' % self._patient)
                self.data = self.__filter_by_patient(self.data,self._patient)
        else:
            # print('\n  ->  Starting from a live MB instance')
            self.matchbox_data = Matchbox(self._url,self._creds,make_raw=self._make_raw).api_data
            self.data = self.gen_patients_list()

    def __str__(self):
        return json.dumps(self.data,sort_keys=True,indent=4)

    def __getitem__(self,key):
        return self.data[key]

    def __iter__(self):
        return self.data.itervalues()

    @staticmethod
    def __filter_by_patient(json,patient):
        return json[patient]

    @staticmethod
    def __get_var_data_by_gene(data,gene_list):
        return [elem for elem in data if elem['gene'] in gene_list ]

    @staticmethod
    def __load_dumped_json(json_file):
        date_string = os.path.basename(json_file).lstrip('mb_obj_').rstrip('.json')
        try:
            formatted_date=datetime.datetime.strptime(date_string,'%m%d%y').strftime('%m/%d/%Y')
        except ValueError:
            creation_date = os.path.getctime(json_file)
            formatted_date=datetime.datetime.fromtimestamp(creation_date).strftime('%m/%d/%Y')
        sys.stderr.write('Loading MATCHBox JSON file created on: %s\n' % formatted_date)
        with open(json_file) as fh:
            return json.load(fh)

    def __get_config_data(self,item):
        config_data = matchbox_conf.Config(self._config_file)
        return config_data[item]

    def __get_patient_table(self,psn,next_key=None):
        # Output the filtered data table for a PSN so that we have a quick way to figure out 
        # key : value structure for the dataset.
        for key,val in self.data[str(psn)].items():
            if next_key:
                if key==next_key:
                    for k2,v2 in self.data[str(psn)][key].items():
                        return json.dumps(self.data[str(psn)][key],indent=4,sort_keys=True)
            else:
                return json.dumps(self.data[str(psn)],indent=4,sort_keys=True)

    def __search_for_value(self,key,val,retval):
        # Input a key and return a value or None
        # Example: __search_for_value(key=psn,val=14420,retval=msn)
        #   => search for PSN14420 in dataset and return MSN<whatever>
        # Example: __search_for_value(key=psn,val=14420,retval=bsn)
        #   => serach for PSN14420 in datasert and return BSN<whatever>

        val = str(val)
        for p in self.data:
            if key == 'msn' and val in self.data[p]['msn']:
                return self.data[p][retval]
            if key == 'psn' and p == val:
                return self.data[p][retval]
            if key == 'bsn' and self.data[p]['bsn'] == val:
                return self.data[p][retval]

        # If we made it here, then we didn't find a result.
        sys.stderr.write('No result for id %s: %s\n' % (key.upper(),val))
        return None

    def gen_patients_list(self):
        """Process the MATCHBox API data.

        Process the MATCHBox API data (usually in JSON format from MongoDB) into 
        a much more concise and easily parsable dict of data. This dict will be 
        the main dataset used for later data analysis and queries and is the main 
        structure for the MatchboxData class below.

        Returns:
            patients (dict): Dict of parsed MATCHBox API data.

        """
        # TODO: What if we parallelized this?
        patients = defaultdict(dict)

        for record in self.matchbox_data:
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
        # Get and load IHC results from dataset.
        ihc_results = {result['biomarker'].rstrip('s').lstrip('ICC') : result['result'] for result in ihc_data}
        # Won't always get RB IHC; depends on if we have other qualifying genomic event.  Fill in data anyway.
        if 'RB' not in ihc_results:
            ihc_results['RB'] = 'ND'
        return ihc_results

    def __proc_ngs_data(self,ngs_results):
       # Create and return a dict of variant call data that can be stored in the patient's obj.
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
        # Based on input variant call data, return a dict of variant type and wanted fields
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

    def get_biopsy_summary(self,category=None):
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
            catetory (str): biopsy category to return. Valid categories are 'psn','passed_biopsy',
                            'failed_biopsy','no_biopsy','msn','sequenced','outside'.

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
        """
        Dump a parsed MATCHBox dataset.
        
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
        formatted_date = datetime.date.today().strftime('%m%d%y')
        if not filename:
            filename = 'mb_obj_' + formatted_date + '.json'
        with open(filename, 'w') as outfile:
            json.dump(self.data,outfile,sort_keys=True,indent=4)

    def map_msn_psn(self,pt_id,id_type):
        """
        Map a MSN to PSN or PSN to MSN

        Note: This function is going to be deprecated in favor of individual calls.

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
            # result = self.__return_key_by_val(pt_id)

        if not result:
            print('No result found for id %s' % pt_id)
            return None
        return result

    def get_psn(self,msn=None,bsn=None):
        """
        Retrieve a patient PSN from either an input MSN or BSN.

        Args:
            msn (str): A MSN number to query. 
            bsn (str): A BSN number to query.

        Returns:
            psn (str): A PSN that maps to the MSN or BSN input.

        >>> print(get_psn(bsn='T-17-000550'))
        PSN14420

        """

        psn = ''
        if msn:
            if not str(msn).startswith('MSN'):
                msn = 'MSN'+str(msn)
            psn = self.__search_for_value(key='msn',val=msn,retval='psn')
        elif bsn:
            psn = self.__search_for_value(key='bsn',val=bsn,retval='psn')
        else:
            sys.stderr.write('ERROR: No MSN or BSN entered!\n')
            return None
        
        if psn:
            return "PSN"+psn
        else:
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
        result = []
        if psn:
            result = self.__search_for_value(key='psn',val=psn,retval='msn')
        elif bsn:
            result = self.__search_for_value(key='bsn',val=bsn,retval='msn')
        else:
            sys.stderr.write('ERROR: No PSN or BSN entered!\n')
            return None

        if result:
            return ','.join(result)
        else:
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

    def get_disease_summary(self,disease=None):
        """
        Return a summary of registered diseases and counts. Despite a MEDRA Code and other bits
        of disease related data, we'll rely on output from CTEP Term value only.

        Args:
            query_disease (str): Disease or comma separated list of diseases to filter on.

        Returns:
            Dictionary of disease(s) and counts.

        """
        diseases = defaultdict(int)
        for psn in self.data:
            # Skip the registered but not yet biopsied patients.
            if self.data[psn]['medra_code'] == '-': 
                continue

            diseases[self.data[psn]['ctep_term']] += 1

        if disease:
            if disease in diseases:
                return {disease : diseases[disease]}
            else:
                sys.stderr.write('Disease "%s" was not found in the database.\n' % disease)
                return None
        else:
            return dict(diseases)

    def get_patients_and_disease(self,psn=None,msn=None,bsn=None,outside=False):
        """
        Return dict of PSN:Disease for valid biopsies.  Valid biopsies can 
        are defined as being only Passed and can not be Failed, No Biopsy or
        outside assay biopsies at this time.

        Args:
            psn (str): Optional PSN or comma separated list of PSNs on which to filter data.
            bsn (str): Optional BSN or comma separated list of BSNs on which to filter data.
            msn (str): Optional MSN or comma separated list of MSNs on which to filter data.
            outside (bool) : Also include outside assay data. False by default.

        Returns:
            Dict of PSN : Disease mappings. If no match for input ID, returns None.

        >>> print(get_disease(psn='11352'))
        'Serous endometrial adenocarcinoma'

        """
        # Don't want to allow for mixed query types. So, number of None args must be > 2, 
        # or else user entered more than one arg type and that's not good.
        count_none = sum((x is None for x in (psn,msn,bsn)))
        if count_none < 2:
            sys.stderr.write('Error: Mixed query types detected. Please only use one type of query '
                'ID in this function.\n')
            sys.exit(1)

        # Prepare an ID list dict if one is provided. Need some special mapping and whatnot before we can pass it.
        id_list = {}
        if psn:
            id_list['psn'] = [x.lstrip('PSN') for x in str(psn).split(',')]
        elif msn:
            id_list['msn'] = ['MSN'+x.lstrip('MSN') for x in str(msn).split(',')]
        elif bsn:
            id_list['bsn'] = bsn.split(',')
        else:
            id_list['psn'] = self.data.keys()

        output_data = {}
        for id_type in id_list:
            for i in id_list[id_type]:
                output_data[i] = self.__search_for_value(key=id_type,val=i,retval='ctep_term')
        return output_data

    def find_variant_frequency(self,query,query_patients=None):
        """
        Find and return variant hit rates.

        Based on an input query in the form of a variant_type : gene dict, where the gene value
        can be a list of genes, output a list of patients that had hits in those gene with some 
        disease and variant information. 

        Args:
            query (dict): Dictionary of variant_type: gene mappings where:
                -  variant type is one or more of 'snvs','indels','fusions','cnvs'
                -  gene is a list of genes to query.
            query_patients (list): List of patients for which we want to obtain data. 

        Returns:
            Will return a dict of matching data with disease and MOI information
        
        Example:
        >>> query={'snvs' : ['BRAF','MTOR'], 'indels' : ['BRAF', 'MTOR']}
        find_variant_frequency(query)


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
        # TODO: Change this to get datafile and try to get BAM, VCF, etc. based on args.
        """
        .. note: 
           THIS METHOD IS NOT YET IMPLEMENTED AND IS JUST A PLACEHOLDER.

        Get path of VCF file from MB Obj and return the VCF file from either the MB mirror or the source.
        """
        return
