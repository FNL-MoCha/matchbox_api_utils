# -*- coding: utf-8 -*-
import sys
import json
import itertools
from collections import defaultdict

from matchbox_api_utils import utils
from matchbox_api_utils import matchbox_conf

from matchbox_api_utils.matchbox import Matchbox
from matchbox_api_utils.match_arms import TreatmentArms
import matchbox_api_utils._version


class MatchData(object):

    """
    **NCI-MATCH MATCHBox Data class**

    Parsed MATCHBox Data from the API as collected from the Matchbox class. 
    This class has methods to generate queries, further filtering, and 
    heuristics on the dataset.

    Generate a MATCHBox data object that can be parsed and queried downstream 
    with some methods. 
    
    Can instantiate with either a config JSON file, which contains the url, 
    username, and password information needed to access the resource, or by 
    supplying the individual arguments to make the connection.  This class 
    will call the Matchbox class in order to make the connection and deploy 
    the data.

    Can do a live query to get data in real time, or load a MATCHBox JSON file 
    derived from the ``matchbox_json_dump.py`` script that is a part of the 
    package.  Since data in MATCHBox is relatively static these days, it's 
    preferred to use an existing JSON DB and only periodically update the DB 
    with a call to the aforementioned script.

    Args:
        matchbox (str) : Name of the MATCHBox system from which we want to
            get data. This is required now that we have several systems to
            choose from.  Valid names are ``adult``, ``ped``, and 
            ``adult-uat`` for those that have access to the adult MATCHBox
            test system. **DEFAULT:** ``adult``.

        config_file (file): Custom config file to use if not using system 
            default.

        username (str): Username required for access to the MATCHBox. Typically
            this is already present in the config file made during setup, but 
            in cases where needed, it can be explicitly defined here.

        password (str): Password associated with the user. As with the above
            username argument, this is typically indicated in the config file
            generated during setup. 

        patient (str): Limit data to a specific PSN.

        json_db (file): MATCHbox processed JSON file containing the whole
            dataset. This is usually generated from 'matchbox_json_dump.py'. 
            The default value is ``'sys_default'`` which loads the default 
            package data. If you wish you get a live call, set this variable 
            to ``None``.

        load_raw (file): Load a raw API dataset rather than making a fresh
            call to the API. This is intended for dev purpose only and may 
            be disabled later.

        make_raw (bool): Make a raw API JSON dataset for dev purposes only. 
            This will be the file used with the ``load_raw`` option.

        quiet (bool): If ``True``, suppress module output debug, information, 
            etc. messages. 

    """

    def __init__(self, matchbox='adult', method='mongo', config_file=None, 
        username=None, password=None, patient=None, json_db='sys_default', 
        load_raw=None, make_raw=None, quiet=False):

        sys.stderr.write('\nWelcome to MATCHBox API Utils Version %s\n' % 
            matchbox_api_utils._version.__version__)
        sys.stderr.flush()

        # Determine which MATCHBox we'll be using and validate the entry.
        self._matchbox = matchbox
        valid_matchboxes = ('adult', 'ped', 'pediatric', 'adult-uat')
        if self._matchbox not in valid_matchboxes:
            sys.stderr.write('ERROR: No such MATCHBox "%s". Valid MATCHBoxes '
                'are:\n' % matchbox)
            sys.stderr.write('\n'.join(valid_matchboxes))
            sys.stderr.write('\n')
            return None

        self._patient = self.__format_id('rm', psn=patient)
        self._json_db = json_db
        self.db_date = utils.get_today('long')
        self._quiet = quiet

        # Ensure that we pass "mb" to Matchbox()
        if make_raw:
            make_raw = 'mb'

        if not self._quiet:
            sys.stderr.write('[ INFO ]  Loading MATCHBox: %s\n' % 
                self._matchbox)

        # Get some configs from the input (or default config file).
        self._config_data = matchbox_conf.Config(self._matchbox, method,
            config_file=config_file)
        sys.stderr.write('[ DEBUG ]  Config data:\n')
        utils.pp(self._config_data.config_data)

        # If json_db is 'sys_default', get json file from matchbox_conf.Config, 
        # which is from matchbox_api_util.__init__.mb_json_data.  Otherwise use 
        # the passed arg; if it's None, do a live call below, and if it's a 
        # custom file, load that.
        if self._json_db == 'sys_default':
            self._json_db = self._config_data.get_config_item('mb_json_data')

        # Load up a TA Obj for annotation and whatnot in some methods.
        ta_data = self._config_data.get_config_item('ta_json_data')
        self.arm_data = TreatmentArms(self._matchbox, json_db=ta_data, 
            quiet=True)
            
        # Load total MB dataset, in raw archived JSON format.
        if load_raw:
            if self._quiet is False:
                sys.stderr.write('\n  ->  Starting from a raw MB JSON Obj\n')
            self.db_date, matchbox_data = utils.load_dumped_json(load_raw)
            self.data = self.__gen_patients_list(matchbox_data, self._patient)

        # Load parsed MB JSON dataset rather than a live query.
        elif self._json_db:
            self.db_date, self.data = utils.load_dumped_json(self._json_db)
            if self._quiet is False:
                sys.stderr.write('\n  ->  Starting from a processed MB JSON '
                    'Object.\n')
                sys.stderr.write('\n  ->  JSON database object date: '
                    '%s\n' % self.db_date)
            if self._patient:
                if self._quiet is False:
                    sys.stderr.write('Filtering on patient: '
                        '%s.\n' % self._patient)
                self.data = self.__get_record(self._patient)

        # Make a live query to MB and either create a new raw_db or parse it out
        # and work from there.
        else:
            if self._quiet is False:
                sys.stderr.write('\n  ->  Starting from a live MB instance\n')
                
            if self._patient:
                if method == 'api':
                    url = self._config_data.get_config_item('url')
                    url += '/%s' % self._patient
                    self._config_data.put_config_item('url', url)
                else:
                    sys.stderr.write('[ WARN ]  We can not make an API call '
                        'with a patient identifier when using the "mongo"\n'
                        'method at this time.\n')
                
            params = {
                'size' : '500',
                'sort' : 'patientSequenceNumber',
            }

            matchbox_data = Matchbox(
                method=method,
                mongo_collection='patient',
                config=self._config_data,
                params=params, 
                make_raw=make_raw,
                quiet=self._quiet,
            ).api_data

            # If we are filtering on a patient, then we don't get a list of 
            # dicts, so we need to convert the data before passing or else 
            # problems.
            if self._patient and method == 'api':
                matchbox_data = [matchbox_data]
            self.data = self.__gen_patients_list(matchbox_data, self._patient)

        if self.data is None:
            sys.stderr.write('[ ERROR ]  No data returned from MATCHBox call! '
                'Something seems to have gone wrong here.\n')
            return None
        # Load up a meddra : ctep term db based on entries so that we can look
        # data up on the fly.
        self._disease_db = self.__make_disease_db()

    def __str__(self):
        return utils.print_json(self.data)

    def __getitem__(self,key):
        return self.data[key]

    def __iter__(self):
        return self.data.itervalues()

    def __make_disease_db(self):
        # Make an on the fly mapping of meddra to ctep term db for mapping later
        # on.  Might make a class and all that later, but for now, since we do
        # not know how this will be displayed later, this is good enough.
        med_map = {}
        for pt in self.data.values():
            meddra = pt.get('meddra_code', None)
            if meddra is None:
                print('Offending record:')
                utils.pp(pt)
                sys.exit()
            if meddra != 'null':
                med_map.update({pt['meddra_code'] : pt['ctep_term']})
        return med_map

    def __get_record(self, psn):
        # Get a patient record based on a PSN if it's in the DB. Return a dict
        # of PSN : Record.
        rec = self.data.get(psn, None)
        if rec is None:
            sys.stderr.write('ERROR: Can not filter on patient with id: %s! '
                'No such patient\nin this version of the database.\n' % psn)
            return None
        return {psn : rec}

    @staticmethod
    def __get_var_data_by_gene(data, gene_list):
        # Get variant report data if the gene is in the input gene list.  But, 
        # only output the variant level details, and filter out the VAF, 
        # coverage, etc. so that we can get unqiue lists later.  If we wanted 
        # to get sequence specific details, we'll run a variant report instead.

        wanted = ('alternative', 'amoi', 'chromosome', 'exon', 'confirmed', 
            'function', 'gene', 'hgvs', 'identifier', 'oncominevariantclass', 
            'position', 'protein', 'reference', 'transcript', 'type', 
            'driverGene', 'partnerGene', 'driverReadCount', 'annotation', 
            'confidenceInterval95percent', 'confidenceInterval5percent',
            'copyNumber', 'alleleFrequency', 'copyNumber', 'driverReadCount')

        results = []
        for rec in data:
            if rec['gene'] in gene_list:
                results.append({i:rec[i] for i in wanted if i in rec})
        return results
        
    @staticmethod
    def __format_id(op, *, msn=None, psn=None):
        if op not in ('add', 'rm'):
            sys.stderr.write('ERROR: operation "%s" is not valid.  Can only '
                'choose from "add" or "rm"!\n')
            sys.exit(1)

        if msn:
            msn = str(msn)
            if op == 'add':
                return 'MSN' + msn.lstrip('MSN')
            elif op == 'rm':
                return msn.lstrip('MSN')
        elif psn:
            psn = str(psn)
            if op == 'add':
                return 'PSN' + psn.lstrip('PSN')
            elif op == 'rm':
                return psn.lstrip('PSN')

    def __get_patient_table(self, psn, next_key=None):
        # Output the filtered data table for a PSN so that we have a quick way 
        # to figure out key : value structure for the dataset.
        for key, val in self.data[str(psn)].items():
            if next_key:
                if key == next_key:
                    for k2, v2 in self.data[str(psn)][key].items():
                        return json.dumps(self.data[str(psn)][key], indent=4,
                                sort_keys=True)
            else:
                return utils.print_json(self.data[str(psn)])

    @staticmethod
    def __get_curr_arm(psn, assignment_logic_list, flag):
        # Figure out the arm to which the patient was assigned based on the 
        # flag message found in the TA Logic flow.
        try:
            return[x['treatmentArmId'] 
                    for x in assignment_logic_list 
                    if x['patientAssignmentReasonCategory'] == flag][0]
        except:
            # There are exactly 4 cases (as of 9/19/2017) where the patient has 
            # PTEN IHC-, but was not assigned Arm P directly for some reason 
            # that I can't discern. Instead patient was put on compassionate 
            # care for Arm P, and although I can't comptutationally derive that
            # since there is no obvious messsage, I don't want to lose those 
            # results. So, I'm going to manually enter data for those 4 until 
            # I can figure out how to get this in better.
            if psn in ('13629','13899','14007','14057'):
                return 'EAY131-P'
            else:
                print('{}: can not get flag from logic list!'.format(psn))
                return 'UNK'

    @staticmethod
    def __get_pt_hist(triggers, assignments, rejoin_triggers):
        # Read the trigger messages to determine the patient treatment and 
        # study arm history.
        arm_hist = {}
        progressed = False
        tot_msgs = len(triggers)

        # If we only ever got to registration and not further (so there's only 
        # 1 message), let's bail out
        if tot_msgs == 1:
            return (triggers[0]['patientStatus'], triggers[0]['message'], {}, 
                False)

        counter = 0
        curr_arm = ''
        for i, msg in enumerate(triggers):
            # On a rare occassion, we get two of the same messages in a row. 
            # Just skip the redundant message?
            if triggers[i-1]['patientStatus'] == msg['patientStatus']:
                continue
            
            if msg['patientStatus'] == 'REJOIN':
                counter += 1

            if msg['patientStatus'] == 'PENDING_APPROVAL':
                curr_arm = MatchData.__get_curr_arm(
                    msg['patientSequenceNumber'],
                    assignments[counter]['patientAssignmentLogic'], 
                    'SELECTED'
                )

                try:
                    arm_hist[curr_arm] = assignments[counter]['patientAssignmentMessages'][0]['status']
                except IndexError:
                    # We don't have a message because no actual assignment ever 
                    # made (i.e. OFF_TRIAL before assignment)
                    arm_hist[curr_arm] = '.'
                counter += 1

            if msg['patientStatus'].startswith("PROG"):
                progressed = True
                arm_hist[curr_arm] = 'FORMERLY_ON_ARM_PROGRESSED'

            elif msg['patientStatus'] == 'COMPASSIONATE_CARE':
                curr_arm = MatchData.__get_curr_arm(
                    msg['patientSequenceNumber'],
                    assignments[counter]['patientAssignmentLogic'], 
                    'ARM_FULL'
                )
                arm_hist[curr_arm] = 'COMPASSIONATE_CARE'

            # When we hit the last message, return what we've collected.
            if i+1 == tot_msgs:
                last_status = msg['patientStatus']
                last_msg = msg.get('message', '---')
                if arm_hist:
                    if last_status.startswith('OFF_TRIAL'):
                        if arm_hist[curr_arm] == 'ON_TREATMENT_ARM':
                            arm_hist[curr_arm] = 'FORMERLY_ON_ARM_OFF_TRIAL'

                    if arm_hist[curr_arm] == '.':
                        arm_hist[curr_arm] = last_status

                return last_status, last_msg, arm_hist, progressed

    def __gen_patients_list(self, matchbox_data, patient):
        # Process the MATCHBox API data (usually in JSON format from MongoDB) 
        # into a much more concise and easily parsable dict of data. This dict 
        # will be the main dataset used for later data analysis and queries and
        # is the main structure for the MatchboxData class below.
        patients = defaultdict(dict)
        for record in matchbox_data:
            psn = record['patientSequenceNumber']
            
            if patient and psn != str(patient):
                continue
            
            patients[psn]['psn']         = psn
            patients[psn]['gender']      = record.get('gender', 'null')
            patients[psn]['ethnicity']   = record.get('ethnicity', 'null')
            patients[psn]['source']      = record.get('patientType', 'null')
            patients[psn]['concordance'] = record.get('concordance', 'null')

            races = record.get('races', [])
            if len(record.get('races', [])) > 0:
                patients[psn]['race'] = races[0]
            else: patients[psn]['race'] = 'null'

            # For diseases, we have a list, where the last element is the latest
            # edit and the most correct data. But the list might be empty if no
            # biopsy ever taken.
            try:
                latest_disease = record['diseases'][-1]
            except IndexError:
                latest_disease = {}

            patients[psn]['ctep_term'] = latest_disease.get('ctepTerm', 'null')
            patients[psn]['meddra_code'] = latest_disease.get('_id', 'null')

            patients[psn]['all_msns']     = []
            patients[psn]['all_biopsies'] = []

            # Get treatment arm history. 
            # TODO: Right now just getting a dict of arm : status. Do we want to
            # set this up as a list of dicts that include assignment date too, 
            # so that we can order them, and make length on arm calcs?
            pt_triggers = record.get('patientTriggers', None)
            pt_assignments = record.get('patientAssignments', None)
            pt_rejoin_trigs = record.get('patientRejoinTriggers', None)

            last_status, last_msg, arm_hist, progressed = self.__get_pt_hist(
                    pt_triggers, 
                    pt_assignments, 
                    pt_rejoin_trigs
            )

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
                    # XXX: manual skip for now; will have to find a way to clean up
                    #      database later.
                    if bsn == 'T-16-002080' and psn == '12850':
                        continue
                    patients[psn]['all_biopsies'].append(bsn)
                
                    biopsy_data = defaultdict(dict)
                    biopsy_data[bsn]['ihc']      = '---'
                    biopsy_data[bsn]['biopsy_source']   = '---'
                    biopsy_data[bsn]['ngs_data'] = {}

                    if biopsy['failure']:
                        biopsy_data[bsn]['biopsy_status'] = 'Failed_Biopsy'
                    else:
                        biopsy_data[bsn]['biopsy_status'] = 'Pass'
                        biopsy_data[bsn]['ihc'] = self.__get_ihc_results(
                                biopsy['assayMessages']
                        )

                        # Define biopsy type as Initial, Progression, or Outside
                        biopsy_type = biopsy['biopsyType']
                        if biopsy_type == 'STANDARD':
                            biopsy_type = biopsy['associatedPatientStatus']

                        biopsy_sources = {
                            'OUTSIDE' : 'Outside',
                            'CONFIRMATION' : 'Confirmation',
                            'PROGRESSION_REBIOPSY' : 'Progression',
                            'REGISTRATION' : 'Initial'
                        }
                        status = biopsy_sources[biopsy_type]
                        biopsy_data[bsn]['biopsy_source'] = status

                        # Don't load up outside assay data as it's mish-mosh
                        if status == 'Outside':
                            biopsy_data[bsn]['ngs_data'] = 'NA'
                        else:
                            for result in biopsy['nextGenerationSequences']:
                                # Skip all Failed and Pending reports.
                                if result['status'] != 'CONFIRMED':  
                                    continue 
                                ir_data = result['ionReporterResults']
                                msn, runid, dna, rna, vcf, vardata = utils.get_vals(
                                    ir_data, 
                                    'molecularSequenceNumber',
                                    'jobName', 
                                    'dnaBamFilePath',
                                    'rnaBamFilePath',
                                    'vcfFilePath',
                                    'variantReport',
                                )
                                patients[psn]['all_msns'].append(msn)
                                biopsy_data[bsn]['ngs_data']['msn'] = msn
                                biopsy_data[bsn]['ngs_data']['ir_runid'] = runid
                                biopsy_data[bsn]['ngs_data']['dna_bam_path'] = dna
                                biopsy_data[bsn]['ngs_data']['rna_bam_path'] = rna
                                biopsy_data[bsn]['ngs_data']['vcf_path'] = vcf

                                biopsy_data[bsn]['ngs_data']['mois']  = dict(
                                    self.__proc_ngs_data(vardata)
                                )

                    patients[psn]['biopsies'].update(dict(biopsy_data))
        # utils.pp(dict(patients))
        # utils.__exit__(448, "Finished with generating Patient DB.")
        return patients

    @staticmethod
    def __get_ihc_results(ihc_data):
        # Get and load IHC results from dataset.
        ihc_results = {}
        for assay in ihc_data:
            if 'result' in assay:
                assay_name = assay['biomarker'].rstrip('s').lstrip('ICC')
                ihc_results[assay_name] = assay['result']

        # Won't always get RB IHC; depends on if we have other qualifying 
        # genomic event.  Fill in data anyway.
        if 'RB' not in ihc_results:
            ihc_results['RB'] = 'ND'
        return ihc_results

    def __proc_ngs_data(self, ngs_results):
       # Create and return a dict of variant call data that can be stored in 
       # the patient's obj.
        variant_call_data = defaultdict(list)
        variant_list = ['singleNucleotideVariants', 'indels', 
            'copyNumberVariants', 'unifiedGeneFusions']

        for var_type in variant_list:
            for variant in ngs_results[var_type]:
                if variant['confirmed']:
                    # Still some non-conforming variants present!
                    if var_type == 'unifiedGeneFusions':
                        if 'Targeted' in variant['identifier']:
                            continue
                    var_data = self.__gen_variant_dict(variant, var_type)
                    var_data.update({'amoi' : self.arm_data.map_amoi(var_data)})
                    variant_call_data[var_type].append(var_data)

        # Remap the driver / partner genes so that we know they're correct, and 
        # add a 'gene' field to use later on.
        if 'unifiedGeneFusions' in variant_call_data:
            variant_call_data['unifiedGeneFusions'] = self.__remap_fusion_genes(
                variant_call_data['unifiedGeneFusions']
            )
        return variant_call_data

    @staticmethod
    def __gen_variant_dict(vardata, vartype):
        # Based on input variant call data, return a dict of variant type and 
        # wanted fields
        meta_key = {
            'singleNucleotideVariants' : 'snvs_indels',
            'indels'                   : 'snvs_indels',
            'copyNumberVariants'       : 'cnvs',
            'unifiedGeneFusions'       : 'fusions',
        }

        include_fields = { 
                'snvs_indels' :  [
                    'alleleFrequency', 'alternative', 
                    'alternativeAlleleObservationCount', 'chromosome', 'exon', 
                    'flowAlternativeAlleleObservationCount', 
                    'flowReferenceAlleleObservations', 'function', 'gene', 
                    'hgvs', 'identifier', 'oncominevariantclass', 'position', 
                    'readDepth', 'reference', 'referenceAlleleObservations', 
                    'transcript', 'protein', 'confirmed'
                ], 
                'cnvs' : [
                    'chromosome', 'identifier', 'confidenceInterval5percent', 
                    'confidenceInterval95percent', 'copyNumber','confirmed',
                    'gene'
                ],
                'fusions' : [
                    'annotation', 'identifier', 'driverReadCount', 'driverGene',
                    'partnerGene','confirmed'
                ]
        }

        data = dict((key, vardata.get(key, '.')) for key in include_fields[meta_key[vartype]])
        data['type'] = meta_key[vartype]
        return data

    @staticmethod
    def __remap_fusion_genes(fusion_data):
        # Fix the fusion driver / partner annotation since it is not always 
        # correct the way it's being parsed.  Also add in a 'gene' field so 
        # that it's easier to aggregate data later on (the rest of the elements 
        # use 'gene').
        for fusion in fusion_data:
            driver, partner = utils.map_fusion_driver(fusion['driverGene'], 
                fusion['partnerGene'])

            fusion['driverGene'] = driver
            fusion['gene'] = driver  
            fusion['partnerGene'] = partner
        return fusion_data

    def get_patient_meta(self, psn, val=None):
        """
        Return data for a patient based on a metadata field name. Sometimes we 
        may want to just get a quick bit of data or field for a patient record 
        rather than a whole analysis, and this can be a convenient way to just 
        check a component rather than writing a method to get each and every bit
        out. If no metaval is entered, will return the whole patient dict.

        .. note::
            This function is more for debugging and troubleshooting that for 
            real functionality.

        Args:
            psn (str):  PSN of patient for which we want to receive data.

            val (str):  Optional metaval of data we want. If nothing entered, 
                will return the entire patient record.

        Returns:
            dict: 
            Either return dict of data if a metaval entered, or whole patient 
            record. Returns ``None`` if no data for a particular record and 
            raises and error if the metaval is not valid for the dataset.

        """
        pt = self.__format_id('rm', psn=psn)
        pt_data = self.__get_record(pt)
        if pt_data is None:
            sys.stderr.write("ERROR: No such patient with id: %s.\n" % psn)
            return None

        if val:
            try:
                return self.data[pt][val]
            except KeyError:
                sys.stderr.write("ERROR: '%s' is not a valid metavalue for "
                    "this dataset.\n" % val)
                return None
        else:
            return pt_data

    def get_biopsy_summary(self, category=None, ret_type='counts'):
        # TODO: These numbers are sort of wonky.  Because of the way patients
        #       are registered, the numbers don't always really make sense. i
        #       think we need some logic here to clean up the values a bit.
        """
        Return dict of patients registered in MATCHBox with biopsy and 
        sequencing information. 
        
        Categories returned are total PSNs issued (including outside assay 
        patients), total passed biopsies, total failed biopsies (per MDACC 
        message), total MSNs (only counting latest MSN if more than one issued 
        to a biopsy due to a failure) as a method of figuring out how many NAs 
        were prepared, and total with sequencing data.

        Can filter output based on any one criteria by leveraging the 
        ``category`` variable

        Args:
            catetory (str): biopsy category to return. Valid categories are:

                * patients - Any patient that has ever registered.
                * failed_biopsy - Number of failed biopsies.
                * no_biopsy - Number of patient for which no biopsy collected.
                * pass - Number of biopsies that passed.
                * sequenced - Number of sequencing results available.
                * outside - Number of outside assay cases.
                * confirmation - Number of confirmation sequences for outside
                  assay results.
                * progression - Number of progression biopsy cases.
                * initial - Number of non-outside assay cases.

            ret_type (str): Data type to return. Valid types are "counts" and 
                "ids", where counts is the total number in that category, and 
                ids are the BSNs for the category. Default is "counts"

        Returns:
            dict:
            Dictionary of whole set of ``{category : count}`` or 
            ``{single category : count}`` data.

        Examples:
            >>> print(data.get_biopsy_summary())
            {'patients': 6560, 'failed_biopsy': 576, 'no_biopsy': 465, 
             'pass': 5776, 'initial': 5563, 'sequenced': 5748, 
             'progression': 19, 'outside': 130, 'confirmation': 64}

            >>> print(data.get_biopsy_summary(category='progression'))
            {'progression': 19}

            >>> print(data.get_biopsy_summary(category='progression', 
            ...     ret_type='ids')
            {'progression': ['T-17-001275',
                 'T-17-000787',
                 'T-17-001175',
                 'T-17-002730',
                 'T-17-002657',
                 'T-17-000333',
                 'T-17-002564',
                 'T-17-002556',
                 'T-17-002600',
                 'T-17-002064',
                 'T-18-000113',
                 'T-17-002755',
                 'T-17-002621',
                 'T-18-000005',
                 'T-17-002680',
                 'T-18-000071',
                 'T-18-000171',
                 'T-18-000123',
                 'T-18-000031']}

        """
        count = defaultdict(int)
        ids = defaultdict(list)

        for p in self.data:
            count['patients'] += 1
            try:
                if self.data[p]['biopsies'] == 'No_Biopsy':
                    count['no_biopsy'] += 1
                    continue
                for bsn, biopsy in self.data[p]['biopsies'].items():
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
    
    def matchbox_dump(self, filename=None):
        """
        Dump a parsed MATCHBox dataset.
        
        Call to the API and make a JSON file that can later be loaded in, 
        rather than making an API call and reprocessing. Useful for quicker 
        look ups as the API call can be very, very slow with such a large DB.

        .. note:: 
            This is a different dataset than the raw dump.

        Args:
            filename (str): Filename to use for output. Default filename is:

                ``mb_obj_<date_generated>.json``

        Returns:
            JSON: 
            MATCHBox API JSON file.

        """
        if self._json_db == 'sys_default':
            sys.stderr.write('ERROR: You can not use the system default JSON '
                'file and create a system default JSON! You must use "json_db'
                '=None" in the call to MatchData!\n')
            return None
        formatted_date = utils.get_today('short')
        if not filename:
            filename = 'mb_obj_' + formatted_date + '.json'
        utils.make_json(outfile=filename, data=self.data)

    def get_psn(self, msn=None, bsn=None):
        """
        Retrieve a patient PSN from either an input MSN or BSN.

        Args:
            msn (str): A MSN number to query. 
            bsn (str): A BSN number to query.

        Returns:
            str: A PSN that maps to the MSN or BSN input.

        Examples: 
            >>> print(get_psn(bsn='T-17-000550'))
            PSN14420

            >>> print(get_psn(msn='57471'))
            PSN15971

        .. warning::
            I have found at least one example where there was a duplicate BSN used
            for a patient, and so great care must be used if trying to map this 
            BSN to other data (see PSNs 12913 and 12850)!

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

    def get_msn(self, psn=None, bsn=None):
        """
        Retrieve a patient MSN from either an input PSN or BSN. 
        
        Args:
            psn (str): A MSN number to query. 
            bsn (str): A BSN number to query.

        .. note:: 
            There can always be more than 1 MSN per patient, but can only 
            ever be 1 MSN per biopsy at a time.

        Returns:
            list: A list of MSNs that correspond with the input PSN or BSN. 

        Examples: 
            >>> print(get_msn(bsn='T-17-000550'))
            [u'MSN44180']

            >>> print(get_msn(bsn='T-16-000811'))
            [u'MSN18184']

            >>> print(get_msn(psn='11583'))
            [u'MSN18184', u'MSN41897']

        """
        query_term = ''
        if psn:
            psn = self.__format_id('rm', psn=psn)
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

    def get_bsn(self, psn=None, msn=None):
        """
        Retrieve a patient BSN from either an input PSN or MSN. 
        
        Args:
            psn (str): A PSN number to query. 
            msn (str): A MSN number to query.

        .. note:: 
            Can have more than one BSN per PSN, but can only ever have 
            one BSN / MSN.

        Returns:
            list: A list BSNs that correspond to the PSN or MSN input.

        Examples: 
            >>> print(get_bsn(psn='14420'))
            [u'T-17-000550']

            >>> print(get_bsn(psn='11583'))
            [u'T-16-000811', u'T-17-000333'] 

            >>> print(get_bsn(msn='18184'))
            [u'T-16-000811']

            >>> print(get_bsn(psn='11586'))
            None

        """
        query_term = ''
        if psn:
            psn = self.__format_id('rm', psn=psn)
            query_term = psn
            biopsies = []
            if psn in self.data:
                biopsy_data = self.data[psn]['biopsies']
                if biopsy_data == 'No_Biopsy':
                    sys.stderr.write('WARN: No Biopsy for specimen %s.\n' % psn)
                    return None

                for biop in biopsy_data.keys():
                    if biopsy_data[biop]['biopsy_status'] != 'Failed_Biopsy':
                        biopsies.append(biop)
            return biopsies
        elif msn:
            msn = self.__format_id('add',msn=msn)
            query_term = msn
            for p in self.data:
                if msn in self.data[p]['all_msns']:
                    for b, data in self.data[p]['biopsies'].items():
                        msn = data['ngs_data'].get('msn', None)
                        if msn is None:
                            continue
                        if data['biopsy_status'] != 'Failed_Biopsy':
                            return [b]
        else:
            sys.stderr.write('ERROR: No PSN or MSN entered!\n')
            return None

        # If we made it here, then we didn't find a result.
        sys.stderr.write('No result for id %s\n' % query_term)
        return None

    def get_disease_summary(self, query_disease=None, query_meddra=None, 
            outside=False):
        """
        Return a summary of registered diseases and counts. With no args, will 
        return a list of all diseases and counts as a dict. One can also limit 
        output to a list of diseases or meddra codes and get counts for those 
        only. 

        Args:
            query_disease (list): List of diseases to filter on.
            query_meddra   (list): List of MEDDRA codes to filter on.
            outside (bool): Include patients registered under outside assay
                initiative in counts. DEFAULT: False

        Returns:
            dict: Dictionary of disease(s) and counts in the form of: ::

            {meddra_code : (ctep_term, count)}

        Examples:
            >>> data.get_disease_summary(query_meddra=['10006190'])
            {'10006190': (u'Invasive breast carcinoma', 605)}

            >>> data.get_disease_summary(query_disease=['Invasive breast carcinoma'])
            {u'10006190': ('Invasive breast carcinoma', 605)} 

            >>> data.get_disease_summary(query_meddra=[10006190,10024193,10014735])
            {'10006190': (u'Invasive breast carcinoma', 605),
             '10014735': (u'Endometrioid endometrial adenocarcinoma', 111),
              '10024193': (u'Leiomyosarcoma (excluding uterine leiomyosarcoma)', 55)}
            
        """
        disease_counts = defaultdict(int)
        results = defaultdict(list)

        for psn in self.data.values():
            if outside is False and 'OUTSIDE' in psn['source']:
                continue

            # Skip the registered but not yet biopsied patients.
            if psn['meddra_code'] == 'null': 
                continue
            disease_counts[psn['meddra_code']] += 1

        if query_meddra:
            if isinstance(query_meddra, list) is False:
                sys.stderr.write('ERROR: arguments to get_disease_summary() '
                    'must be lists!\n') 
                return None
            for q in query_meddra:
                q = str(q)
                if q in disease_counts:
                    results[q] = (self._disease_db[q], disease_counts[q])
                else:
                    sys.stderr.write('MEDDRA code "%s" was not found in the '
                        'MATCH study dataset.\n' % q)
        elif query_disease:
            if isinstance(query_disease, list) is False:
                sys.stderr.write('ERROR: arguments to get_disease_summary() '
                    'must be lists!\n') 
                return None
            for q in query_disease:
                    q = str(q)
                    meddra = next((meddra for meddra, term in self._disease_db.items() if q == term), None)
                    if meddra is not None:
                        results[meddra] = (q, disease_counts[meddra])
                    else:
                        sys.stderr.write('CTEP Term "%s" was not found in the '
                            'MATCH study dataset.\n' % q)
        else:
            for meddra in self._disease_db:
                results[meddra] = (self._disease_db[meddra], 
                    disease_counts[meddra])

        if results:
            return dict(results)
        else:
            return None

    def get_histology(self, psn=None, msn=None, bsn=None, outside=False, 
            no_disease=False, ret_type='ctep_term'):
        """
        Return dict of PSN:Disease for valid biopsies.  Valid biopsies are 
        defined as being only `Passed`,  and can not be `Failed`, `No Biopsy`,
        or outside assay biopsies at this time.

        Args:
            psn (str): Optional PSN or comma separated list of PSNs on which 
                to filter data.

            bsn (str): Optional BSN or comma separated list of BSNs on which 
                to filter data.
                
            msn (str): Optional MSN or comma separated list of MSNs on which 
                to filter data.

            outside (bool): Also include outside assay data. Default: ``False``

            no_disease (bool): Return all data, even if there is no disease 
                indicated for the patient specimen. Default: ``False``

            ret_type (str): Type of data to return.  Can only either be one
                of 'ctep_term' or 'meddra_code'

        Returns:
            dict: Dict of ID : Disease mappings. If no match for input ID, 
            returns ``None``.

        Examples: 
            >>> data.get_histology(psn='11352')
            {'PSN11352': 'Serous endometrial adenocarcinoma'}

            >>> data.get_histology(psn='12104,12724,12948,13367,15784')
            WARN: The following specimens were filtered from the output due to 
            either the "outside" or "no_disease" filters:
	         12724,15784
            {'PSN12104': 'CNS primary tumor, NOS',
             'PSN12948': 'Cholangiocarcinoma, intrahepatic and extrahepatic '
                         'bile ducts (adenocarcinoma)',
             'PSN13367': 'Adenocarcinoma of the pancreas'}

            >>> data.get_histology(msn='12104,12724,12948,13367,15784')
            {
                'MSN15748': None, 
                'MSN12104': 'Colorectal cancer, NOS', 
                'MSN12724': 'Squamous cell carcinoma of the anus', 
                'MSN12948': 'Adenocarcinoma of the colon', 
                'MSN13367': 'Invasive breast carcinoma'
            }

            >>> data.get_histology(msn=3060)
            No result for id MSN3060
            {'MSN3060': None}

            >>> data.get_histology(psn='11352', ret_type='meddra_code')
            {'PSN11352' : '10033700'}

        """

        # Don't want to allow for mixed query types. So, number of None args 
        # must be > 2 or else user incorrectly entered more than one arg type.
        count_none = sum((x is None for x in (psn, msn, bsn)))
        if count_none < 2:
            sys.stderr.write('Error: Mixed query types detected. Please only '
                'use one type of query ID in this function.\n')
            return None

        if ret_type not in ('ctep_term', 'meddra_code'):
            sys.stderr.write('Error: Choose either "ctep_term" or "meddra_code"'
                ' as the ret_type.')
            return None

        # Prepare an ID list dict if one is provided. Need some special mapping 
        # and whatnot before we can pass it.
        query_list = {} # always psn : original ID (ex: {'10098':'T-16-000987'})
        output_data = {}

        if psn:
            # make set with and without IDs
            psn_list = [x.lstrip('PSN') for x in str(psn).split(',')]
            psn_list2 = map(lambda x: self.__format_id('add', psn=x), psn_list)
            query_list = dict(zip(psn_list, psn_list2))

            for p in query_list:
                if p not in self.data:
                    output_data[query_list[p]] = None
        
        elif msn:
            msn_list = [self.__format_id('add', msn=x) for x in str(msn).split(',')]
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
            psn_list2 = map(lambda x: self.__format_id('add', psn=x), psn_list)
            query_list = dict(zip(psn_list, psn_list2))

        # Iterate through the valid PSNs and get results if they pass filters.
        filtered = []
        for psn in query_list:
            if psn in self.data:
                # If the no disease filter is turned on (i.e. False) don't 
                # output "No Biopsy" results.
                if outside is False and 'OUTSIDE' in self.data[psn]['source']:
                    filtered.append(psn)
                    continue
                if no_disease is False and self.data[psn]['ctep_term']=='null':
                    filtered.append(psn)
                    continue

                output_data[query_list[psn]] = self.data[psn][ret_type]

        if filtered: 
            if len(filtered) > 10:
                sys.stderr.write('WARN: there were %i records that were '
                    'filtered from the output due to either\nthe "outside" '
                    'or "no_disease" option.\n' % len(filtered))
            else:
                sys.stderr.write('WARN: The following specimens were filtered '
                    'from the output due to either\nthe "outside" or '
                    '"no_disease" filters:\n')
                sys.stderr.write('\t%s\n' % ','.join(filtered))
        return output_data

    def find_variant_frequency(self, query, query_patients=None):
        """
        Find and return variant hit rates.

        Based on an input query in the form of a `variant_type : gene` dict,
        where the gene value can be a list of genes, output a list of patients
        that had hits in those gene with some disease and variant information. 

        The return val will be unique to a patient. So, in the cases where we 
        have multiple biopsies from the same patient (an intitial and 
        progression re-biopsy for example), we will only get the union of the 
        two sets, and duplicate variants will not be output.  This will prevent
        the hit rate from getting over inflated.  Also, there is no sequence 
        specific information output in this version (i.e. no VAF, Coverage, etc.
        ). Sequence level information for a call can be obtained from the 
        method ``get_variant_report()``.

        Args:
            query (dict): Dictionary of variant_type: gene mappings where: ::

                -  variant type is one or more of 'snvs', 'indels', 'fusions',
                    'cnvs'
                -  gene is a list of genes to query.

            query_patients (list): List of patients for which we want to obtain 
                data. 

        Returns:
            dict: 
            Return a dict of matching data with disease and MOI 
            information, along with a count of the number of patients 
            queried and the number of biopsies queried.
        
        Examples:
            >>> query={'snvs' : ['BRAF','MTOR'], 'indels' : ['BRAF', 'MTOR']}
            >>> find_variant_frequency(query)
            >>> # Note the result list is too long to print here.

            >>> query = {'snvs':['EGFR'], 'indels':['EGFR']}
            >>> data.find_variant_frequency(query, [15232])[0]
            {'15232': {'bsns': ['T-17-001423'],
            'disease': 'Lung adenocarcinoma',
            'mois': [{'alleleFrequency': 0.191596,
                      'alternative': 'T',
                      'amoi': ['EAY131-A(e)', 'EAY131-E(i)'],
                      'chromosome': 'chr7',
                      'confirmed': True,
                      'exon': '20',
                      'function': 'missense',
                      'gene': 'EGFR',
                      'hgvs': 'c.2369C>T',
                      'identifier': 'COSM6240',
                      'oncominevariantclass': 'Hotspot',
                      'position': '55249071',
                      'protein': 'p.Thr790Met',
                      'reference': 'C',
                      'transcript': 'NM_005228.3',
                      'type': 'snvs_indels'},
                     {'alleleFrequency': 0.748107,
                      'alternative': '-',
                      'amoi': ['EAY131-A(i)'],
                      'chromosome': 'chr7',
                      'confirmed': True,
                      'exon': '19',
                      'function': 'nonframeshiftDeletion',
                      'gene': 'EGFR',
                      'hgvs': 'c.2240_2257delTAAGAGAAGCAACATCTC',
                      'identifier': 'COSM12370',
                      'oncominevariantclass': 'Hotspot',
                      'position': '55242470',
                      'protein': 'p.Leu747_Pro753delinsSer',
                      'reference': 'TAAGAGAAGCAACATCTC',
                      'transcript': 'NM_005228.3',
                      'type': 'snvs_indels'}],
            'msns': ['MSN52258'],
            'psn': '15232'}}

        """
        results = {} 
        plist = [] 

        # Queue up a patient's list in case you just want to find data for one 
        # patient.
        if query_patients:
            # if type(query_patients) is not list:
            if isinstance(query_patients, list) is False:
                sys.stderr.write('ERROR: You must input the query patients as '
                    'a list, even if only inputting one!\n')
                return None
            pt_list = [self.__format_id('rm', psn=x) for x in query_patients]
        else:
            pt_list = self.data.keys()

        for patient in pt_list:
            # Skip no biopsy and all outside biospy cases.  For outside assay 
            # cases, we don't want to consider any of it since the confirmation 
            # data will skew results.
            if self.data[patient]['biopsies'] == 'No_Biopsy':
                continue
            elif 'OUTSIDE' in self.data[patient]['source']:
                continue
            else:
                matches = []
                for biopsy in self.data[patient]['biopsies']:
                    b_record = self.data[patient]['biopsies'][biopsy]

                    # Get rid of Outside assays biopsies (but not outside 
                    # confirmation) and Failed biopsies.
                    if b_record['biopsy_status'] != "Pass":
                        continue
                    biopsies = []

                    if (
                        b_record['ngs_data'] 
                        and 'mois' in b_record['ngs_data']
                    ):
                        plist.append(patient)
                        biopsies.append(biopsy)
                        input_data = b_record['ngs_data']['mois']

                        if (
                            'snvs' in query 
                            and 'singleNucleotideVariants' in input_data
                        ):
                            matches += self.__get_var_data_by_gene(
                                input_data['singleNucleotideVariants'],
                                query['snvs']
                            )

                        if 'indels' in query and 'indels' in input_data:
                            matches += self.__get_var_data_by_gene(
                                input_data['indels'], 
                                query['indels']
                            )

                        if (
                            'cnvs' in query 
                            and 'copyNumberVariants' in input_data
                        ):
                            matches += self.__get_var_data_by_gene(
                                input_data['copyNumberVariants'],
                                query['cnvs']
                            )

                        if (
                            'fusions' in query 
                            and 'unifiedGeneFusions' in input_data
                        ):
                            # input_data['unifiedGeneFusions'] is a list
                            filtered_fusions = []
                            skip=('Novel', 'Non-Targeted')
                            for fusion in input_data['unifiedGeneFusions']:
                                if any(x in fusion['identifier'] for x in skip):
                                    continue
                                else:
                                    filtered_fusions.append(fusion)
                            matches += self.__get_var_data_by_gene(
                                filtered_fusions,query['fusions']
                            )

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
        .. _get_variant_report:

        Input a PSN or MSN **(preferred!)** and return a list of dicts of 
        variant call data.

        Since there can be more than one MSN per patient, one will get a more 
        robust result by querying on a MSN.  That is, only one variant report 
        per MSN can be generated and the results, then, will be clear.  In the 
        case of querying by PSN, a variant report for each MSN under that PSN, 
        assuming that the MSN is associated with a variant report, will be 
        returned.

        Args:
           msn (str):  MSN for which a variant report should be returned.
           psn (str):  PSN for which the variant reports should be returned.

        Returns:
           dict: List of dicts of variant results. ::

           msn: { 
               'singleNucleotideVariants' : [{var_data}], 
               'copyNumberVariants' : [{var_data},{var_data}], etc. 
           }

        Examples:
            >>> data.get_variant_report(psn=10005)
            {'MSN3111': {'unifiedGeneFusions': [{'amoi': None,
                                     'annotation': 'COSF1232',
                                     'confirmed': True,
                                     'driverGene': 'RET',
                                     'driverReadCount': 7121,
                                     'gene': 'RET',
                                     'identifier': 'KIF5B-RET.K15R12.COSF1232',
                                     'partnerGene': 'KIF5B',
                                     'type': 'fusions'}]}}

            >>> data.get_variant_report(msn=35733)
            {
                'MSN35733': {
                    'singleNucleotideVariants': [
                        {
                            'alleleFrequency': 0.570856,
                            'alternative': 'T',
                            'alternativeAlleleObservationCount': 3190,
                            'amoi': ['EAY131-Z1I(i)'],
                            'chromosome': 'chr13',
                            'confirmed': True,
                            'exon': '25',
                            'flowAlternativeAlleleObservationCount': '1140',
                            'flowReferenceAlleleObservations': '177',
                            'function': 'nonsense',
                            'gene': 'BRCA2',
                            'hgvs': 'c.9382C>T',
                            'identifier': '.',
                            'oncominevariantclass': 'Deleterious',
                            'position': '32968951',
                            'protein': 'p.Arg3128Ter',
                            'readDepth': 5551,
                            'reference': 'C',
                            'referenceAlleleObservations': 456,
                            'transcript': 'NM_000059.3',
                            'type': 'snvs_indels'
                        }
                    ]
                }
            }

        """
        if msn:
            msn = self.__format_id('add', msn=msn)
            psn = self.__format_id('rm', psn=self.get_psn(msn=msn))

            for biopsy in self.data[psn]['biopsies'].values():
                if 'ngs_data' in biopsy and biopsy['ngs_data']['msn'] == msn:
                    formatted_msn = self.__format_id('add', msn=msn)
                    return {formatted_msn : biopsy['ngs_data']['mois']}
                else:
                    return None
        elif psn:
            # if we are searching by PSN, can get multiple reports. Print them 
            # all as a list.
            if not self._quiet:
                sys.stderr.write('WARN: Using a PSN can result in multiple reports,'
                    ' especially in cases where\nthere is more than one valid MSN '
                    'per PSN (like as in progression cases. It\nis recommended to '
                    'use a MSN for this method.\n')

            results = {}  
            psn = self.__format_id('rm', psn=psn)
            try:
                if not len(self.data[psn]['all_msns']) > 0:
                    sys.stderr.write('No variant report available for patient: '
                        '%s.\n' % psn)
                    return None
            except KeyError:
                sys.stderr.write('ERROR: Patient %s does not exist in the '
                    'database!\n' % psn)
                return None

            for biopsy in self.data[psn]['biopsies'].values():
                # Skip the outside assays biopsies since the variant reports 
                # are unreliable. Also have to skip outside confirmation cases 
                # now as the assay does not always cover the variants and now 
                # MATCHBox is including calls that are outside of our 
                # reportable range....a real mess!
                if 'Outside' in biopsy['biopsy_source']:
                    continue
                elif biopsy['ngs_data'] and 'mois' in biopsy['ngs_data']:
                    identifier = self.__format_id(
                        'add', 
                        msn=biopsy['ngs_data']['msn']
                    )
                    results[identifier] = biopsy['ngs_data']['mois']
            if results:
                return results
            else:
                return None

    def get_patient_ta_status(self, psn=None):
        """
        Input a PSN and return information about the treatment arm(s) to which
        they were assigned, if they were assigned to any arms. If no PSN is 
        passed to the function, return results for every PSN in the study.

        Args:
            psn (str): PSN string to query.

        Returns:
            dict: Dict of Arm IDs with last status.

        Examples:
            >>> data.get_patient_ta_status(psn=10837)
            {'EAY131-Z1A': 'FORMERLY_ON_ARM_OFF_TRIAL'}

            >>> data.get_patient_ta_status(psn=11889)
            {u'EAY131-IX1': u'FORMERLY_ON_ARM_OFF_TRIAL', 
             u'EAY131-I': u'COMPASSIONATE_CARE'}

            >>> data.get_patient_ta_status(psn=10003)
            {}

        """
        results = {}
        if psn:
            psn = self.__format_id('rm', psn=psn)
            if psn in self.data:
                return self.data[psn]['ta_arms']
            else:
                return None
        else:
            for p in self.data:
                results[p] = self.data[p]['ta_arms']
        return results 
    
    def get_patients_by_disease(self, histology=None, meddra_code=None, 
            outside=False):
        """
        Input a disease and return a list of patients that were registered with 
        that disease type. For histology query, we can do partial matching 
        based on the python ``in`` function. So, if one were to query `Lung 
        Adenocarcinoma`, `Lung` , `Lung Adeno`, or `Adeno`, all Lung 
        Adenocarinoma cases would be returned. It may be more robust to just 
        stick with MEDDRA codes as they would to be more precise 
        
        .. note:: 
            Simply inputting `Lung`, would also return `Non-small Cell Lung 
            Adenocarinoma`, `Squamous Cell Lung Adenocarcinoma`, etc, and 
            querying `Adeno` would return anything that had `adeno`. So, care 
            must be taken with the query, and secondary filtering may be 
            necessary. Querying based on MEDDRA codes is specific and only an 
            exact match will return results; **This is the preferred method.**

        Args:
            histology (str):  One of the CTEP shotname disease codes.
            meddra_code (str): A MEDDRA code to query rather than histology.
            outside (bool):   Include Outside Assays patients in the results.

        Returns:
            dict: Dict of Patient : Histology Mapping

        Examples:
            >>> data.get_patients_by_disease(histology='glioma')
            {'10512': 'Oligodendroglioma, NOS',
             '13496': 'Anaplastic oligodendroglioma',
             '13511': 'Anaplastic oligodendroglioma',
             '16124': 'Anaplastic oligodendroglioma',
             '16160': 'Anaplastic oligodendroglioma',
             '16248': 'Anaplastic oligodendroglioma'}

            We see here that Small Cell and Non-small cell get combined.

            >>> ret_list = data.get_patients_by_disease(
            ...     histology='Small cell lung cancer').values()
            >>> print('Total returned: {}'.format(len(ret_list)))
            102
            >>> print(set(ret_list))
            {'Small cell lung cancer', 'Non-small cell lung cancer, NOS'}

            Here we distinguish and only get the Non-small cell cases, by 
            using a MEDDRA code

            >>> meddra = utils.map_histology(
            ...    self._disease_db, 
            ...    histology='Non-small cell lung cancer, NOS')

            >>> data.get_patients_by_disease(meddra_code=meddra)
            {'10196': 'Non-small cell lung cancer, NOS',
             '10312': 'Non-small cell lung cancer, NOS',
             '10540': 'Non-small cell lung cancer, NOS',
             '11850': 'Non-small cell lung cancer, NOS',
             '11929': 'Non-small cell lung cancer, NOS',
             '12541': 'Non-small cell lung cancer, NOS',
             '12577': 'Non-small cell lung cancer, NOS',
             '12790': 'Non-small cell lung cancer, NOS',
             '12916': 'Non-small cell lung cancer, NOS',
             '13187': 'Non-small cell lung cancer, NOS',
             '13242': 'Non-small cell lung cancer, NOS',
             '13620': 'Non-small cell lung cancer, NOS',
             '14256': 'Non-small cell lung cancer, NOS',
             '15097': 'Non-small cell lung cancer, NOS',
             '15114': 'Non-small cell lung cancer, NOS',
             '16095': 'Non-small cell lung cancer, NOS',
             '16212': 'Non-small cell lung cancer, NOS',
             '16412': 'Non-small cell lung cancer, NOS',
             '16467': 'Non-small cell lung cancer, NOS',
             '16469': 'Non-small cell lung cancer, NOS',
             '16498': 'Non-small cell lung cancer, NOS',
             '16554': 'Non-small cell lung cancer, NOS'}

        """

        if not any(x for x in [histology, meddra_code]):
            sys.stderr.write("ERROR: You must input either a histology or "
                "meddra code to query!\n")
            return None

        results = {}
        if histology:
            for pt in self.data:
                if outside is False and 'OUTSIDE' in self.data[pt]['source']:
                    continue
                if histology.lower() in self.data[pt]['ctep_term'].lower():
                    results[pt] = self.data[pt]['ctep_term']
        elif meddra_code:
            for pt in self.data:
                if outside is False and 'OUTSIDE' in self.data[pt]['source']:
                    continue
                if meddra_code == self.data[pt]['meddra_code']:
                    results[pt] = self.data[pt]['ctep_term']
        return results

    def get_patients_by_arm(self, arm, outside=False):
        """
        Input an official NCI-MATCH arm identifier (e.g. `EAY131-A`) and return
        a set of patients that have ever qualified for the arm based on variant
        level data.  This not only includes patients `ON_TREATMENT_ARM`, but 
        also `FORMERLY_ON_ARM_OFF_TRIAL` and even `COMPASSIONATE_CARE`. Also, 
        since the variant call data is not always confirmable by the NCI-MATCH
        assay, and only those that are confirmed are "evaluable", all outside
        assay cases are removed from this list as well, unless explicity 
        requested at your own peril.

        Args:
            arm (str): One of the official NCI-MATCH arm identifiers.
            outside (bool): If set to ``True``, will also output outside assay
                cases in the cohort. DEFAULT: ``False``.

        Returns:
            list: List of tuples of patient, arm, and arm_status.

        Examples:
            >>> data.get_patients_by_arm(arm='EAY131-E', outside=True)
            [
                (u'11476', 'EAY131-E', u'OFF_TRIAL_DECEASED'), 
                (u'14343', 'EAY131-E', u'FORMERLY_ON_ARM_OFF_TRIAL'), 
                (u'10626', 'EAY131-E', u'ON_TREATMENT_ARM'), 
                (u'14256', 'EAY131-E', u'ON_TREATMENT_ARM'), 
                (u'16472', 'EAY131-E', u'FORMERLY_ON_ARM_OFF_TRIAL')
            ]

            .. note:: 
                we use default outside assay filter in this case.

            >>> data.get_patients_by_arm(arm='EAY131-E')
            [
                ('10626', 'EAY131-E', 'ON_TREATMENT_ARM'), 
                ('11476', 'EAY131-E', 'OFF_TRIAL_DECEASED'), 
                ('14256', 'EAY131-E', 'ON_TREATMENT_ARM'), 
                ('14343', 'EAY131-E', 'ON_TREATMENT_ARM')
            ]

        """
            
        results = []
        
        if arm not in self.arm_data.data:
            sys.stderr.write('ERROR: No such arm: {}!\n'.format(arm))
            return None

        for pt in self.data:
            if outside is False and 'OUTSIDE' in self.data[pt]['source']:
                continue
            if arm in self.data[pt]['ta_arms']:
                results.append((pt, arm, self.data[pt]['ta_arms'][arm]))
        return results

    @staticmethod
    def __map_ihc_results(ihc_data):
        # Set up a dict of assays now that we'll fill in since the number has 
        # changed over time, and it's good to have results for all assays.
        all_ihc_assays = {
            'RB' : None, 
            'MSH2' : None, 
            'MLH1' : None, 
            'PTEN' : None
        }
        return {x : ihc_data.get(x, None) for x in all_ihc_assays.keys()}

    def get_ihc_results(self, psn=None, msn=None, bsn=None, assays=None):
        """
        Get the IHC results for a patient.

        Input a PSN, MSN, or BSN and / or a set of IHC assays, and return a dict
        of data.

        .. note::
            Each MSN or BSN will have only one set of IHC results typically, 
            since newer results would overwrite the other ones.  However, there
            can be more than one BSN or MSN for a PSN, and so using a PSN for 
            this query is discouraged since you can get multiple results.

        Args:
            psn (str):  Query the data by PSN. 
            msn (str):  Query the data by MSN.
            bsn (str):  Query the data by BSN.
            assay (list): IHC assay for which we want to return results. If no 
                assay is passed, will return all IHC assay results.

        Returns:
            dict: Dict of lists containing the MSN and all IHC assays available 
            for the specimen.

        Examples:
            >>> data.get_ihc_results(msn='MSN30791')
            {'MSN30791': {'MLH1': u'POSITIVE',
                          'MSH2': u'POSITIVE',
                          'PTEN': u'POSITIVE',
                          'RB': u'ND'}}

            >>> data.get_ihc_results(bsn='T-16-002222', assays=['PTEN'])
            {u'MSN30791': {'PTEN': u'POSITIVE'}}

            >>> data.get_ihc_results(psn=10818)
            {'MSN12104': {'MLH1': 'POSITIVE',
                          'MSH2': 'POSITIVE',
                          'PTEN': 'POSITIVE',
                          'RB': 'ND'},
             'MSN51268': {'MLH1': 'POSITIVE',
                          'MSH2': 'POSITIVE',
                          'PTEN': 'POSITIVE',
                          'RB': 'ND'}}


        """

        if (len([y for y in [psn, msn, bsn] if y is not None]) > 1):
            sys.stderr.write("ERROR: Only enter one ID per query. We can not "
               "look up an MSN and PSN at the same time, for example.\n")
            return None

        results = defaultdict(dict)

        if msn or bsn:
            if msn:
                psn = self.get_psn(msn=msn)
                if psn is None:
                    sys.stderr.write('ERROR: No such MSN "%s" in the '
                        'dataset!\n' % msn)
                    return None
                bsn = self.get_bsn(msn=msn)[0]
            elif bsn:
                psn = self.get_psn(bsn=bsn)
                if psn is None:
                    sys.stderr.write('ERROR: No such BSN "%s" in the '
                        'dataset!\n' % bsn)
                    return None
                msn = self.get_msn(bsn=bsn)[0]
            
            record = self.get_patient_meta(psn=psn, val='biopsies')
            results[msn] = self.__map_ihc_results(record[bsn]['ihc'])

        # If we're working with a PSN, there can be multiple results, so we
        # have to parse the all and build a total set.
        elif psn:
            record = self.get_patient_meta(psn=psn, val='biopsies')
            bsn_list = self.get_bsn(psn=psn)
            for b in bsn_list:
                msn = self.get_msn(bsn=b)[0]
                results[msn] = self.__map_ihc_results(record[b]['ihc'])
        else:
            sys.stderr.write("ERROR: You must input an MSN, BSN, or PSN to "
                " query!\n")
            return None

        if assays:
            for m in results:
                filtered_results = {a : results[m].get(a, None) for a in assays}
                results[m] = filtered_results

        return dict(results)
    
    def get_biopsy_info(self, *, bsn, term=None):
        """
        Collect some metadata info about a biopsy and return a dict of all data,
        or just a single term:value entry.

        Args:
            bsn (str):  BSN for which we want to get data.
            term (str): Optional metadata value to filter on.

        Returns:
            dict: Dict of results matching the BSN and term (if entered).

        Examples:

            >>> self.get_biopsy_info(bsn='T-16-000029')
            {'T-16-000029': {
                'biopsy_source': 'Initial', 
                'biopsy_status': 'Pass'
                }
            }
            
            >>> self.get_biopsy_info(bsn='T-16-000029', term='biopsy_source')
            {'T-16-000029': {'biopsy_source': 'Initial'}}

            >>> self.get_biopsy_info(bsn='T-16-000029', term='foo')
            None
            ERROR: No such term 'foo' in data structure!
        
        """
        metaval = defaultdict(dict)
        wanted_data = ('biopsy_source', 'biopsy_status')
        psn = self.__format_id('rm', psn=self.get_psn(bsn=bsn))
        biopsy_record = self.data[psn]['biopsies'][bsn]
        if term:
            ret  = utils.get_vals(biopsy_record, term)[0]
            if ret == '---':
                sys.stderr.write("ERROR: No such term '%s' in data structure! "
                    % term)
                return None
            metaval[term] = ret
        else:
            for t in wanted_data:
                metaval[t] = utils.get_vals(biopsy_record, t)[0]
        return {bsn : dict(metaval)}
