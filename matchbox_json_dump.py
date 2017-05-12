#!/usr/local/bin/python3
import sys
import os
import json
import argparse
from pprint import pprint as pp

# Dirty hack for right now to see if we can figure out how call this as an external script
# TODO: Fix this once we make a real package.
bin_path = os.path.dirname(os.path.realpath(__file__)).rstrip('/bin')
sys.path.append(bin_path)
from Matchbox import *

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

def get_args():
    version = '1.2.0_110116'
    parser = argparse.ArgumentParser(
        formatter_class = lambda prog: argparse.HelpFormatter(prog, max_help_position=100, width=150),
        description=
        '''
        Get parsed dataset from MATCHBox and dump as a JSON object that we can use later on to speed up development and
        periodic searching for data.  
        '''
    )
    parser.add_argument('-v', '--version', action='version', version = '%(prog)s  -  ' + version)
    parser.add_argument('-o', '--outfile', metavar='<out.json>', help='Name of output JSON file. DEFAULT: "mb_<datestring>.json"')
    args = parser.parse_args()
    return args

def main(data,outfile=None):
    print('args as passed\ndata: {}\noutfile: {}\n'.format(data,outfile))
    sys.stdout.write("Dumping matchbox as a JSON file for easier and faster code testing...")
    sys.stdout.flush()
    data._matchbox_dump(outfile)
    sys.stdout.write("Done!")

if __name__=='__main__':
    # config_file = 'config.json'
    config_file = os.path.join(os.path.dirname(os.path.realpath(__file__)),'config.json')
    config_data = Config.read_config(config_file)
    args = get_args()
    outfile = args.outfile
    data = MatchboxData(config_data['url'],config_data['creds'])
    main(data,outfile)

