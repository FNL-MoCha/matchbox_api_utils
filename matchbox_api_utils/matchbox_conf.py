#!/usr/bin/env python
import sys
import os
import json

class Config(object):
    '''Configuration class for Matchbox. Can be run standalone or called (more properly) from matchbox'''
    def __init__(self,config_file):
        self.config_file = config_file
        self.config_data = Config.read_config(self.config_file)

    def __repr__(self):
        return '%s:%s' % (self.__class__,self.__dict__)

    def __getitem__(self,key):
        return self.config_data[key]

    def __iter__(self):
        return self.config_data.itervalues()

    @classmethod
    def read_config(cls,config_file):
        with open(config_file) as fh:
            data = json.load(fh)
        return data

if __name__=='__main__':
    config_file = os.path.join(os.environ['HOME'], '.mb_utils/config.json')
    if not os.path.isfile(config_file):
        config_file = os.path.join(os.getcwd(), 'config.json')

    try:
        config_data = Config(config_file)
    except IOError:
        print("ERROR: no configuration file found. Need to create a config file in the current directory or use system "
              "provided file in ~/.mb_utils")
        sys.exit(1)
