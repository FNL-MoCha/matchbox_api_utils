# -*- coding: utf-8 -*-
# TODO:
#    - get arm by gene lookup.
import sys
import json
from collections import defaultdict
from pprint import pprint as pp

from matchbox_api_utils import utils
from matchbox_api_utils import matchbox_conf
from matchbox_api_utils.matchbox import Matchbox


class TreatmentArms(object):
    """

    NCI-MATCH Treatment Arms and aMOIs Class

    """

    def __init__(self, config_file=None, url=None, creds=None, json_db='sys_default',
            load_raw=None, make_raw=False):
        """

        Generate a MATCHBox treatment arms object that can be parsed and queried 
        downstream. 
        
        Can instantiate with either a config JSON file, which contains the url, 
        username, and password information needed to access the resource, or by 
        supplying the individual arguments to make the connection.  This class
        will call the Matchbox class in order to make the connection and deploy 
        the data.

        Can do a live query to get data in real time, or load a MATCHBox JSON file 
        derived from the matchbox_json_dump.py script that is a part of the package. 
        Since data in MATCHBox is relatively static these days, it's preferred to 
        use an existing JSON DB and only periodically update the DB with a call 
        to the aforementioned script.

         Args:
               config_file (file): Custom config file to use if not using system 
                                   default.
               url (str):          MATCHBox API URL to use.
               creds (dict):       MATCHBox credentials to use. Needs to be in the 
                                   form of:

                            {'username':<username>,'password':<password>}

               json_db (file):     MATCHbox processed JSON file containing the 
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
        self._json_db = json_db
        self._load_raw = load_raw
        self.db_date = utils.get_today('long')
        self._config_file = config_file
        
        if not self._url:
            self._url = utils.get_config_data(self._config_file, 'arms_url')
        
        if not self._creds:
            self._creds = utils.get_config_data(self._config_file, 'creds')
        
        if self._json_db == 'sys_default':
            self._json_db = utils.get_config_data(self._config_file, 
                'ta_json_data')

        if make_raw:
            Matchbox(self._url,self._creds,make_raw='ta')
        elif self._load_raw:
            self.db_date,matchbox_data = utils.load_dumped_json(self._load_raw)
            self.data = self.make_match_arms_db(matchbox_data)
        elif self._json_db:
            self.db_date,self.data = utils.load_dumped_json(self._json_db)
        else:
            # make api call to get json data; load and present to self.data.
            matchbox_data = Matchbox(self._url,self._creds).api_data
            self.data = self.make_match_arms_db(matchbox_data)
        
        # Make a condensed aMOI lookup table too for running aMOIs rules.
        self.amoi_lookup_table = self.__gen_rules_table()

    def __str__(self):
        return json.dumps(self.data, sort_keys=True, indent=4)

    def __getitem__(self,key):
        return self.data[key]

    def __iter__(self):
        return self.data.itervalues()

    def ta_json_dump(self,amois_filename=None,ta_filename=None):
        """
        Dump the TreatmentArms data to a JSON file that can be easily loaded 
        downstream. We will make both the treatment arms object, as well as the 
        amois lookup table object.

        Args:
            amois_filename (str): Name of aMOI lookup JSON file. Default: 
                amoi_lookup_<datestring>.json
            ta_filename (str): Name of TA object JSON file Default: 
                ta_obj_<datestring>.json

        Returns:
            ta_obj_<date>.json
            amois_lookup_<date>.json

        """
        # sys.stdout.write('Writing MATCH aMOIs and Arms to JSON file.\n')
        if not amois_filename:
            amois_filename = 'amoi_lookup_' + utils.get_today('short') + '.json'
        if not ta_filename:
            ta_filename = 'ta_obj_' + utils.get_today('short') + '.json'

        utils.make_json(amois_filename, self.amoi_lookup_table)
        utils.make_json(ta_filename, self.data)

    def __retrive_data_with_keys(self, data, k1, k2):
        results = {}
        for elem in data:
            results[elem[k1]] = elem[k2]
        if results:
            return results
        else:
            return None

    def __gen_rules_table(self,arm_id = None):
        # wanted data struct:
            # 'hotspots' : {
                # 'hs_id' : [arm1, arm2, arm3],
                # 'hs_id' : [arma, armb, armc],
            # },
            # 'cnvs' : {
                # 'gene1' : [arm1, arm2],
                # 'gene2' : [arma, armb],
            # },
            # 'fusions' : {
                # 'fusion_id' : [arm1, arm2, arm3],
            # },
            # 'positional' : {
                # 'gene' : [ 'exon|function' : [arms]],
                # 'EGFR' : [ '19|nonframeshiftDeletion' : [ArmA]],
                # 'ERBB2' : [ '20|nonframeshiftInsertion' : [ArmB, ArmBX1]],
            # }
            # 'deleterious' : {
                 # 'gene' : [arms],
            # }
        rules_table = {
            'hotspot'     : defaultdict(list),
            'cnv'         : defaultdict(list), 
            'fusion'      : defaultdict(list),
            'deleterious' : defaultdict(list),
            'positional'  : defaultdict(list)
        }
        ie_flag = {'True' : 'i', 'False' : 'e'}

        for arm in self.data:
            amoi_data = self.data[arm]['amois']
            for var_type in rules_table:
                # non_hs mois
                if var_type in ('deleterious', 'positional') and amoi_data['non_hs'][var_type]:
                    for var,flag in amoi_data['non_hs'][var_type].items():
                        rules_table[var_type][var].append('{}({})'.format(
                            arm,ie_flag[str(flag)]))
                # All other mois
                elif amoi_data[var_type]:
                    for var,flag in amoi_data[var_type].items():
                        rules_table[var_type][var].append('{}({})'.format(
                            arm,ie_flag[str(flag)]))
        return rules_table

    def __parse_amois(self,amoi_data):
        # Getting a dict of amois with keys:
            # copyNumberVariants
            # geneFusions
            # indels
            # nonHotspotRules
            # singleNucleotideVariants

        parsed_amois = defaultdict(dict)

        wanted = {
            'singleNucleotideVariants' : 'hotspot',
            'indels'                   : 'hotspot',
            'copyNumberVariants'       : 'cnv',
            'geneFusions'              : 'fusion',
            'nonHotspotRules'          : 'non_hs'
        }

        for var in wanted:
            # Have to handle non-hs vars a bit differently.
            if var == 'nonHotspotRules':
                nhr_vars = {
                    'deleterious' : defaultdict(dict), 
                    'positional' : defaultdict(dict)
                }
                for elem in amoi_data[var]:
                    if elem['oncominevariantclass'] == 'Deleterious':
                        nhr_vars['deleterious'].update({elem['gene'] : elem['inclusion']})
                    else:
                        var_id = '|'.join([elem['gene'], elem['exon'], elem['function']])
                        nhr_vars['positional'].update({var_id : elem['inclusion']})
                parsed_amois[wanted[var]] = nhr_vars
            elif amoi_data[var]:
                results = { i['matchingId'] : i['inclusion'] for i in amoi_data[var]} 
                parsed_amois[wanted[var]].update(results)

        # Pad out data
        for i in wanted.values():
            if i not in parsed_amois:
                parsed_amois[i] = None
        return parsed_amois

    def make_match_arms_db(self,api_data):
        """
        Make a database of MATCH Treatment Arms.

        Read in raw API data and create pared down JSON structure that can be 
        easily parsed later one.  

        """
        arm_data = defaultdict(dict)
        for arm in api_data:
            arm_id = arm['id']
            # if arm_id != 'EAY131-Z1A':
                # continue

            arm_data[arm_id]['name']          = arm['name']
            arm_data[arm_id]['arm_id']        = arm['id']
            arm_data[arm_id]['gene']          = arm['gene']
            arm_data[arm_id]['drug_name']     = arm['targetName']
            arm_data[arm_id]['drug_id']       = arm['treatmentArmDrugs'][0]['drugId']
            arm_data[arm_id]['assigned']      = arm['numPatientsAssigned']
            arm_data[arm_id]['excl_diseases'] = self.__retrive_data_with_keys(arm['exclusionDiseases'],'shortName','medraCode')
            arm_data[arm_id]['ihc']           = self.__retrive_data_with_keys(arm['assayResults'],'gene','assayResultStatus')
            arm_data[arm_id]['amois']         = self.__parse_amois(arm['variantReport'])

        return arm_data
    
    @staticmethod
    def __validate_variant_dict(variant):
        # Validate that we have enough information to run the aMOIs rules 
        # processing. Will have different amounts of data depending on the source 
        # data. From MATCHBox we'll get less than user input, and going to need 
        #to account for that.
        acceptable_keys = ('type', 'gene', 'identifier', 'exon', 'function', 
            'oncominevariantclass')
        if 'type' in variant:
            if variant['type'] == 'cnvs':
                acceptable_keys = ('type','gene')
            elif variant['type'] == 'fusions':
                acceptable_keys = ('type', 'identifier')

        if not all(i in variant.keys() for i in acceptable_keys):
            sys.stderr.write("ERROR: Your variant dict is missing keys. You must "
                "input all keys:\n")
            sys.stderr.write("\t%s" % ', '.join(acceptable_keys))
            sys.stderr.write('\n')
            sys.exit(1)

    def map_amoi(self,variant):
        """
        Input a variant dict derived from some kind and return either an aMOI id 
        in the form of Arm(i|e). If variant is not an aMOI, returns 'None'.

        Args:
            variant (dict):  Variant dict to annotate.  Dict must have the following 
                             keys in order to be valid:

                                    - type : [snvs_indels, cnvs, fusions]
                                    - oncomineVariantClass
                                    - gene
                                    - identifier (i.e. variant ID (COSM476))
                                    - exon
                                    - function

                            Not all variant types will have meaningful data for 
                            these fields, and so fields may be padded with a null 
                            char (e.g. '.', '-', 'NA', etc.).

        Returns
            results (list):  Arm ID(s) with (i)nclusion or (e)xclusion information.

        Example:
            >>> variant = { 'type' : 'snvs_indels', 'gene' : 'BRAF', 'identifier' : 'COSM476', 'exon' : '15', 'function' : 'missense' , 'oncominevariantclass' : 'Hotspot' }
            ['EAY131-Y(e)', 'EAY131-P(e)', 'EAY131-N(e)', 'EAY131-H(i)']


        """
        self.__validate_variant_dict(variant)

        result = []
        if variant['type'] == 'snvs_indels':
            if variant['oncominevariantclass'] == 'Hotspot' and variant['identifier'] in self.amoi_lookup_table['hotspot']:
                result = self.amoi_lookup_table['hotspot'][variant['identifier']]

            elif variant['oncominevariantclass'] == 'Deleterious' and variant['gene'] in self.amoi_lookup_table['deleterious']:
                result = self.amoi_lookup_table['deleterious'][variant['gene']]

            else:
                for v in self.amoi_lookup_table['positional']:
                    if v.startswith(variant['gene']):
                        gene,exon,func = v.split('|')
                        if variant['exon'] == exon and variant['function'] == func:
                            result = self.amoi_lookup_table['positional'][v]

        elif variant['type'] == 'cnvs':
            if variant['gene'] in self.amoi_lookup_table['cnv']:
                result = self.amoi_lookup_table['cnv'][variant['gene']]

        elif variant['type'] == 'fusions':
            if variant['identifier'] in self.amoi_lookup_table['fusion']:
                result = self.amoi_lookup_table['fusion'][variant['identifier']]

        if result:
            return result
        else:
            return None

    def map_drug_arm(self,armid=None,drugname=None):
        """
        Input an Arm ID or a drug name, and retun a tuple of arm, drugname, and 
        ID. If no arm ID or drug name is input, will return a whole table of all 
        arm data.

        Args:
            armid (str): Offcial NCI-MATCH Arm ID in the form of EAY131-xxx (e.g. 
                EAY131-Z1A).
            drugname (str): Drug name as registered in the NCI-MATCH subprotocols.  
                Right now, required to have the full string (e.g. 'MLN0128(TAK-228)' 
                or, unfortunately, 'Sunitinib malate (SU011248 L-malate)'), but 
                will work on a regex to help make this easier later on.

        Returns:
            List of tuples or None.

        Example:
            >>> map_drug_arm(armid='EAY131-Z1A')
            (u'EAY131-Z1A', 'Binimetinib', u'788187')

        """
        if all(x is None for x in [armid,drugname]):
            return [(arm, self.data[arm]['drug_name'], self.data[arm]['drug_id']) for arm in sorted(self.data)]
        elif armid:
            if armid in self.data:     
                return (armid, self.data[armid]['drug_name'], 
                        self.data[armid]['drug_id'])
        elif drugname: 
            for arm in self.data:
                if self.data[arm]['drug_name'] == drugname:
                    return (self.data[arm]['arm_id'],drugname, 
                            self.data[arm]['drug_id'])
        return None
    
    def get_exclusion_disease(self,armid):
        """
        Input an arm ID and return a list of exclusionary diseases for the arm, 
        if there are any. Otherwise return None.

        Args:
            armid (str): Full identifier of the arm to be queried.

        Returns:
            List of exclusionary diseases for the arm, or None if there aren't any.

        Example:
            >>> get_exclusion_disease('EAY131-Z1A')
            [u'Melanoma', u'Colorectal Cancer']

            >>> get_exclusion_disease('EAY131-Y')
            None

        """
        if armid in self.data:
            if self.data[armid]['excl_diseases']:
                return self.data[armid]['excl_diseases'].keys()
            else:
                return None
        else:
            print('ERROR: No arm with ID: "%s" found in study!' % armid)
            return None

    def get_amois_by_arm(self, arm):
        """
        Input an arm identifier and return a list of aMOIs for the arm broken
        down by category.

        Args:
            arm (str):  Arm identifier to query

        Returns:
            
        """

        try:
            arm_data = self.data[arm]
        except KeyError:
            sys.stderr.write('ERROR: No arm with ID: "%s" found in study!\n' % arm)
            return None

        # Iterate through hotspots, cnvs, fusions, and non-hs aMOIs and generate
        # a list of tuples of data that can be printed easily later.

        #TODO: implement this.  For now just dump out dict.
        return dict(arm_data['amois'])

