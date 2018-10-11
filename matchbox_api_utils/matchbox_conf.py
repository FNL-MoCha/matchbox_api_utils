# -*- coding:utf-8 -*-
import sys
import os
import json

import matchbox_api_utils

from matchbox_api_utils import utils


class Config(object):
    def __init__(self, matchbox_name, connection, config_file=None, 
            mb_json_data=None, ta_json_data=None, amois_lookup=None):
        """
        MATCHBox Configuration Class

        Allow for import of custon configuration and mb.json data, or else just
        load the standard dataset deployed during package installation.

        Args:
            matchbox_name (str) Name of the MATCHBox to which we'll make the 
                connection. 

            connection (str): Type of connection to be made.  Choose only from
                'api' or 'mongo'. 
                .. note::
                    The `api` method is to be deprecated, and connections using
                    `mongo` will be preferred.

        """

        self._matchbox_name = matchbox_name
        self._connection = connection
        if config_file is not None:
            self._config_file = config_file
        else: 
            self._config_file = matchbox_api_utils.mb_config_file
        self.config_data = self.read_config()

        # This might fail when we are running the package setup post installer 
        # for brand new installs on systems where we have never installed the 
        # package. But the failure is OK, because the rest of the steps will 
        # take care of filling in the blanks.
        try:
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
        except AttributeError:
            sys.stderr.write('Have not yet established initial MATCHBox JSON DB '
                'files. If this is not a package\nsetup message, then we may '
                'have a problem and setup needs to be re-run.\n')

    def __repr__(self):
        return '%s:%s' % (self.__class__, self.__dict__)

    def __str__(self):
        return utils.print_json(self.config_data)

    def __getitem__(self, key):
        return self.config_data[key]

    def __iter__(self):
        return self.config_data.itervalues()

    def get_config_item(self, item):
        # return self.config_data[item]
        return self.config_data.get(item, None)

    def put_config_item(self, key, val):
        self.config_data.update({key: val})

    def read_config(self):
        try:
            data = utils.read_json(self._config_file)
        except:
            sys.stderr.write('ERROR: No configuration file found. You must '
                'either run the package configuration tools or provide a config'
                ' file using the "config" option. Can not continue!\n')
            sys.exit(1)
        return data[self._matchbox_name][self._connection]
