import sys
import os
import json

import matchbox_api_utils

class Config(object):
    def __init__(self,mb_config_file=None,mb_json_data=None):
        """MATCHBox Configuration Class

        Allow for import of custon configuration and mb.json data, or else just
        load the standard dataset deployed during package installation.

        """
        if mb_config_file:
            self.config_file = mb_config_file
        else:
            self.config_file = matchbox_api_utils.mb_config_file
        self.config_data = Config.read_config(self.config_file)

        if mb_json_data:
            self.config_data['mb_json_data'] = mb_json_data
        else:
            self.config_data['mb_json_data'] = matchbox_api_utils.mb_json_data

    def __repr__(self):
        return '%s:%s' % (self.__class__,self.__dict__)

    def __getitem__(self,key):
        return self.config_data[key]

    def __iter__(self):
        return self.config_data.itervalues()

    @classmethod
    def read_config(cls,config_file):
        try:
            with open(config_file) as fh:
                data = json.load(fh)
        except IOError:
            sys.stderr.write('ERROR: No configuration file found. You must either run the package configuration '
                'tools or provide a config file using the "config" option. Can not continue!\n')
            sys.exit(1)
        return data
