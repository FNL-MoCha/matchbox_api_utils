# -*- coding: utf-8 -*-
# TODO:
#    - get_ihc_results() -> a method to print out patient IHC data based on gene name or psn.
import os
import sys
import json
import itertools
from collections import defaultdict
from pprint import pprint as pp

import utils
import matchbox_conf
from matchbox import Matchbox
from match_arms import TreatmentArms


class MatchData(object):

    """
    MatchboxData class

    Parsed MATCHBox Data from the API as collected from the Matchbox class above. This 
    class has methods to generate queries, further filtering, and heuristics on the 
    dataset.

    """

    def __init__(self,config_file=None,url=None,creds=None,patient=None,json_db='sys_default',load_raw=None,make_raw=None):
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
               json_db (file): MATCHbox processed JSON file containing the 
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
        self._json_db = json_db
        self._load_raw = load_raw
        self._config_file = config_file
        self.db_date = utils.get_today('long')

        if not self._url:
            self._url = utils.get_config_data(self._config_file,'url')

        if not self._creds:
            self._creds = utils.get_config_data(self._config_file,'creds')

        if self._patient:
            self._patient = str(self._patient)
            self._url += '?patientId=%s' % self._patient 

        # If json_db is 'sys_default', get json file from matchbox_conf.Config, which is from 
        # matchbox_api_util.__init__.mb_json_data.  Otherwise use the passed arg; if it's None, do
        # a live call below, and if it's a custom file, load that.
        if self._json_db == 'sys_default':
            self._json_db = utils.get_config_data(self._config_file,'mb_json_data')

        ta_data = utils.get_config_data(self._config_file,'ta_json_data')
        self.arm_data = TreatmentArms(json_db=ta_data)
            
        if make_raw:
            Matchbox(self._url,self._creds,make_raw='mb')
        elif self._load_raw:
            print('\n  ->  Starting from a raw MB JSON Obj')
            self.db_date, matchbox_data = utils.load_dumped_json(self._load_raw)
            self.data = self.gen_patients_list(matchbox_data,self._patient)
        elif self._json_db:
            print('\n  ->  Starting from a processed MB JSON Obj')
            self.db_date, self.data = utils.load_dumped_json(self._json_db)
            if self._patient:
                print('filtering on patient: %s\n' % self._patient)
                self.data = self.__filter_by_patient(self.data,self._patient)
        else:
            print('\n  ->  Starting from a live MB instance')
            matchbox_data = Matchbox(self._url,self._creds).api_data
            self.data = self.gen_patients_list(matchbox_data,self._patient)

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

    @staticmethod
    def __get_curr_arm(psn,assignment_logic_list,flag):
        # Bad(!) abuse of list comprehension to grab the "SELECTED" arm.  More reliable than any other message!
        # TODO: Just have to fix this and I think we're golden.
        # FIXME: I have found cases where a patient was given compassionate care, but there was no arm eligibility,
        #        though it seems there should have been. Not sure how to deal with these cases.

        try:
            return [x['treatmentArmId'] for x in assignment_logic_list if x['reasonCategory'] == flag][0]
        except:
            print('{}: can not get flag from logic list!'.format(psn))
            # pp(assignment_logic_list)
            return 'UNK'

    @staticmethod
    def __get_pt_hist(triggers,assignments,rejoin_triggers):
        # Read the trigger messages to determine the patient treatment and study arm history.

        # TODO:
        #    - If we get a rejoin request in the triggers message flow, we'll need to grab the indicated
        #      arm from the rejoin_triggers, and use taht instead of using ta logic from pending_approval
        #      signal to add arm to history.  Else, we're getting error trying to figure out what arm the
        #      patient was eligible for upon rejoin
        arms = []
        arm_hist = {}
        progressed = False
        tot_msgs = len(triggers)

        # If we only ever got to registration and not further (so there's only 1 message), let's bail out
        if tot_msgs == 1:
            return (triggers[0]['patientStatus'], triggers[0]['message'], {}, False)

        counter = 0
        for i,msg in enumerate(triggers):

            # XXX
            '''
            #DEBUG:
            print('{}  Current Message: ({}/{})  {}'.format('-'*25, i+1, tot_msgs, '-'*25))
            pp(msg)
            print('-'*76)
            '''

            # On a rare occassion, we get two of the same messages in a row.  Just skip the redundant message?
            if triggers[i-1]['patientStatus'] == msg['patientStatus']:
                continue
            
            if msg['patientStatus'] == 'REJOIN':
                counter += 1

            if msg['patientStatus'] == 'PENDING_APPROVAL':
                # XXX
                # pp(assignments[counter])
                curr_arm = MatchData.__get_curr_arm(msg['patientSequenceNumber'],assignments[counter]['patientAssignmentLogic'], 'SELECTED')
                arms.append(curr_arm)

                try:
                    arm_hist[curr_arm] = assignments[counter]['patientAssignmentMessage'][0]['status']
                except IndexError:
                    # We don't have a message because no actual assignment ever made (i.e. OFF_TRIAL before assignment)
                    arm_hist[curr_arm] = '.'
                # XXX
                # pp(arm_hist)
                # pp(arms)
                counter += 1

            if msg['patientStatus'].startswith("PROG"):
                progressed = True
                arm_hist[curr_arm] = 'FORMERLY_ON_ARM_PROGRESSED'

            elif msg['patientStatus'] == 'COMPASSIONATE_CARE':
                curr_arm = MatchData.__get_curr_arm(msg['patientSequenceNumber'],assignments[counter]['patientAssignmentLogic'], 'ARM_FULL')
                arm_hist[curr_arm] = 'COMPASSIONATE_CARE'

            # When we hit the last message, return what we've collected.
            if i+1 == tot_msgs:
                last_status = msg['patientStatus']
                last_msg = msg['message']

                if last_status.startswith('OFF_TRIAL') and arms:
                    if arm_hist[arms[-1]] == 'ON_TREATMENT_ARM':
                        arm_hist[arms[-1]] = 'FORMERLY_ON_ARM_OFF_TRIAL'
                    elif arm_hist[arms[-1]] == '.':
                        arm_hist[arms[-1]] = last_status

                return last_status,last_msg,arm_hist,progressed

    def gen_patients_list(self,matchbox_data,patient):
        """Process the MATCHBox API data.

        Process the MATCHBox API data (usually in JSON format from MongoDB) into 
        a much more concise and easily parsable dict of data. This dict will be 
        the main dataset used for later data analysis and queries and is the main 
        structure for the MatchboxData class below.

        Returns:
            patients (dict): Dict of parsed MATCHBox API data.

        """
        patients = defaultdict(dict)
        for record in matchbox_data:
            psn = record['patientSequenceNumber']       
            if patient and psn != patient:
                continue
            
            # Trim dict for now..too damned long and confusing!
            # TODO: can remove this once we've finished.
            # XXX
            for r in record['patientAssignments']:
                del r['treatmentArm']

            # XXX
            # pp(record.keys())
            # pp(record['patientAssignments'])

            # XXX
            # if any(x['patientStatus'] == 'COMPASSIONATE_CARE' for x in record['patientTriggers']):
                # print psn
            # continue


            # Get treatment arm history. 
            last_status,last_msg,arm_hist,progressed = self.__get_pt_hist(record['patientTriggers'],record['patientAssignments'],record['patientRejoinTriggers'])

            patients[psn]['current_status']    = last_status
            patients[psn]['last_msg']          = last_msg
            patients[psn]['ta_arms']           = arm_hist
            patients[psn]['progressed']        = progressed

            # XXX
            # pp(dict(patients))
            # sys.exit()


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
                    # continue

                msns = []
                for message in biopsy_data['mdAndersonMessages']:
                    if message['message'] == 'NUCLEIC_ACID_SENDOUT':
                        msns.append(message['molecularSequenceNumber'])
                patients[psn]['msn'] = msns # Can have more than one in the case of re-extractions.

                for result in biopsy_data['nextGenerationSequences']:
                    # Skip all Failed and Pending reports.
                    if result['status'] != 'CONFIRMED':  
                        continue 
                    # Now patients are getting an MSN directly from outside assay and put into data like normal, but 
                    # of course no IR stuff. So, we have to filter this.
                    try:
                        patients[psn]['ir_runid']     = result['ionReporterResults']['jobName']
                        patients[psn]['dna_bam_path'] = result['ionReporterResults']['dnaBamFilePath']
                        patients[psn]['rna_bam_path'] = result['ionReporterResults']['rnaBamFilePath']
                        patients[psn]['vcf_name']     = os.path.basename(result['ionReporterResults']['vcfFilePath'])
                        patients[psn]['vcf_path']     = result['ionReporterResults']['vcfFilePath']
                    except:
                        continue
                        # print('offending psn: %s' % psn)

                    # Get and add MOI data to patient record; might be from outside.
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
                if variant['confirmed']:
                    var_data = self.__gen_variant_dict(variant,var_type)
                    var_data.update({'amoi' : self.arm_data.map_amoi(var_data)})
                    variant_call_data[var_type].append(var_data)

        # Remap the driver / partner genes so that we know they're correct, and add a 'gene' field to use later on.
        if 'unifiedGeneFusions' in variant_call_data:
            variant_call_data['unifiedGeneFusions'] = self.__remap_fusion_genes(variant_call_data['unifiedGeneFusions'])

        return variant_call_data

    @staticmethod
    def __gen_variant_dict(vardata,vartype):
        # Based on input variant call data, return a dict of variant type and wanted fields
        meta_key = {
            'singleNucleotideVariants' : 'snvs_indels',
            'indels'                   : 'snvs_indels',
            'copyNumberVariants'       : 'cnvs',
            'unifiedGeneFusions'       : 'fusions',
        }

        include_fields = { 
                'snvs_indels' :  ['alleleFrequency', 'alternative', 'alternativeAlleleObservationCount', 'chromosome', 
                    'exon', 'flowAlternativeAlleleObservationCount', 'flowReferenceAlleleObservations', 'function', 
                    'gene', 'hgvs', 'identifier', 'oncominevariantclass', 'position', 'readDepth', 'reference', 
                    'referenceAlleleObservations', 'transcript', 'protein', 'confirmed'], 
                'cnvs'        : ['chromosome', 'gene', 'confidenceInterval5percent', 'confidenceInterval95percent', 
                    'copyNumber','confirmed'],
                'fusions'     : ['annotation', 'identifier', 'driverReadCount', 'driverGene', 'partnerGene','confirmed']
        }
        data = dict((key, vardata[key]) for key in include_fields[meta_key[vartype]])
        data['type'] = meta_key[vartype]
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
            elif gene1 in drivers and gene2 in drivers:
                driver = partner = 'NA'
            elif gene1 not in drivers and gene2 not in drivers:
                driver = partner = 'NA'

            try:
                fusion['driverGene'] = driver
                fusion['partnerGene'] = partner
            except:
                pp(fusion_data)
                sys.exit()
        return fusion_data

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
    
    def matchbox_dump(self,filename=None):
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
        # XXX
        # Need a warning here if we load the sys default JSON file *and* make a JSON file; they 
        # will be the same dataset!  Need to ensure a live query in that case.
        # formatted_date = datetime.date.today().strftime('%m%d%y')
        formatted_date = utils.get_today('short')
        if not filename:
            filename = 'mb_obj_' + formatted_date + '.json'
        # with open(filename, 'w') as outfile:
            # json.dump(self.data,outfile,sort_keys=True,indent=4)
        utils.make_json(filename,self.data)

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

    def get_patients_and_disease(self,psn=None,msn=None,bsn=None,outside=False,no_disease=False):
        """
        Return dict of PSN:Disease for valid biopsies.  Valid biopsies can 
        are defined as being only Passed and can not be Failed, No Biopsy or
        outside assay biopsies at this time.

        Args:
            psn (str): Optional PSN or comma separated list of PSNs on which to filter data.
            bsn (str): Optional BSN or comma separated list of BSNs on which to filter data.
            msn (str): Optional MSN or comma separated list of MSNs on which to filter data.
            outside (bool): Also include outside assay data. False by default.
            no_disease (bool): Return all data, even if there is no disease indicated for the 
                patient specimen. Default: False

        Returns:
            Dict of PSN : Disease mappings. If no match for input ID, returns None.

        Example: 
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
                biopsy = self.__search_for_value(key=id_type,val=i,retval='biopsy')

                # TODO: For now we're going to just remove patients based on these criteria. Eventually we may want to output them,
                #       but with the reason for filtering (i.e. output Failed Biopsy, No Biopsy, etc.).
                if outside is False and biopsy == 'Outside':
                    # output_data[i] = None
                    output_data[i] = biopsy
                    continue
                # Most Passed are OK, though there are a few cases where no fail flag applied yet.
                if no_disease is False and biopsy != 'Pass':
                    # output_data[i] = None
                    output_data[i] = biopsy
                    continue
                else:
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

    def get_variant_report(self,psn=None,msn=None):
        """
        Input a PSN or MSN and return a tab delimited set of variant data for the patient
        return var dict
        psn, msn, bsn
        disease

        """
        if psn:
            psn = str(psn) # allow flexibility if we do not explictly input string.
            if self.data[psn]['mois'] and self.data[psn]['mois'] != '---':
                try:
                    ret_data = dict(self.data[psn]['mois'])
                except:
                    print('error: cant make dict for patient: %s' % psn)
                    pp(self.data[psn]['mois'])
                    sys.exit()
                return dict(self.data[psn]['mois'])
        # TODO: Not sure I want to look up by MSN. Better to work wiht a PSN since there can be multiple MSNs in my dataset.
        #       Actually might be good to restructure this and get rid of multiple MSNs altogether.
        elif msn:
            msn = 'MSN' + str(msn).lstrip('MSN') 
            return dict(self.__search_for_value(key='msn',val=msn,retval='mois'))
        else:
            sys.stderr.write('ERROR: you must input either a PSN or MSN to this function!\n')
            # Bail out here instead of returning None?
            return None

    def get_patient_ta_status(self,psn=None):
        """
        Input a list of PSNs and return information about the treatment arm(s) to which they were
        assigned, if they were assigned to any arms. If no PSN list is passed to the function, return
        results for every PSN in the study.

        Args:
            psn (str):  PSN string to query.

        Returns:
            Dict of Arm IDs with last status.

        Example:
            >>> data.get_patient_ta_status(psn=10837)
            {u'EAY131-Z1A': u'ON_TREATMENT_ARM'}

            >>> data.get_patient_ta_status(psn=11889)
            {u'EAY131-IX1': u'FORMERLY_ON_ARM_OFF_TRIAL', u'EAY131-I': u'COMPASSIONATE_CARE'}

            >>> data.get_patient_ta_status(psn=10003)
            {}

        """
        results = {}
        if psn:
            psn = str(psn)
            if psn in self.data:
                return self.data[psn]['ta_arms']
            else:
                return None
        else:
            for p in self.data:
                results[p] = self.data[p]['ta_arms']
        return results 
    
    def get_seq_datafile(self,dtype=None,msn=None,psn=None):
        # TODO: Change this to get datafile and try to get BAM, VCF, etc. based on args.
        """
        .. note: 
           THIS METHOD IS NOT YET IMPLEMENTED AND IS JUST A PLACEHOLDER.

        Get path of VCF file from MB Obj and return the VCF file from either the MB mirror or the source.
        """
        valid_types = ('vcf','dna','rna','all')
        if dtype and dtype not in valid_types:
            sys.stderr.write('ERROR: %s is not a valid data type. You must choose from "vcf", "rna", or "dna".\n')
            sys.exit(1)

        if msn:
            msn = 'MSN' + str(msn).strip('MSN')
            psn = self.__search_for_value(key='msn',val=msn, retval='psn')
        elif psn:
            psn = str(psn).lstrip('PSN')

        print('psn: %s' % psn)
        # pp(dict(self.data[psn]))
        return

    def get_patients_by_arm(self,arm):
        results = []
        
        if arm not in self.arm_data.data:
            sys.stderr.write('ERROR: No such arm: {}!\n'.format(arm))
            return None

        for pt in self.data:
            if arm in self.data[pt]['ta_arms']:
                # print(','.join([pt,arm,self.data[pt]['ta_arms'][arm]]))
                results.append((pt,arm,self.data[pt]['ta_arms'][arm]))
        return results
