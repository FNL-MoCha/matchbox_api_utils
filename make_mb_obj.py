#!/usr/local/bin/python3
import sys
import os
import json

from matchbox_api_utils.Matchbox import *

version = '0.1.0_111816'

class Config(object):
    def __init__(self,config_file):
        self.config_file = config_file
        self.config_data = {}
        self.config_data = Config.read_config(self.config_file)

    def __repr__(self):
        return '%s:%s' % (self.__class__,self.__dict__)

    def __getitem__(self,key):
        return self.config_data[key]

    def __iter__(self):
        return self.config_data.itervalues()

    @classmethod
    def read_config(cls,config_file):
        '''Read in a config file of params to use in this program'''
        with open(config_file) as fh:
            data = json.load(fh)
        return data

def main(json=None,patient=None):
    config_file = 'config.json'
    config_data = Config.read_config(config_file)
    match_data = MatchboxData(config_data['url'],config_data['creds'],json,patient)
    return match_data

if __name__=='__main__':
    main()
