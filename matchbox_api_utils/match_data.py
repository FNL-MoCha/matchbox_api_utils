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
        # Get variant report data if the gene is in the input gene list.  But, only output the variant level
        # details, and filter out the VAF, coverage, etc. so that we can get unqiue lists later.  If we wanted
        # to get sequence specific details, we'll run a variant report instead.
        wanted = ('alternative', 'amoi', 'chromosome', 'exon', 'confirmed', 'function', 'gene', 'hgvs',
            'identifier', 'oncominevariantclass', 'position', 'protein', 'reference', 'transcript', 'type')
        # return [elem for elem in data if elem['gene'] in gene_list ]
        return [{i:elem[i] for i in wanted} for elem in data if elem['gene'] in gene_list]
        


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
        # XXX: This is now deprecated.  Remove once we finishe recoding for this method.
        # Input a key and return a value or None
        # Example: __search_for_value(key=psn,val=14420,retval=msn)
        #   => search for PSN14420 in dataset and return MSN<whatever>
        # Example: __search_for_value(key=psn,val=14420,retval=bsn)
        #   => search for PSN14420 in datasert and return BSN<whatever>

        print('self.__search_for_value(): This method is longer valid!')
        sys.exit(213)
        val = str(val)
        record = {}

        # First find the record
        if key == 'psn' and val in self.data:
            record = self.data[val]
        else:
            for p in self.data:
                if key == 'msn' and val in self.data[p]['all_msns']:
                    record = self.data[p]
                elif key == 'bsn' and val in self.data[p]['all_biopsies']:
                    record = self.data[p]

        # Now figure out if we need a toplevel return value or we have to traverse the record.
        if retval in record.keys():
            return record[retval]
        elif retval == 'biopsy_status':
            return record['biopsies'][val]['biopsy_status']

        """
                return self.data[p][retval]

            if key == 'psn' and p == val:
                return self.data[p][retval]

            if key == 'bsn' and self.data[p]['bsn'] == val:
                return self.data[p][retval]

        """
        # If we made it here, then we didn't find a result.
        sys.stderr.write('No result for id %s: %s\n' % (key.upper(),val))
        return None

    @staticmethod
    def __get_curr_arm(psn,assignment_logic_list,flag):
        # Figure out the arm to which the patient was assinged based on the flag message found in the TA Logic flow.
        try:
            return [x['treatmentArmId'] for x in assignment_logic_list if x['reasonCategory'] == flag][0]
        except:
            # There are exactly 4 cases (as of 9/19/2017) where the patient has PTEN IHC-, but was not assigned Arm P
            # directly for some reason that I can't discern. Instead patient was put on compassionate care for Arm P,
            # and although I can't comptutationally derive that since there is no obvious messsage, I don't want to lose
            # those results. So, I'm going to manually enter data for those 4 until I can figure out how to get this 
            # in better.
            if psn in ('13629','13899','14007','14057'):
                return 'EAY131-P'
            else:
                print('{}: can not get flag from logic list!'.format(psn))
                return 'UNK'

    @staticmethod
    def __get_pt_hist(triggers,assignments,rejoin_triggers):
        # Read the trigger messages to determine the patient treatment and study arm history.
        # TODO: Still have an issue here!  If there was a progressino re-biopsy (like in the case of PSN11583), we
        #       do not have the correct variant report necessarily.  This is causing an issue and will cause a mis-match
        #       issue through out.  I think I need to try to get on top of the multi-biopsies and multi-MSNs a bit better.
        arms = []
        arm_hist = {}
        progressed = False
        tot_msgs = len(triggers)

        # If we only ever got to registration and not further (so there's only 1 message), let's bail out
        if tot_msgs == 1:
            return (triggers[0]['patientStatus'], triggers[0]['message'], {}, False)

        counter = 0
        for i,msg in enumerate(triggers):
            # On a rare occassion, we get two of the same messages in a row.  Just skip the redundant message?
            if triggers[i-1]['patientStatus'] == msg['patientStatus']:
                continue
            
            if msg['patientStatus'] == 'REJOIN':
                counter += 1

            if msg['patientStatus'] == 'PENDING_APPROVAL':
                curr_arm = MatchData.__get_curr_arm(msg['patientSequenceNumber'],assignments[counter]['patientAssignmentLogic'], 'SELECTED')
                arms.append(curr_arm)

                try:
                    arm_hist[curr_arm] = assignments[counter]['patientAssignmentMessage'][0]['status']
                except IndexError:
                    # We don't have a message because no actual assignment ever made (i.e. OFF_TRIAL before assignment)
                    arm_hist[curr_arm] = '.'
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
                if arms:
                    if last_status.startswith('OFF_TRIAL'):
                        if arm_hist[arms[-1]] == 'ON_TREATMENT_ARM':
                            arm_hist[arms[-1]] = 'FORMERLY_ON_ARM_OFF_TRIAL'

                    if arm_hist[arms[-1]] == '.':
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
            
            patients[psn]['psn']         = psn
            patients[psn]['gender']      = record['gender']
            patients[psn]['ethnicity']   = record['ethnicity']
            patients[psn]['source']      = record['patientTriggers'][0]['patientStatus']
            patients[psn]['concordance'] = record['concordance']

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
            patients[psn]['all_msns']     = []
            patients[psn]['all_biopsies'] = []

            # Get treatment arm history. 
            # TODO: Fix this.
            last_status,last_msg,arm_hist,progressed = self.__get_pt_hist(record['patientTriggers'],record['patientAssignments'],record['patientRejoinTriggers'])

            patients[psn]['current_trial_status']    = last_status
            patients[psn]['last_msg']                = last_msg
            patients[psn]['ta_arms']                 = arm_hist
            patients[psn]['progressed']              = progressed


            patients[psn]['biopsies'] = {}
            
            if not record['biopsies']:
                patients[psn]['biopsies'] = 'No_Biopsy'
            else:
                for biopsy in record['biopsies']:
                    bsn = biopsy['biopsySequenceNumber']
                    patients[psn]['all_biopsies'].append(bsn)
                
                    biopsy_data = defaultdict(dict)
                    biopsy_data[bsn]['ihc']      = '---'
                    biopsy_data[bsn]['biopsy_source']   = '---'

                    # TODO remove this extra layer.  not needed.
                    biopsy_data[bsn]['ngs_data'] = {}

                    if biopsy['failure']:
                        biopsy_data[bsn]['biopsy_status'] = 'Failed_Biopsy'

                    else:
                        biopsy_data[bsn]['biopsy_status'] = 'Pass'
                        biopsy_data[bsn]['ihc'] = self.__get_ihc_results(biopsy['assayMessagesWithResult'])

                        # Define biopsy type as Initial, Progression, or Outside. 
                        if biopsy['associatedPatientStatus'] == 'REGISTRATION_OUTSIDE_ASSAY':
                            if bsn.startswith('T-'):
                                biopsy_data[bsn]['biopsy_source'] = 'Outside_Confirmation'
                            else:
                                biopsy_data[bsn]['biopsy_source'] = 'Outside'
                        elif biopsy['associatedPatientStatus'] == 'PROGRESSION_REBIOPSY':
                            biopsy_data[bsn]['biopsy_source'] = 'Progression'
                        elif biopsy['associatedPatientStatus'] == 'REGISTRATION':
                            biopsy_data[bsn]['biopsy_source'] = 'Initial'

                        # Make MSNs Struct
                        # msns = defaultdict(dict)
                        for result in biopsy['nextGenerationSequences']:
                            # Skip all Failed and Pending reports.
                            if result['status'] != 'CONFIRMED':  
                                continue 
                            msn = result['ionReporterResults']['molecularSequenceNumber']
                            patients[psn]['all_msns'].append(msn)

                            # Now patients are getting an MSN directly from outside assay and put into data like normal,
                            # but of course no IR stuff. So, we have to filter this.
                            try:
                                biopsy_data[bsn]['ngs_data']['msn']          = msn
                                biopsy_data[bsn]['ngs_data']['ir_runid']     = result['ionReporterResults']['jobName']
                                biopsy_data[bsn]['ngs_data']['dna_bam_path'] = result['ionReporterResults']['dnaBamFilePath']
                                biopsy_data[bsn]['ngs_data']['rna_bam_path'] = result['ionReporterResults']['rnaBamFilePath']
                                biopsy_data[bsn]['ngs_data']['vcf_path']     = result['ionReporterResults']['vcfFilePath']
                                # msns[msn]['ir_runid']     = result['ionReporterResults']['jobName']
                                # msns[msn]['dna_bam_path'] = result['ionReporterResults']['dnaBamFilePath']
                                # msns[msn]['rna_bam_path'] = result['ionReporterResults']['rnaBamFilePath']
                                # msns[msn]['vcf_path']     = result['ionReporterResults']['vcfFilePath']
                            except:
                                continue
                                # print('offending psn: %s' % psn)

                            # Get and add MOI data to patient record; might be from outside.
                            variant_report     = result['ionReporterResults']['variantReport']
                            # msns[msn]['mois']  = dict(self.__proc_ngs_data(variant_report))
                            biopsy_data[bsn]['ngs_data']['mois']  = dict(self.__proc_ngs_data(variant_report))

                            # TODO: remove this layer.
                            # biopsy_data[bsn]['ngs_data'].update(dict(msns))
                            # biopsy_data[bsn][msn] = dict(msns)

                    patients[psn]['biopsies'].update(dict(biopsy_data))
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

    def get_patient_meta(self,psn,val=None):
        """
        Return data for a patient based on a metadata field name. Sometimes we may want to just get 
        a quick bit of data or field for a patient record rather than a whole analysis, and this can
        be a convenient way to just check a component rather than writing a method to get each and 
        every bit out. If no metaval is entered, will return the whole patient dict.

        Args:
            psn (str):  PSN of patient for which we want to receive data.
            val (str):  Optional metaval of data we want. If no entered, will
                return the entire patient record.

        Returns:
            Either return dict of data if a metaval entered, or whole patient record. Returns 'None' if
            no data for a particular record and raises and error if the metaval is not valid for the dataset.

        """
        if val:
            try:
                return {val:self.data[str(psn)][val]}
            except KeyError:
                sys.stderr.write("ERROR: '%s' is not a valid metavalue for this dataset.\n" % val)
                return None
        else:
            return dict(self.data[str(psn)])

    def get_biopsy_summary(self,category=None):
        # TODO: Fix this. Not getting correct counts and fields.  Also, need to add number sequenced to this output.
        """
        Return dict of patients registered in MATCHBox with biopsy and sequencing
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
        '''
        count = {
            'psn'                  : 0,
            'passed_biopsy'        : 0,
            'failed_biopsy'        : 0,
            'no_biopsy'            : 0,
            'sequenced'            : 0,

            'initial'              : 0,
            'progression_biopsy'   : 0,
            'outside'              : 0,
            'outside_confirmation' : 0,

            'sequenced'            : 0,
        }
        '''

        count = defaultdict(int)

        for p in self.data:
            count['psn'] += 1
            for biopsy in self.data[p]['all_biopsies']:
                biopsy_flag = self.data[p]['biopsies'][biopsy]['status']
                source = self.data[p]['biopsies'][biopsy]['source']
                count[biopsy_flag] += 1
                count[source] += 1


                '''
                if biopsy_flag == 'No Biopsy':
                    count['no_biopsy'] += 1
                elif biopsy_flag == 'Failed Biopsy':
                    count['failed_biopsy'] += 1 
                elif biopsy_flag == 'Pass':
                    count['passed_biopsy'] += 1 

                elif source == 'Outside':
                    count['outside'] += 1
                elif source == 'Progression':
                    count['progression_biopsy'] += 1
                '''

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
        if self._json_db == 'sys_default':
            sys.stderr.write('ERROR: You can not use the system default JSON file and create a system default JSON. You must use '
                'json_db = None in the call to MatchData!\n')
            return None
        formatted_date = utils.get_today('short')
        if not filename:
            filename = 'mb_obj_' + formatted_date + '.json'
        utils.make_json(filename,self.data)

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
        query_term = ''
        for p in self.data:
            if msn:
                if not str(msn).startswith('MSN'):
                    msn = 'MSN'+str(msn)
                query_term = msn
                if msn in self.data[p]['all_msns']:
                    return 'PSN' + p
            elif bsn:
                query_term = bsn
                if bsn in self.data[p]['all_biopsies']:
                    return 'PSN' + p
            else:
                sys.stderr.write('ERROR: No MSN or BSN entered!\n')
                return None
        
        # If we made it here, then we didn't find a result.
        sys.stderr.write('No result for id %s\n' % query_term)
        return None

    def get_msn(self,psn=None,bsn=None):
        """
        Retrieve a patient BSN from either an input PSN or MSN.

        Args:
            psn (str): A MSN number to query. 
            bsn (str): A BSN number to query.

        Returns:
            A list of MSNs that correspond with the input PSN or BSN. 

        >>> print(get_msn(bsn='T-17-000550'))
        [u'MSN44180']

        """
        # result = []
        query_term = ''
        if psn:
            psn = str(psn)
            query_term = psn
            if psn in self.data:
                return self.data[psn]['all_msns']
            # result = self.__search_for_value(key='psn',val=psn,retval='all_msns')

        # TODO: Need to fix this...new struct may break it.
        elif bsn:
            query_term = bsn
            # result = self.__search_for_value(key='bsn',val=bsn,retval='all_msns')
            for p in self.data:
                if bsn in self.data[p]['all_biopsies']:
                    return self.data[p]['biopsies'][bsn]['ngs_data'].keys()
        else:
            sys.stderr.write('ERROR: No PSN or BSN entered!\n')
            return None

        # If we made it here, then we didn't find a result.
        sys.stderr.write('No result for id %s\n' % query_term)
        return None

    def get_bsn(self,psn=None,msn=None):
        """
        Retrieve a patient BSN from either an input PSN or MSN.

        Args:
            psn (str): A PSN number to query. 
            msn (str): A MSN number to query.

        Returns:
            A list PSNs that correspond to the PSN or MSN input.

        >>> print(get_bsn(psn='14420'))
        [u'T-17-000550']

        >>> print(get_bsn(msn='40493'))
        [u'T-17-000165']

        """
        query_term = ''
        if psn:
            psn=str(psn)
            query_term = psn
            if psn in self.data:
                return self.data[psn]['all_biopsies']

        # TODO: Need to fix this. new struct may break it.
        elif msn:
            if not str(msn).startswith('MSN'):
                msn = 'MSN'+str(msn)
            query_term = msn
            for p in self.data:
                if msn in self.data[p]['all_msns']:
                    for b in self.data[p]['biopsies']:
                        if msn in self.data[p]['biopsies'][b]['ngs_data']:
                            return [b]
        else:
            sys.stderr.write('ERROR: No PSN or MSN entered!\n')
            return None

        # If we made it here, then we didn't find a result.
        sys.stderr.write('No result for id %s\n' % query_term)
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

    def get_histology(self,psn=None,msn=None,bsn=None,outside=False,no_disease=False):
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
            >>> print(get_histology(psn='11352'))
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
        psn_list = []
        if psn:
            psn_list = [x.lstrip('PSN') for x in str(psn).split(',')]
        elif msn:
            psn_list = [self.get_psn(msn=x.lstrip('MSN')).lstrip('PSN') for x in str(msn).split(',')]
        elif bsn:
            psn_list = [self.get_psn(bsn=x).lstrip('PSN') for x in bsn.split(',')]
        else:
            psn_list = self.data.keys()

        # TODO: Might need to tweak and re-work the Outside and No Disease filters a bit as they can conflict. But this 
        #       should be workable enough for now.
        output_data = {}
        filtered = []
        for psn in psn_list:
            if psn in self.data:
                # If the no disease filter is turned on (i.e. False) don't out put "No Biopsy" results.
                if outside is False and 'OUTSIDE' in self.data[psn]['source']:
                    filtered.append(psn)
                    continue

                if no_disease is False and self.data[psn]['ctep_term'] == '-':
                    filtered.append(psn)
                    continue

                output_data[psn] = self.data[psn]['ctep_term']
        if filtered:
            sys.stderr.write('WARN: The following specimens were filtered from the output due to either the '
                '"outside" or "no_disease" filters:\n')
            sys.stderr.write('\t%s\n' % ','.join(filtered))

        return output_data

    def find_variant_frequency(self,query):
        """
        Find and return variant hit rates.

        Based on an input query in the form of a variant_type : gene dict, where the gene value
        can be a list of genes, output a list of patients that had hits in those gene with some 
        disease and variant information. 

        The return val will be unique to a patient. So, in the cases where we have multiple biopsies
        from the same patient (an intitial and progression re-biopsy for example), we will only get 
        the union of the two sets, and duplicate variants will not be output.  This will preven the 
        hit rate from getting over inflated.  Also, there is no sequence specific information output
        in this version (i.e. no VAF, Coverage, etc.).  Sequence level information for a call can be
        obtained from the get_variant_report() method below.

        Args:
            query (dict): Dictionary of variant_type: gene mappings where:
                -  variant type is one or more of 'snvs','indels','fusions','cnvs'
                -  gene is a list of genes to query.

            query_patients (list): List of patients for which we want to obtain data. 

        Returns:
            Will return a dict of matching data with disease and MOI information. 
        
        Example:
        >>> query={'snvs' : ['BRAF','MTOR'], 'indels' : ['BRAF', 'MTOR']}
        find_variant_frequency(query)

        """
        # Test cases:
        #    psn11546 : Had failed biopsy, followed by good biopsy wiht NGS results.
        results = {} 
        count = 0
        for patient in self.data:
            if self.data[patient]['biopsies'] != 'No_Biopsy':
                matches = []

                for biopsy in self.data[patient]['biopsies']:
                    b_record = self.data[patient]['biopsies'][biopsy]

                    # Get rid of Outside assays biopsies (but not outside confirmation) and Failed biopsies.
                    if b_record['biopsy_source'] == 'Outside' or b_record['biopsy_status'] != "Pass":
                        continue
                    count += 1
                    biopsies = []

                    # TODO: remove this try except once we're working OK. 
                    try:
                        if b_record['ngs_data'] and 'mois' in b_record['ngs_data']:
                            biopsies.append(biopsy)
                            input_data = b_record['ngs_data']['mois']

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
                    except:
                        print('offending patient record: %s' % patient)
                        sys.exit()

                    if matches:
                        results[patient] = {
                            'psn'      : self.data[patient]['psn'],
                            'disease'  : self.data[patient]['ctep_term'],
                            'msns'     : self.data[patient]['all_msns'],
                            'bsns'     : biopsies,
                            'mois'     : matches
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
