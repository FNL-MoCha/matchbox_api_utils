# -*- coding:utf-8 -*-
import sys
import os
import json

import matchbox_api_utils

from pprint import pprint as pp
from matchbox_api_utils import utils


class Config(object):
    def __init__(self, matchbox_name, config_file=None, mb_json_data=None, 
            ta_json_data=None, amois_lookup=None):
        """
        MATCHBox Configuration Class

        Allow for import of custon configuration and mb.json data, or else just
        load the standard dataset deployed during package installation.

        """

        self._matchbox_name = matchbox_name
        if config_file is not None:
            self._config_file = config_file
        else: 
            self._config_file = matchbox_api_utils.mb_config_file
        self.config_data = self.read_config()

        # TODO: Fix this 
        '''
        if mb_json_data:
            self.config_data['mb_json_data'] = mb_json_data
        else:
            self.config_data['mb_json_data'] = matchbox_api_utils.mb_json_data

        if ta_json_data:
            self.config_data['ta_json_data'] = ta_json_data
        else:
            self.config_data['ta_json_data'] = matchbox_api_utils.ta_json_data

        if amois_lookup:
            self.config_data['amois_lookup'] = amois_lookup
        else:
            self.config_data['amois_lookup'] = matchbox_api_utils.amoi_json_data
        '''

    def __repr__(self):
        return '%s:%s' % (self.__class__, self.__dict__)

    def __str__(self):
        return utils.print_json(self.config_data)

    def __getitem__(self, key):
        return self.config_data[key]

    def __iter__(self):
        return self.config_data.itervalues()

    def get_config_item(self, item):
        return self.config_data[item]

    def read_config(self):
        try:
            with open(self._config_file) as fh:
                data = json.load(fh)
        except IOError:
            sys.stderr.write('ERROR: No configuration file found. You must either '
                'run the package configuration tools or provide a config file '
                'using the "config" option. Can not continue!\n')
            sys.exit(1)
        return data[self._matchbox_name]
