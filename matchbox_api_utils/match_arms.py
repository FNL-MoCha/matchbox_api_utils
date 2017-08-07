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
        """
        <Description>
        
        """
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
        
        if self._load_raw:
            self.db_date,matchbox_data = load_dumped_json(self._load_raw)
            self.data = self.make_match_arms_db(matchbox_data)
        elif self._json_db:
            self.db_date,self.data = self.load_dumped_json(self._json_db)
        else:
            # make api call to get json data; load and present to self.data.
            matchbox_data = Matchbox(self._url,self._creds,make_raw=raw_flag).api_data
            self.data = self.make_match_arms_db(matchbox_data)
        
        self.__gen_rules_table()
        # pp(vars(self))

    def __str__(self):
        return json.dumps(self.data, sort_keys=True, indent=4)

    def __getitem__(self,key):
        return self.data[key]

    def __iter__(self):
        return self.data.itervalues()

    # FIXME: Move to utils module?
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

    # TODO: See if we can make more generic and usable to MatchData()
    def __retrive_data_with_keys(self,data,k1,k2):
        results = {}
        for elem in data:
            results[elem[k1]] = elem[k2]
        if results:
            return results
        else:
            return None

    def __gen_rules_table(self,arm_id = None):
        """
        wanted data struct:
            'hotspots' : [
                'hs_id' : [arm1, arm2, arm3],
                'hs_id' : [arma, armb, armc],
            ],
            'cnvs' : [
                'gene1' : [arm1, arm2],
                'gene2' : [arma, armb],
            ],
            'fusions' : [
                'fusion_id' : [arm1, arm2, arm3],
            ],
            'non_hs' : {
                'positional' : [
                    'gene' : [ 'exon|function' : [arms]],
                    'EGFR' : [ '19|nonframeshiftDeletion' : [ArmA]],
                    'ERBB2' : [ '20|nonframeshiftInsertion' : [ArmB, ArmBX1]],
                ]
                'deleterious' : [
                     'gene' : [arms],
                ]
            }

        """
        rules_table = {
            'hotspots' : defaultdict(list),
            'cnvs' : defaultdict(list), 
            'fusions' : defaultdict(list),
            'non_hs' : {'positional' : [], 'deleterious' : []}
        }
        ie_flag = {'True' : 'i', 'False' : 'e'}

        for arm in self.data:
            amoi_data = self.data[arm]['amois']
            if amoi_data['cnv']:
                # cnvs = [self.__get_varid(x) for x in amoi_data['cnv']]
                for v in amoi_data['cnv']:
                    rules_table['cnvs'][v].append('{}{}'.format(arm,ie_flag[str(amoi_data['cnv'][v])]))
                pass
            elif amoi_data['fusion']:
                for v in amoi_data['fusion']:
                    rules_table['fusions'][v].append('{}{}'.format(arm,ie_flag[str(amoi_data['fusion'][v])]))
                # fusions = [self.__get_varid(x) for x in amoi_data['fusion']]
                pass
            elif amoi_data['hotspot']:
                for v in amoi_data['hotspot']:
                    rules_table['hotspots'][v].append('{}{}'.format(arm,ie_flag[str(amoi_data['hotspot'][v])]))
                # snvs = [self.__get_varid(x) for x in amoi_data['snv']]
            elif amoi_data['non_hs']:
                pass
        # pp(dict(rules_table))
        for var_type in rules_table:
            print('type: {} => total: {}'.format(var_type,len(rules_table[var_type].keys())))
            pp(dict(rules_table[var_type]))



    @staticmethod
    def __get_varid(var):
        ie_flag = {'True' : 'i', 'False' : 'e'}
        v,f = var.items()
        return '{}{}'.format(v,ie_flag[str(f)])


    def __parse_amois(self,amoi_data):
        """
        Getting a dict of amois with keys:
            copyNumberVariants
            geneFusions
            indels
            nonHotspotRules
            singleNucleotideVariants

        """
        parsed_amois = defaultdict(dict)

        wanted = {
            'singleNucleotideVariants' : 'hotspot',
            'indels'                   : 'hotspot',
            'copyNumberVariants'       : 'cnv',
            'geneFusions'              : 'fusion',
            'nonHotspotRules'          : 'non_hs'
        }

        # test = defaultdict(dict)
        for var in wanted:
            # Have to handle non-hs vars a bit differently.
            if var == 'nonHotspotRules':
                nhr_vars = {'deleterious' : [], 'positional' : []}
                for elem in amoi_data[var]:
                    if elem['oncominevariantclass'] == 'Deleterious':
                        nhr_vars['deleterious'].append({elem['gene'] : elem['inclusion']})
                    else:
                        var_id = '|'.join([elem['gene'],elem['exon'],elem['function']])
                        nhr_vars['positional'].append({var_id : elem['inclusion']})
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

        Read in raw API data and create pared down JSON structure that can be easily parsed later one.  Maybe 
        make an Arm class and use that instead?

        """
        arm_data = defaultdict(dict)
        """
        for arm in api_data:
            print(arm['id'] + ':')
            wanted = arm['variantReport']['singleNucleotideVariants']
            if wanted:
                for var in wanted:
                    print('\t{} -> {}'.format(var['matchingId'],var['inclusion']))
                # pp(wanted)
        """
        for arm in api_data:
            arm_id = arm['id']
            #TODO: remove this.
            # if arm_id.endswith('V'):
            # if arm_id.startswith('EAY'):
            if arm_id == 'EAY131-A':
                print('\n->processing arm: %s' % arm_id)
                # amoi_tmp = self.__parse_amois(arm['variantReport'])
                # print('\n')
            else:
                continue
            # print(arm.keys())
            arm_data[arm_id]['name']          = arm['name']
            arm_data[arm_id]['arm_id']        = arm['id']
            arm_data[arm_id]['gene']          = arm['gene']
            arm_data[arm_id]['drug_name']     = arm['targetName']
            arm_data[arm_id]['drug_id']       = arm['treatmentArmDrugs'][0]['drugId']
            arm_data[arm_id]['assigned']      = arm['numPatientsAssigned']
            arm_data[arm_id]['excl_diseases'] = self.__retrive_data_with_keys(arm['exclusionDiseases'],'shortName','medraCode')
            arm_data[arm_id]['ihc']           = self.__retrive_data_with_keys(arm['assayResults'],'gene','assayResultStatus')
            arm_data[arm_id]['amois']         = self.__parse_amois(arm['variantReport'])

        # pp(dict(arm_data))
        # sys.exit()
        return arm_data
