# -*- coding: utf-8 -*-
import sys
import json
from collections import defaultdict

from matchbox_api_utils import utils
from matchbox_api_utils import matchbox_conf

from matchbox_api_utils.matchbox import Matchbox


class TreatmentArms(object):
    """

    **NCI-MATCH Treatment Arms and aMOIs Class**

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
        matchbox (str): Name of the MATCHBox system from which we want to get 
            data. This is required now that we have several systems to choose
            from. Valid names are ``adult``, ``ped``, and ``adult-uat`` for 
            those that have access to the adult MATCHBox test system. 
            **DEFUALT:** ``adult``.

        config_file (file): Custom config file to use if not using system 
            default.

        username (str): Username required for access to MATCHBox. Typically this
            is already present in the config file made during setup, but in
            cases where needed, it can be explicitly defined here. 

        password (str): Password associated with the user. As with the above 
            username argument, this is typically indicated in the config file
            generated during setup.

        json_db (file):     MATCHbox processed JSON file containing the whole 
            dataset. This is usually generated from ``'matchbox_json_dump.py'``. 
            The default value is ``'sys_default'`` which loads the default
            package data. If you wish you get a live call, set this variable to 
            `"None"`.

        load_raw (file): Load a raw API dataset rather than making a fresh call 
            to the API. This is intended for dev purpose only and may be 
            disabled later.

        make_raw (bool): Make a raw API JSON dataset for dev purposes only. This
            file will be used with the ``load_raw`` option.

        quiet (bool); If ``True``, supress module output debug, information,
            etc. messages.

    """

    def __init__(self, matchbox='adult', method='api', config_file=None, 
        username=None, password=None, json_db='sys_default', load_raw=None, 
        make_raw=None, quiet=True):

        # TODO:
        #    For now we'll just keep the old API call method since this is 
        #    working and easy to maintain. But, once we finish the other bits, 
        #    let's transition this over to a MongoDB call too.

        self._matchbox = matchbox
        self._json_db = json_db
        self.db_date = utils.get_today('long')
        self._quiet = quiet

        # Ensure we pass "ta" to Matchbox().
        if make_raw:
            make_raw = 'ta'
        
        if quiet is False:
            sys.stderr.write('[ INFO ]  Loading Treatment Arm data from '
                'MATCHBox: %s\n' % self._matchbox)
        self._config_data = matchbox_conf.Config(self._matchbox, method, 
            config_file)


        if username:
            if method == 'mongo':
                self._config_data.put_config_item('mongo_user', username)
            else:
                self._config_data.put_config_item('username', username)
        if password:
            if method == 'mongo':
                self._config_data.put_config_item('mongo_pass', password)
            else:
                self._config_data.put_config_item('password', password)

        if self._json_db == 'sys_default':
            self._json_db = self._config_data.get_config_item('ta_json_data')

        # Loading a pre-made Raw MB dump
        if load_raw:
            if self._quiet is False:
                sys.stderr.write('\n  ->  Starting from a raw TA JSON Obj\n')
            self.db_date, matchbox_data = utils.load_dumped_json(load_raw)
            self.data = self.make_match_arms_db(matchbox_data)

        # Loading a MB parsed DB
        elif self._json_db:
            if make_raw:
                sys.stderr.write("ERROR: You can not load a processed JSON DB "
                    "*and* ask to make a raw \nDB. You should set the 'json_db' "
                    "argument to `False`.\n")
                return None

            self.db_date, self.data = utils.load_dumped_json(self._json_db)
            if self._quiet is False:
                sys.stderr.write('\n  ->  Starting from a processed TA JSON '
                    'Object.\n')
                sys.stderr.write('\n  ->  JSON database object date: '
                    '%s\n' % self.db_date)

        # Making a live query
        else:
            # make api call to get json data; load and present to self.data.
            if self._quiet is False:
                sys.stderr.write('  ->  Starting from a live MB instance.\n')
            if method == 'api':
                self._config_data.put_config_item(
                    'url', 
                    '%s%s' % (
                        self._config_data.get_config_item('baseurl'),
                        'treatment_arms'
                    )
                )

            params = {'active' : True}
            matchbox_data = Matchbox(
                method=method,
                mongo_collection='treatmentArms',
                config=self._config_data,
                params=params, 
                make_raw=make_raw,
                quiet=self._quiet,
            ).api_data
            self.data = self.make_match_arms_db(matchbox_data)
        
        # Make a condensed aMOI lookup table too for running aMOIs rules.
        self.amoi_lookup_table = self.__gen_rules_table()

    def __str__(self):
        return utils.print_json(self.data)

    def __repr__(self):
        return '%s: %s' % (self.__class__, self.__dict__)

    def __getitem__(self,key):
        return self.data[key]

    def __iter__(self):
        return self.data.itervalues()

    def ta_json_dump(self, amois_filename=None, ta_filename=None):
        """
        Dump the TreatmentArms data to a JSON file that can be easily loaded 
        downstream. We will make both the treatment arms object, as well as the 
        amois lookup table object.

        Args:
            amois_filename (str): Name of aMOI lookup JSON file. **Default:**
                `amoi_lookup_<datestring>.json`

            ta_filename (str): Name of TA object JSON file **Default:**  
                `ta_obj_<datestring>.json`

        Returns:
            json: 
                ta_obj_<date>.json
                amois_lookup_<date>.json

        """
        if not amois_filename:
            amois_filename = 'amoi_lookup_' + utils.get_today('short') + '.json'
        if not ta_filename:
            ta_filename = 'ta_obj_' + utils.get_today('short') + '.json'

        utils.make_json(outfile=amois_filename, data=self.amoi_lookup_table)
        utils.make_json(outfile=ta_filename, data=self.data)

    @staticmethod
    # XXX
    def __retrieve_data_with_keys(data, k1, k2):
        results = {}
        for elem in data:
            results[elem[k1]] = elem[k2]
        if results:
            return results
        else:
            return None

    def __gen_rules_table(self, arm_id = None):
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
                if var_type in ('deleterious', 'positional'):
                    if amoi_data['non_hs'][var_type]:
                        for var, flag in amoi_data['non_hs'][var_type].items():
                            rules_table[var_type][var].append('{}({})'.format(
                                arm, ie_flag[str(flag)]))
                # All other mois
                elif amoi_data[var_type]:
                    for var, flag in amoi_data[var_type].items():
                        rules_table[var_type][var].append('{}({})'.format(
                            arm, ie_flag[str(flag)]))
        return rules_table

    def __parse_amois(self, amoi_data):
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
                    if 'oncominevariantclass' in elem:
                        if elem['oncominevariantclass'] == 'Deleterious':
                            nhr_vars['deleterious'].update(
                                {elem['gene'] : elem['inclusion']}
                            )
                    else:
                        var_id = '|'.join(
                            [elem['gene'], elem['exon'], elem['function']]
                        )
                        nhr_vars['positional'].update({var_id : elem['inclusion']})
                parsed_amois[wanted[var]] = nhr_vars

            # Rest of variant classes
            elif amoi_data[var]:
                # Now we have the unreliable and random "NOVEL" variants from
                # outside labs.  Skip all of these since you can't do a 
                # uniform analysis with the data. As an idea of how unreliable
                # this all is, the "metadata", "variantSource", etc. info isn't
                # even in every variant entry.  This database is a mess!
                for entry in amoi_data[var]:
                    try:
                        source = entry['metadata']['variantSource']
                    except KeyError:
                        # Not all entries have this information for some reason!
                        # Let's just assume it's not Novel or whatever.
                        source = None

                    if source == 'NOVEL':
                        continue
                    else:
                        parsed_amois[wanted[var]].update(
                            {entry['identifier'] : entry['inclusion']}
                        )
        # Pad out data
        for i in wanted.values():
            if i not in parsed_amois:
                parsed_amois[i] = None
        return parsed_amois

    def make_match_arms_db(self, api_data):
        """
        **Make a database of MATCH Treatment Arms** 

        Read in raw API data and create pared down JSON structure that can be 
        easily parsed later one.  

        Args:
            api_data (json): Entire raw MATCHBox API retrieved dataset.

        Returns:
            json: All Arm data.

        """
        arm_data = defaultdict(dict)
        for arm in api_data:
            arm_id = arm['treatmentArmId']
            # if arm_id != 'EAY131-H':
                # continue
            arm_data[arm_id]['name']      = arm['name']
            arm_data[arm_id]['target']    = arm.get('gene', 'UNK')
            arm_data[arm_id]['arm_id']    = arm_id
            arm_data[arm_id]['drug_name'] = arm['targetName']
            arm_data[arm_id]['drug_id']   = arm['treatmentArmDrugs'][0]['drugId']
            arm_data[arm_id]['assigned']      = arm['numPatientsAssigned']
            arm_data[arm_id]['excl_diseases'] = self.__retrieve_data_with_keys(
                arm['exclusionDiseases'], 'ctepCategory', '_id')
            arm_data[arm_id]['ihc']           = self.__retrieve_data_with_keys(
                arm['assayResults'], 'gene', 'assayResultStatus')
            arm_data[arm_id]['amois'] = self.__parse_amois(arm['variantReport'])
            arm_data[arm_id]['status'] = arm['treatmentArmStatus']
            
        return arm_data
    
    @staticmethod
    def __validate_variant_dict(variant):
        # Validate that we have enough information to run the aMOIs rules 
        # processing. Will have different amounts of data depending on the
        # source data. From MATCHBox we'll get less than user input, and going
        # to need to account for that.
        acceptable_keys = ('type', 'gene', 'identifier', 'exon', 'function', 
            'oncominevariantclass')
        if 'type' in variant:
            if variant['type'] == 'cnvs':
                acceptable_keys = ('type', 'identifier')
            elif variant['type'] == 'fusions':
                acceptable_keys = ('type', 'identifier')

        if not all(i in variant.keys() for i in acceptable_keys):
            sys.stderr.write("ERROR: Your variant dict is missing keys. You "
                "must input all keys:\n")
            sys.stderr.write("\t%s" % ', '.join(acceptable_keys))
            sys.stderr.write('\n')
            return None

    def map_amoi(self, variant):
        """
        Input a variant dict derived from some kind and return either an aMOI 
        id in the form of Arm(i|e). If variant is not an aMOI, returns 
        ``'None'``.

        Args:
            variant (dict):  Variant dict to annotate.  Dict must have the 
                following keys in order to be valid: ::

                    - type : [snvs_indels, cnvs, fusions]
                    - oncominevariantclass
                    - gene
                    - identifier (i.e. variant ID (COSM476))
                    - exon
                    - function

                Not all variant types will have meaningful data for these 
                fields, and so fields may be padded with a null char (e.g. 
                '.', '-', 'NA', etc.).

        Returns
            list:  
            Arm ID(s) with (i)nclusion or (e)xclusion information, or ``None``
            if the variant is not an aMOI.

        Examples:
            >>> variant = { 
                'type' : 'snvs_indels', 
                'gene' : 'BRAF', 
                'identifier' : 'COSM476', 
                'exon' : '15', 
                'function' : 'missense' , 
                'oncominevariantclass' : 'Hotspot' 
            }
            self.map_amoi(variant)
            ['EAY131-Y(e)', 'EAY131-P(e)', 'EAY131-N(e)', 'EAY131-H(i)']

            >>> variant = { 
                'type' : 'snvs_indels', 
                'gene' : 'TP53', 
                'identifier' : 'COSM10660', 
                'exon' : '-', 
                'function' : 'missense' , 
                'oncominevariantclass' : '-' 
            }
            self.map_amoi(variant)
            None

        """

        self.__validate_variant_dict(variant)

        result = []
        if variant['type'] == 'snvs_indels':
            if (
                variant['oncominevariantclass'] == 'Hotspot' 
                or variant['identifier'] in self.amoi_lookup_table['hotspot']
            ):
                result=self.amoi_lookup_table['hotspot'][variant['identifier']]

            elif (
                variant['oncominevariantclass'] == 'Deleterious' 
                and variant['gene'] in self.amoi_lookup_table['deleterious']
            ):
                result = self.amoi_lookup_table['deleterious'][variant['gene']]

            else:
                for v in self.amoi_lookup_table['positional']:
                    if v.startswith(variant['gene']):
                        gene,exon,func = v.split('|')
                        if (
                            variant['exon'] == exon 
                            and variant['function'] == func
                        ):
                            result = self.amoi_lookup_table['positional'][v]

        elif variant['type'] == 'cnvs':
            # Sometimes the MATCHBox team is inserting these data as "gene" (
            # the way it was originally intended!) and sometimes it's as 
            # "identifier".  Need to be able to handle both.
            if variant['gene'] in ('-', '.', None, 'null', ''):
                variant['gene'] = variant['identifier']

            if variant['gene'] in self.amoi_lookup_table['cnv']:
                result = self.amoi_lookup_table['cnv'][variant['gene']]

        elif variant['type'] == 'fusions':
            if variant['identifier'] in self.amoi_lookup_table['fusion']:
                result = self.amoi_lookup_table['fusion'][variant['identifier']]

        if result:
            return sorted(result)
        else:
            return None

    def map_drug_arm(self, armid=None, drugname=None, drugcode=None):
        """
        Input an Arm ID or a drug name, and return a tuple of arm, drugname,
        and ID. 

        Args:
            armid (str): Offcial NCI-MATCH Arm ID in the form of `EAY131-xxx`
                (e.g. 'EAY131-Z1A').

            drugname (str): Drug name as registered in the NCI-MATCH 
                subprotocols. Right now, required to have the full string (e.g.
                'MLN0128(TAK-228)' or, unfortunately, 'Sunitinib malate 
                (SU011248 L-malate)'), but will work on a regex to help make 
                this easier later on.

            drugcode (str): Use the 6-digit drug code to pull results.

        .. note::
            Note that using the ``drugname`` or ``drugcode`` option may return
            more than one result as we can have more than one arm per drug.

        Returns:
            list: List of tuples or ``None``.

        Examples:
            >>> map_drug_arm(armid='EAY131-Z1A')
            (u'EAY131-Z1A', 'Binimetinib', u'788187')

            >>> map_drug_arm(drugname='Afatinib')
            [('EAY131-A', 'Afatinib', '750691'),
             ('EAY131-B', 'Afatinib', '750691'),
             ('EAY131-BX1', 'Afatinib', '750691')]

            >>> map_drug_arm(drugcode='750691')
            [('EAY131-A', 'Afatinib', '750691'),
             ('EAY131-B', 'Afatinib', '750691'),
             ('EAY131-BX1', 'Afatinib', '750691')]

            >>> map_drug_arm(drugname='Tylenol')
            None

        """

        if all(x is None for x in [armid, drugname, drugcode]):
            sys.stderr.write('ERROR: No Arm ID, Drugname, or Drug Code info '
                'entered. Need to specify something to lookup!\n')
            return None
        elif armid:
            if armid in self.data:     
                return (armid, self.data[armid]['drug_name'], 
                        self.data[armid]['drug_id'])
        elif drugname or drugcode: 
            results = [] 
            for arm in self.data:
                if drugname and self.data[arm]['drug_name'] != drugname:
                    continue
                elif drugcode and self.data[arm]['drug_id'] != drugcode:
                    continue
                results.append(
                    (self.data[arm]['arm_id'], self.data[arm]['drug_name'], 
                    self.data[arm]['drug_id']))
            if not results:
                results = None
            return results
        return None
    
    def get_exclusion_disease(self, armid):
        """
        Input an arm ID and return a list of exclusionary diseases for the arm, 
        if there are any. Otherwise return ``None``.

        Args:
            armid (str): Full identifier of the arm to be queried.

        Returns:
            list: List of exclusionary diseases for the arm, or ``None`` if 
            there aren't any.

        Example:
            >>> self.get_exclusion_disease('EAY131-Z1A')
            ['Melanoma']

            >>> self.get_exclusion_disease('EAY131-Y')
            None

            >>> self.get_exclusion_disease('EAY131-A')
            ['Bronchioloalveolar carcinoma',
             'Lung adenocar. w/ bronch. feat.',
             'Lung adenocarcinoma',
             'Non-small cell lung cancer, NOS',
             'Small Cell Lung Cancer',
             'Squamous cell lung carcinoma']

        """
        if armid in self.data:
            excl_diseases = self.data[armid].get('excl_diseases', None)
            if excl_diseases is not None:
                return list(excl_diseases.keys())
            else:
                return excl_diseases
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
            dict: All aMOIs indicated for an arm.

        """

        try:
            arm_data = self.data[arm]
        except KeyError:
            sys.stderr.write('ERROR: No arm with ID: "%s" found in '
                'study!\n' % arm)
            return None

        # Iterate through hotspots, cnvs, fusions, and non-hs aMOIs and generate
        # a list of tuples of data that can be printed easily later.
        return dict(arm_data['amois'])

    def get_match_arm_info(self, armid=None):
        """
        Get information about NCI-MATCH study arms.

        This method will either return a full dictionary of study arms, with 
        drug, target, short description information for the whole study, or 
        filter out the data by arm using the ``armid`` argument.

        Args:
            armid (list): List of arms that you would like to filter on.

        Returns:
            dict: Dict of study arm data.

        Example: 
            >>> # Need to add example here.

        """
        results = defaultdict(dict)
        wanted = ('drug_id', 'name', 'target', 'status')

        for arm in self.data:
            results[arm] = {x : self.data[arm].get(x, None) for x in wanted}
        return dict(results)

    def get_arm_by_amoi(self, gene=None, hotspot=None):
        """
        Query study arms by gene or hotspot ID

        Input either a HUGO gene name or a hotspot ID as it is represented in
        the hotspots BED file (e.g. COSM476, MCH12, etc.), and return a list of
        arms for which that variant is a part, along with the type of variant 
        represented by the identifier.  If one were to enter BRAF, then all arms
        that contain BRAF mutations, along with the categories of `Hotspot` and 
        `Fusion` would be indicated, as BRAF can be activating in either of 
        those categories.  

        Args:
            gene (str): HUGO genename to use for querying the database.

            hotspot (str): NCI-MATCH assay hotspots BED file identifier to use
                query the database.

        Returns:
            list: List of study arms for which the query variants are aMOIs.

        Examples:

            >>> # Need to put an example here.

        .. attention::
            This method is not yet functional and is only a placeholder for
            now.  Intend to code and implement soon!

        """
        
        if gene:
            pass

