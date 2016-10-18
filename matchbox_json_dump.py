#!/usr/bin/python
import sys
import os
import json
import csv
import datetime
from pprint import pprint as pp
from Matchbox import *

version = '1.1.0_092916'

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

if __name__=='__main__':
    config_file = 'config.json'
    config_data = Config.read_config(config_file)
    data = MatchboxData(config_data['url'],config_data['creds'])
    print "Dumping matchbox as a JSON file for easier and faster code testing...",
    try:
        outfile = sys.argv[1]
        data._matchbox_dump(outfile)
    except IndexError:
        data._matchbox_dump()
    print "Done!"
