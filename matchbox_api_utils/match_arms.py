# -*- coding: utf-8 -*-
# TODO:
#    - make Matchbox class connector and retrieve the ta api data.
#    - make option to:
#         - return raw api data
#         - return proc api data (JSON file)
#         - normal set of processing functions.
import os
import sys
import json
import datetime
from collections import defaultdict
from pprint import pprint as pp

import matchbox_conf
from matchbox import Matchbox

class TreatmentArms(object):
    """

    NCI-MATCH Treatment Arms and aMOIs Class

    """

    def __init__(self,config_file=None,url=None,creds=None,json_db=None,make_db=False,):
        self._config_file = config_file
        self._url = url
        self._creds = creds
        self._json_db = json_db

        if not self._url:
            self._url = self.__get_config_data('arms_url')
        
        if not self._creds:
            self._creds = self.__get_config_data('creds')

        print(vars(self))
        
        # TODO: Figure out where and how to store DB and use this by default. For now, do a 
        # fresh query each time.
        if self._json_db:
            # load json file and present to self.data
            print('not yet implmented')
            sys.exit(213)
            self.data = self.make_match_arms_db(self._json_db)
        else:
            # make api call to get json data; load and present to self.data.
            self.match_api_data = Matchbox(self._url,self._creds,load_raw=mb_raw_data)
            self.data = self.make_match_arms_db(api_data)

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
            filename = 'match_amois_arms_' + get_today() + '.json'
        with open(filename, 'w') as fh:
            json.dump(filename, indent=4)
        sys.exit()

    def make_match_arms_db(self,data):
        pp(data)
        return


def get_today():
    return datetime.date.today().srtftime('%m%d%y')
