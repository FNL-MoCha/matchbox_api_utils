# -*- coding: utf-8 -*-
# TODO:
#    - get_ihc_results() -> a method to print out patient IHC data based on gene name or psn.
#    - Add BSN query to args list of get_variant_report()
import sys
import json
import itertools
from collections import defaultdict
from pprint import pprint as pp  # TODO: remove in prod i think.

from matchbox_api_utils import utils
from matchbox_api_utils import matchbox_conf

from matchbox_api_utils.matchbox import Matchbox
from matchbox_api_utils.match_arms import TreatmentArms


class MatchData(object):

    """
    MatchboxData class

    Parsed MATCHBox Data from the API as collected from the Matchbox class above. This 
    class has methods to generate queries, further filtering, and heuristics on the 
    dataset.

    """

    def __init__(self, config_file=None, url=None, creds=None, patient=None, 
            json_db='sys_default', load_raw=None, make_raw=None, quiet=True):
        """
        Generate a MATCHBox data object that can be parsed and queried downstream 
        with some methods. 
        
        Can instantiate with either a config JSON file, which contains the url, username, 
        and password information needed to access the resource, or by supplying the 
        individual arguments to make the connection.  This class will call the Matchbox 
        class in order to make the connection and deploy the data.

        Can do a live query to get data in real time, or load a MATCHBox JSON file derived 
        from the matchbox_json_dump.py script that is a part of the package. Since data in 
        MATCHBox is relatively static these days, it's preferred to use an existing JSON DB 
        and only periodically update the DB with a call to the aforementioned script.

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
        self._quiet = quiet
        self._disease_db = {}

        if not self._url:
            self._url = utils.get_config_data(self._config_file,'url')

        if not self._creds:
            self._creds = utils.get_config_data(self._config_file, 'creds')

        if self._patient:
            self._patient = str(self._patient)
            self._url += '?patientId=%s' % self._patient 

        # If json_db is 'sys_default', get json file from matchbox_conf.Config, which is from 
        # matchbox_api_util.__init__.mb_json_data.  Otherwise use the passed arg; if it's None, do
        # a live call below, and if it's a custom file, load that.
        if self._json_db == 'sys_default':
            self._json_db = utils.get_config_data(self._config_file, 'mb_json_data')

        ta_data = utils.get_config_data(self._config_file,'ta_json_data')
        self.arm_data = TreatmentArms(json_db=ta_data)
            
        if make_raw:
            Matchbox(self._url, self._creds, make_raw='mb')
        elif self._load_raw:
            if self._quiet is False:
                print('\n  ->  Starting from a raw MB JSON Obj')
            self.db_date, matchbox_data = utils.load_dumped_json(self._load_raw)
            self.data = self.gen_patients_list(matchbox_data, self._patient)
        elif self._json_db:
            self.db_date, self.data = utils.load_dumped_json(self._json_db)
            if self._quiet is False:
                print('\n  ->  Starting from a processed MB JSON Obj')
                print('\n  ->  JSON database object date: %s' % self.db_date)
            if self._patient:
                if self._quiet is False:
                    print('filtering on patient: %s\n' % self._patient)
                self.data = self.__filter_by_patient(self.data, self._patient)
        else:
            if self._quiet is False:
                print('\n  ->  Starting from a live MB instance')
            matchbox_data = Matchbox(self._url, self._creds).api_data
            self.data = self.gen_patients_list(matchbox_data, self._patient)

        # Load up a medra : ctep term db based on entries so that we can look
        # data up on the fly.
        self._disease_db = self.__make_disease_db()

    def __str__(self):
        return json.dumps(self.data,sort_keys=True,indent=4)

    def __getitem__(self,key):
        return self.data[key]

    def __iter__(self):
        return self.data.itervalues()

    def __make_disease_db(self):
        # Make an on the fly mapping of medra to ctep term db for mapping later
        # on.  Might make a class and all that later, but for now, since we do
        # not know how this will be displayed later, this is good enough.
        med_map = {}
        for pt in self.data.values():
            if 'medra_code' in pt and pt['medra_code'] != '-':
                med_map.update({pt['medra_code'] : pt['ctep_term']})
        return med_map

    @staticmethod
    def __filter_by_patient(json,patient):
        return json[patient]

    @staticmethod
    def __get_var_data_by_gene(data,gene_list):
        # Get variant report data if the gene is in the input gene list.  But, only output the variant level
        # details, and filter out the VAF, coverage, etc. so that we can get unqiue lists later.  If we wanted
        # to get sequence specific details, we'll run a variant report instead.
        wanted = ('alternative', 'amoi', 'chromosome', 'exon', 'confirmed', 'function', 'gene', 'hgvs',
            'identifier', 'oncominevariantclass', 'position', 'protein', 'reference', 'transcript', 'type',
            'driverGene','partnerGene','driverReadCount','annotation','confidenceInterval95percent',
            'confidenceInterval5percent','copyNumber')

        # This is first iteration, and I can't remember why I don't just want all variant level data any more.  
        # return [elem for elem in data if elem['gene'] in gene_list ]
        # return [{i:elem[i] for i in wanted if i in data} for elem in data if elem['gene'] in gene_list]

        results = []
        for rec in data:
            if rec['gene'] in gene_list:
                results.append({i:rec[i] for i in wanted if i in rec})
        return results
        
    @staticmethod
    def __format_id(op,msn=None,psn=None):
        if msn:
            msn = str(msn)
            if op == 'add':
                return 'MSN' + msn.lstrip('MSN')
            elif op == 'rm':
                return msn.lstrip('MSN')
            else:
                sys.stderr.write('ERROR: operation "%s" is not valid.  Can only choose from "add" or "rm"!\n')
                sys.exit(1)
        elif psn:
            psn = str(psn)
            if op == 'add':
                return 'PSN' + psn.lstrip('PSN')
            elif op == 'rm':
                return psn.lstrip('PSN')
            else:
                sys.stderr.write('ERROR: operation "%s" is not valid.  Can only choose from "add" or "rm"!\n')
                sys.exit(1)
        else:
            sys.stderr.write("Nothing to do!\n")
            return None

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
                curr_arm = MatchData.__get_curr_arm(msg['patientSequenceNumber'],
                        assignments[counter]['patientAssignmentLogic'], 'SELECTED')
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
                curr_arm = MatchData.__get_curr_arm(msg['patientSequenceNumber'],
                        assignments[counter]['patientAssignmentLogic'], 'ARM_FULL')
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
            last_status, last_msg, arm_hist, progressed = self.__get_pt_hist(record['patientTriggers'],
                    record['patientAssignments'], record['patientRejoinTriggers'])

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
                            except:
                                continue
                                # print('offending psn: %s' % psn)

                            # Get and add MOI data to patient record; might be from outside.
                            variant_report     = result['ionReporterResults']['variantReport']
                            biopsy_data[bsn]['ngs_data']['mois']  = dict(self.__proc_ngs_data(variant_report))
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

            fusion['driverGene'] = driver
            # Also make a "gene" entry so that we can look things up in a similar way to the other classes.
            fusion['gene'] = driver  
            fusion['partnerGene'] = partner
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
        psn = self.__format_id('rm',psn=psn)
        if val:
            try:
                return {val:self.data[psn][val]}
            except KeyError:
                sys.stderr.write("ERROR: '%s' is not a valid metavalue for this dataset.\n" % val)
                return None
        else:
            return dict(self.data[psn])

    def get_biopsy_summary(self, category=None, ret_type='counts'):
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
            catetory (str): biopsy category to return. Valid categories are:
                'pass', 'failed_biopsy', 'sequenced', 'outside','outside_confirmation', 
                'progression','initial'.
            ret_type (str): Data type to return. Valid types are "counts" and 
                "ids", where counts is the total number in that category, and 
                ids are the BSNs for the category. Default is "counts"

        Returns:
            dict: whole set of category:count or single category:count data.

        # TODO: fix examples.
        Example:
            >>> print(data.get_biopsy_summary())
            {u'sequenced': 5620, u'msns': 5620, u'progression': 9, u'initial': 5563, u'patients': 6491, 
                u'outside': 61, u'no_biopsy': 465, u'failed_biopsy': 574, u'pass': 5654, u'outside_confirmation': 21}


        """
        count = defaultdict(int)
        ids = defaultdict(list)

        for p in self.data:
            count['patients'] += 1
            try:
                if self.data[p]['biopsies'] == 'No_Biopsy':
                    count['no_biopsy'] += 1
                    continue
                for bsn, biopsy in self.data[p]['biopsies'].iteritems():
                    biopsy_flag = biopsy['biopsy_status']
                    source      = biopsy['biopsy_source']
                    count[biopsy_flag.lower()] += 1
                    ids[biopsy_flag.lower()].append(bsn) 

                    # Source will be '---' when a biopsy fails, so exclude those
                    if source != '---':
                        count[source.lower()] += 1
                        ids[source.lower()].append(bsn)
                    if biopsy['ngs_data']:
                        count['sequenced'] += 1
                        ids['sequenced'].append(bsn)
            except:
                print('offending record: %s' % p)
                raise

        results = {}
        if ret_type == 'counts':
            results = dict(count)
        elif ret_type == 'ids':
            results = dict(ids)

        if category:
            try:
                return {category : results[category]}
            except KeyError:
                sys.stderr.write('ERROR: no such category "%s".\n' % category)
                return None
        else:
            return results
    
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
                msn = self.__format_id('add', msn=msn)
                query_term = msn
                if msn in self.data[p]['all_msns']:
                    return self.__format_id('add',psn=p)
            elif bsn:
                query_term = bsn
                if bsn in self.data[p]['all_biopsies']:
                    return self.__format_id('add',psn=p)
            else:
                sys.stderr.write('ERROR: No MSN or BSN entered!\n')
                return None
        
        # If we made it here, then we didn't find a result.
        sys.stderr.write('No result for id %s\n' % query_term)
        return None

    def get_msn(self,psn=None,bsn=None):
        """
        Retrieve a patient MSN from either an input PSN or BSN. Note that there can
        always be more than 1 MSN per patient, but can only ever be 1 MSN per biopsy
        at a time.

        Args:
            psn (str): A MSN number to query. 
            bsn (str): A BSN number to query.

        Returns:
            A list of MSNs that correspond with the input PSN or BSN. 

        >>> print(get_msn(bsn='T-17-000550'))
        [u'MSN44180']

        >>> print(get_msn(bsn='T-16-000811'))
        [u'MSN18184']

        >>> print(get_msn(psn='11583'))
        [u'MSN18184', u'MSN41897']

        """
        query_term = ''
        if psn:
            psn = self.__format_id('rm',psn=psn)
            query_term = psn
            if psn in self.data:
                return self.data[psn]['all_msns']
        elif bsn:
            query_term = bsn
            for p in self.data:
                if bsn in self.data[p]['all_biopsies']:
                    biopsy_data = self.data[p]['biopsies'][bsn]
                    try:
                        return [biopsy_data['ngs_data']['msn']]
                    except KeyError:
                        # We have a biopsy, but no MSN issued yet (or at all).
                        return None
        else:
            sys.stderr.write('ERROR: No PSN or BSN entered!\n')
            return None

        # If we made it here, then we didn't find a result.
        sys.stderr.write('No result for id %s\n' % query_term)
        return None

    def get_bsn(self,psn=None,msn=None):
        """
        Retrieve a patient BSN from either an input PSN or MSN. Note that we can have more than one
        BSN per PSN, but we can only ever have one BSN / MSN.

        Args:
            psn (str): A PSN number to query. 
            msn (str): A MSN number to query.

        Returns:
            A list BSNs that correspond to the PSN or MSN input.

        >>> print(get_bsn(psn='14420'))
        [u'T-17-000550']

        >>> print(get_bsn(psn='11583'))
        [u'T-16-000811', u'T-17-000333'] 

        >>> print(get_bsn(msn='18184'))
        [u'T-16-000811']

        """
        query_term = ''
        if psn:
            psn = self.__format_id('rm', psn=psn)
            query_term = psn
            if psn in self.data:
                return self.data[psn]['all_biopsies']
        elif msn:
            msn = self.__format_id('add',msn=msn)
            query_term = msn
            for p in self.data:
                if msn in self.data[p]['all_msns']:
                    for b in self.data[p]['biopsies']:
                        try:
                            if msn == self.data[p]['biopsies'][b]['ngs_data']['msn']:
                                return [b]
                        except KeyError:
                            continue
        else:
            sys.stderr.write('ERROR: No PSN or MSN entered!\n')
            return None

        # If we made it here, then we didn't find a result.
        sys.stderr.write('No result for id %s\n' % query_term)
        return None

    def get_disease_summary(self, query_disease=None, query_medra=None):
        # TODO: Data is good, but should try to filter outside assay data, failed 
        # specimens, and progression biopsies (collapsed into one count) to get a
        # value that is closer to the accepted 5560 count of study data cohort size.
        """
        Return a summary of registered diseases and counts. With no args, will return
        a list of all diseases and counts as a dict. One can also limit output to a
        list of diseases or medra codes and get counts for those only. 

        Args:
            query_disease (list): List of diseases to filter on.
            query_medra   (list): List of MEDRA codes to filter on.

        Returns:
            Dictionary of disease(s) and counts in the form of:

                    {medra_code : (ctep_term, count)}
        Example:
            >>> data.get_disease_summary(query_medra=['10006190'])
            {'10006190': (u'Invasive breast carcinoma', 641)}

            >>> data.get_disease_summary(query_disease=['Invasive breast carcinoma'])
            {u'10006190': ('Invasive breast carcinoma', 641)} 

            >>> data.get_disease_summary(query_medra=[10006190,10024193,10014735])
            {'10006190': (u'Invasive breast carcinoma', 641),
             '10014735': (u'Endometrioid endometrial adenocarcinoma', 124),
              '10024193': (u'Leiomyosarcoma (excluding uterine leiomyosarcoma)', 57)}
            
        """
        disease_counts = defaultdict(int)
        results = defaultdict(list)

        for psn in self.data.values():
            # Skip the registered but not yet biopsied patients.
            if psn['medra_code'] == '-': 
                continue
            disease_counts[psn['medra_code']] += 1

        if query_medra:
            if isinstance(query_medra, list) is False:
                sys.stderr.write('ERROR: arguments to get_disease_summary() must be lists!\n') 
                return None
            for q in query_medra:
                q = str(q)
                if q in disease_counts:
                    results[q] = (self._disease_db[q], disease_counts[q])
                else:
                    sys.stderr.write('MEDRA code "%s" was not found in the MATCH study '
                        'dataset.\n' % q)
        elif query_disease:
            if isinstance(query_disease, list) is False:
                sys.stderr.write('ERROR: arguments to get_disease_summary() must be lists!\n') 
                return None
            for q in query_disease:
                    q = str(q)
                    medra = next((medra for medra,term in self._disease_db.items() if q == term), None)
                    if medra is not None:
                        results[medra] = (q, disease_counts[medra])
                    else:
                        sys.stderr.write('CTEP Term "%s" was not found in the MATCH study '
                            'dataset.\n' % q)
        else:
            for medra in self._disease_db:
                results[medra] = (self._disease_db[medra], disease_counts[medra])

        if results:
            return dict(results)
        else:
            return None

    def get_histology(self, psn=None, msn=None, bsn=None, outside=False, 
            no_disease=False):
        """
        Return dict of PSN:Disease for valid biopsies.  Valid biopsies can 
        are defined as being only Passed and can not be Failed, No Biopsy or
        outside assay biopsies at this time.

        Args:
            psn (str): Optional PSN or comma separated list of PSNs on which 
                       to filter data.
            bsn (str): Optional BSN or comma separated list of BSNs on which 
                       to filter data.
            msn (str): Optional MSN or comma separated list of MSNs on which 
                       to filter data.
            outside (bool): Also include outside assay data. False by default.
            no_disease (bool): Return all data, even if there is no disease 
                               indicated for the patient specimen. Default: False

        Returns:
            Dict of ID : Disease mappings. If no match for input ID, returns None.

        Example: 
            >>> data.get_histology(psn='11352')
            {'PSN11352': u'Serous endometrial adenocarcinoma'}

            >>> data.get_histology(msn=3060)
            No result for id MSN3060
            {'MSN3060': None}

        """
        # Don't want to allow for mixed query types. So, number of None args 
        # must be > 2 or else user incorrectly entered more than one arg type.
        count_none = sum((x is None for x in (psn,msn,bsn)))
        if count_none < 2:
            sys.stderr.write('Error: Mixed query types detected. Please only use '
                'one type of query ID in this function.\n')
            sys.exit(1)

        # Prepare an ID list dict if one is provided. Need some special mapping 
        # and whatnot before we can pass it.
        query_list = {} # always psn : original ID (ex: {'10098':'T-16-000987'})
        output_data = {}

        if psn:
            psn_list = [x.lstrip('PSN') for x in str(psn).split(',')]
            query_list = dict(zip(psn_list,map(lambda x: self.__format_id('add',psn=x),psn_list)))
            for p in query_list:
                if p not in self.data:
                    output_data[query_list[p]] = None
        
        elif msn:
            msn_list = [self.__format_id('add',msn=x) for x in str(msn).split(',')]
            for m in msn_list:
                psn = self.get_psn(msn=m)
                if psn is not None:
                    query_list[self.__format_id('rm',psn=psn)] = m
                else:
                    output_data[m] = None

        elif bsn:
            bsn_list = bsn.split(',')
            for b in bsn_list:
                psn = self.get_psn(bsn=b)
                if psn is not None:
                    query_list[self.__format_id('rm',psn=psn)] = b
                else:
                    output_data[b] = None
        else:
            psn_list = self.data.keys()
            query_list = dict(zip(psn_list,map(lambda x: self.__format_id('add',psn=x),psn_list)))

        # Iterate through the valid PSNs and get results if they pass filters.
        filtered = []
        for psn in query_list:
            if psn in self.data:
                # If the no disease filter is turned on (i.e. False) don't out put "No Biopsy" results.
                if outside is False and 'OUTSIDE' in self.data[psn]['source']:
                    filtered.append(psn)
                    continue
                if no_disease is False and self.data[psn]['ctep_term'] == '-':
                    filtered.append(psn)
                    continue
                output_data[query_list[psn]] = self.data[psn]['ctep_term']

        if filtered and self._quiet is False:
            sys.stderr.write('WARN: The following specimens were filtered from the output due to either the '
                '"outside" or "no_disease" filters:\n')
            sys.stderr.write('\t%s\n' % ','.join(filtered))

        return output_data

    def find_variant_frequency(self, query, query_patients=None):
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
            Will return a dict of matching data with disease and MOI information, along with 
            a count of the number of patients queried and the number of biopsies queried.
        
        Example:
        >>> query={'snvs' : ['BRAF','MTOR'], 'indels' : ['BRAF', 'MTOR']}
        find_variant_frequency(query)

        >>> pprint(data.find_variant_frequency({'snvs':['EGFR'], 'indels':['EGFR']}, [15232]))
        ({'15232': {'bsns': [u'T-17-001423'],
                    'disease': u'Lung adenocarcinoma',
                    'mois': [{'alternative': u'T',
                              'amoi': [u'EAY131-E(i)', u'EAY131-A(e)'],
                              'chromosome': u'chr7',
                              'confirmed': True,
                              'exon': u'20',
                              'function': u'missense',
                              'gene': u'EGFR',
                              'hgvs': u'c.2369C>T',
                              'identifier': u'COSM6240',
                              'oncominevariantclass': u'Hotspot',
                              'position': u'55249071',
                              'protein': u'p.Thr790Met',
                              'reference': u'C',
                              'transcript': u'NM_005228.3',
                              'type': u'snvs_indels'},
                             {'alternative': u'-',
                              'amoi': [u'EAY131-A(i)'],
                              'chromosome': u'chr7',
                              'confirmed': True,
                              'exon': u'19',
                              'function': u'nonframeshiftDeletion',
                              'gene': u'EGFR',
                              'hgvs': u'c.2240_2257delTAAGAGAAGCAACATCTC',
                              'identifier': u'COSM12370',
                              'oncominevariantclass': u'Hotspot',
                              'position': u'55242470',
                              'protein': u'p.Leu747_Pro753delinsSer',
                              'reference': u'TAAGAGAAGCAACATCTC',
                              'transcript': u'NM_005228.3',
                              'type': u'snvs_indels'}],
                    'msns': [u'MSN52258'],
                    'psn': u'15232'}},
        1)


        """
        results = {} 
        plist = [] 

        # Queue up a patient's list in case you just want to find data for one patient.
        if query_patients:
            pt_list = [self.__format_id('rm',x) for x in query_patients]
        else:
            pt_list = self.data.keys()

        for patient in pt_list:
            # Skip no biopsy and all outside biospy cases.  For outside assay cases, we 
            # don't want to consider any of it since the confirmation data will skew results.
            if self.data[patient]['biopsies'] != 'No_Biopsy' and 'OUTSIDE' not in self.data[patient]['source']:
                matches = []
                for biopsy in self.data[patient]['biopsies']:
                    b_record = self.data[patient]['biopsies'][biopsy]

                    # Get rid of Outside assays biopsies (but not outside confirmation) and Failed biopsies.
                    # if b_record['biopsy_source'] == 'Outside' or b_record['biopsy_status'] != "Pass":
                    if b_record['biopsy_status'] != "Pass":
                        continue
                    biopsies = []

                    try:
                        if b_record['ngs_data'] and 'mois' in b_record['ngs_data']:
                            plist.append(patient)
                            biopsies.append(biopsy)
                            input_data = b_record['ngs_data']['mois']

                            if 'snvs' in query and 'singleNucleotideVariants' in input_data:
                                matches += self.__get_var_data_by_gene(input_data['singleNucleotideVariants'],
                                    query['snvs'])

                            if 'indels' in query and 'indels' in input_data:
                                matches += self.__get_var_data_by_gene(input_data['indels'],query['indels'])

                            if 'cnvs' in query and 'copyNumberVariants' in input_data:
                                matches += self.__get_var_data_by_gene(input_data['copyNumberVariants'],query['cnvs'])

                            if 'fusions' in query and 'unifiedGeneFusions' in input_data:
                                # input_data['unifiedGeneFusions'] is a list
                                filtered_fusions = []
                                for fusion in input_data['unifiedGeneFusions']:
                                    if fusion['identifier'].endswith('Novel') or fusion['identifier'].endswith('Non-Targeted'): 
                                        continue
                                    else:
                                        filtered_fusions.append(fusion)
                                matches += self.__get_var_data_by_gene(filtered_fusions,query['fusions'])
                    except:
                        print('offending patient record: %s' % patient)
                        raise

                    if matches:
                        results[patient] = {
                            'psn'      : self.data[patient]['psn'],
                            'disease'  : self.data[patient]['ctep_term'],
                            'msns'     : self.data[patient]['all_msns'],
                            'bsns'     : biopsies,
                            'mois'     : matches
                        }
        return results, len(set(plist)), len(plist)

    def get_variant_report(self, psn=None, msn=None):
        """
        Input a PSN or MSN (preferred!) and return a list of dicts of variant call data.

        Since there can be more than one MSN per patient, one will get a more robust result 
        by querying on a MSN.  That is, only one variant report / MSN can be generated and 
        the results, then, will be clear.  In the case of querying by PSN, a variant report
        for each MSN under that PSN, assuming that the MSN is associated with a variant 
        report, will be returned.

        Args:
           msn (str):  MSN for which a variant report should be returned.
           psn (str):  PSN for which the variant reports should be returned.

        Returns:
           List of dicts of variant results.
           msn: { 'singleNucleotideVariants' : [{var_data}], 'copyNumberVariants' : [{var_data},{var_data}], etc. }

        """
        if msn:
            msn = self.__format_id('add',msn=msn)
            psn=self.get_psn(msn=self.__format_id('rm',msn=msn))
            for biopsy in self.data[psn]['biopsies'].values():
                if 'ngs_data' in biopsy and biopsy['ngs_data']['msn'] == msn:
                    return {self.__format_id('add',msn=msn) : biopsy['ngs_data']['mois']}
                else:
                    return None
        elif psn:
            results = {}  # if we are searching by PSN, can get multiple reports. Print them all as a list.
            psn = self.__format_id('rm',psn=psn)
            try:
                if not len(self.data[psn]['all_msns']) > 0:
                    sys.stderr.write('No variant report available for patient: %s.\n' % psn)
                    return None
            except:
                sys.stderr.write('ERROR: Patient %s does not exist in the database!\n')
                return None

            for biopsy in self.data[psn]['biopsies'].values():
                # Skip the outside assays biopsies since the variant reports are unreliable for now. Maybe we'll 
                # take these later with an option? Also have to skip outside confirmation cases now as the assay
                # does not always cover the variants and now MATCHBox is including calls that are outside of our 
                # reportable range....a real mess!
                # if biopsy['biopsy_source'] == 'Outside':
                if 'Outside' in biopsy['biopsy_source']:
                    continue
                elif biopsy['ngs_data'] and 'mois' in biopsy['ngs_data']:
                    results[self.__format_id('add',msn=biopsy['ngs_data']['msn'])] = biopsy['ngs_data']['mois']
            if results:
                return results
            else:
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
    
    def get_patients_by_disease(self, histology=None, medra_code=None):
        """
        Input a disease and return a list of patients that were registered with that disease
        type. For histology query, we can do partial matching based on the python `in` function.
        So, if one were to query Lung Adenocarcinoma, Lung, Lung Adeno, or Adeno, all Lung 
        Adenocarinoma cases would be returned.  Note that simply inputting Lung, would also 
        return Non-small Cell Lung Adenocarinoma, Squamouse cell lung adenocarcinoma, etc, and 
        querying "Adeno" would return anything that had adeno.  So, care must be taken with the 
        query, and secondary filtering may be necessary.  Querying based on MEDRA codes is specific
        and only an exact match will return results.

        Args:
            histology (str):  One of the CTEP shotname disease codes.
            medra_code (str): A MEDRA code to query rather than histology.

        Returns:
            Dict of Patient : Histology Mapping

        Example:
            >>> <put example here>


        """
        if not any(x for x in [histology, medra_code]):
            sys.stderr.write("ERROR: You must input either a histologie or medra code "
                "to query!\n")
            return None

        results = {}
        if histology:
            for pt in self.data:
                if histology.lower() in self.data[pt]['ctep_term'].lower():
                    results[pt] = self.data[pt]['ctep_term']

        elif medra_code:
            for pt in self.data:
                if medra_code == self.data[pt]['medra_code']:
                    results[pt] = self.data[pt]['ctep_term']
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
                results.append((pt,arm,self.data[pt]['ta_arms'][arm]))
        return results
