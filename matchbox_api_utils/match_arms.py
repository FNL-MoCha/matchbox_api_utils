# -*- coding: utf-8 -*-
# TODO:
#    - make Matchbox class connector and retrieve the ta api data.
#    - make option to:
#         - return raw api data
#         - return proc api data (JSON file)
#         - normal set of processing functions.
import os
import sys
import re
import json
from collections import defaultdict
from pprint import pprint as pp

import matchbox_conf
from matchbox import Matchbox
from utils import *

class TreatmentArms(object):
    """

    NCI-MATCH Treatment Arms and aMOIs Class

    """

    def __init__(self,config_file=None,url=None,creds=None,json_db=None,make_db=False,load_raw=None,make_raw=False):

        self._config_file = config_file
        self._url = url
        self._creds = creds
        self._json_db = json_db
        self._load_raw = load_raw
        self.db_date = get_today('long')
        raw_flag = None

        if make_raw:
            raw_flag = 'ta'

        if not self._url:
            self._url = self.__get_config_data('arms_url')
        
        if not self._creds:
            self._creds = self.__get_config_data('creds')

        pp(vars(self))
        
        if self._load_raw:
            self.db_date,matchbox_data = load_dumped_json(self._load_raw)
            self.data = self.make_match_arms_db(matchbox_data)
        elif self._json_db:
            self.db_date,self.data = self.load_dumped_json(self._json_db)
        else:
            # make api call to get json data; load and present to self.data.
            matchbox_data = Matchbox(self._url,self._creds,make_raw=raw_flag).api_data
            self.data = self.make_match_arms_db(matchbox_data)

    def __str__(self):
        return json.dumps(self.data, sort_keys=True, indent=4)

    def __getitem__(self,key):
        return self.data[key]

    def __iter__(self):
        return self.data.itervalues()

    def __get_config_data(self,item):
        config_data = matchbox_conf.Config(self._config_file)
        return config_data[item]

    def __make_json_dump(data,filename=None):
        sys.stdout.write('Writing MATCH aMOIs and Arms to JSON file.\n')
        if not filename:
            filename = 'match_amois_arms_' + get_today('short') + '.json'
        with open(filename, 'w') as fh:
            json.dump(filename, indent=4)
        sys.exit()

    def __parse_diseases(self,disease_list):
        results = {}
        for d in disease_list:
            results[d['shortName']] = d['medraCode']
        if results:
            return results
        else:
            return None

    def __parse_ihc(self,ihc_assays):
        results = {}
        for assay in ihc_assays:
            results[assay['gene']] = assay['assayResultStatus']
        if results:
            return results
        else:
            return None

    def __parse_amois(self,amoi_data):
        """
        Getting a dict of amois with keys:
            copyNumberVariants
            geneFusions
            indels
            nonHotspotRules
            singleNucleotideVariants

        Each has variant params that we'll filter on.
            - Create functions to process each type.
            - Out dict of {variant_type: [{variant : (inclusion|exclusion)}]}
        # NOTE: how to handle non-hotspot rules.  Can't just input a gene and inclusion / exclusion. 
        #       Need to know the rest of the matching criteria.  Do we need a separate matching function
        #       or something to deal with this?

        """
        parsed_amois = {
            'cnv'    : None,
            'snv'    : None,
            'indel'  : None,
            'fusion' : None,
            'non_hs' : None,
        }

        #wanted = {
            #'singleNucleotideVariants' : 'snv',
            #'indels'                   : 'indel',
            #'copyNumberVariants'       : 'cnv',
            #'geneFusions'              : 'fusion',
            #'nonHotspotRules'          : 'non_hs'
        #}
        wanted = {'nonHotspotRules':'non_hs'}

        for var in wanted:
            if amoi_data[var]:
                pp(amoi_data[var])
                parsed_amois[wanted[var]] = self.__proc_var_table(amoi_data[var])
            else:
                parsed_amois[wanted[var]] = None
        pp(parsed_amois)

    @staticmethod
    def __proc_var_table(var_list):
        results = { i['matchingId'] : i['inclusion'] for i in var_list } 
        return results
    
    def make_match_arms_db(self,api_data):
        """
        Make a database of MATCH Treatment Arms.

        Read in raw API data and create pared down JSON structure that can be easily parsed later one.  Maybe 
        make an Arm class and use that instead?

        """
        # print('{}: len({})'.format(type(api_data),len(api_data)))
        # pp(api_data[0]['treatmentArmDrugs']) # list of dicts of treatment data with keys: 'description', 'drugClass','drugId','name','pathway','target'.  Probably just want name. Also no combos, so all lists are 1 elem.
        # pp(api_data[0]['exclusionDiseases']) # list of dicts of disease with keys 'ctepSubCategory','ctepTerm','medraCode','shortName'. probably want short name.
        # pp(api_data[i]['assayResults']) # list of dicts of IHC requirements. Capture 'gene' and 'assayResultStatus'

        # self.__parse_amois(api_data[0]['variantReport'])
       
        arm_data = defaultdict(dict)
        """
        #num = 1
        for num in xrange(0,38):
            print('\n->processing arm: %s' % api_data[num]['id'])
            self.__parse_amois(api_data[num]['variantReport'])
        sys.exit()

        for arm in api_data:
            print(arm['id'] + ':')
            wanted = arm['variantReport']['singleNucleotideVariants']
            if wanted:
                for var in wanted:
                    print('\t{} -> {}'.format(var['matchingId'],var['inclusion']))
                # pp(wanted)

        # amoi_report = api_data[29]['variantReport']
        # pp(amoi_report)
        # self.__parse_amois()

        # for i in api_data:
            # print(i['id'])
            # disdict = self.__parse_diseases(i['exclusionDiseases'])
            # if not disdict:
                # disdict = {None:None}
            # pp(disdict)
            # print('\n')
        sys.exit()

        """
        for arm in api_data:
            arm_id = arm['id']
            # print(arm.keys())
            arm_data[arm_id]['name']          = arm['name']
            arm_data[arm_id]['arm_id']        = arm['id']
            arm_data[arm_id]['gene']          = arm['gene']
            arm_data[arm_id]['drug_name']     = arm['targetName']
            arm_data[arm_id]['drug_id']       = arm['treatmentArmDrugs'][0]['drugId']
            arm_data[arm_id]['assigned']      = arm['numPatientsAssigned']
            arm_data[arm_id]['excl_diseases'] = self.__parse_diseases(arm['exclusionDiseases'])
            arm_data[arm_id]['ihc']           = self.__parse_ihc(arm['assayResults'])

        # pp(api_data[0]['variantReport']) # list of aMOIs....need a lot of parsing!
        # pp(dict(arm_data))
        return
