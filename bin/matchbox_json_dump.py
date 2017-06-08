#!/usr/bin/env python
import sys
import os
import json
import argparse
from pprint import pprint as pp

# Dirty hack for right now to see if we can figure out how call this as an external script
# TODO: Fix this once we make a real package.
# bin_path = os.path.dirname(os.path.realpath(__file__)).rstrip('/bin')
# sys.path.append(bin_path)
from matchbox_api_utils.Matchbox import *

version = '1.3.0_060717'

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

    parser = argparse.ArgumentParser(
        formatter_class = lambda prog: argparse.HelpFormatter(prog, max_help_position=100, width=150),
        description=
        '''
        Get parsed dataset from MATCHBox and dump as a JSON object that we can use later on to speed up development and
        periodic searching for data.  
        '''
    )
    parser.add_argument('-d', '--data', metavar='<raw_mb_datafile.json>',
            help='Load a raw MATCHBox database file (usually after running with the -r option).')
    parser.add_argument('-r', '--raw', action='store_true',
        help='Generate a raw dump of MATCHbox so that we can see the raw data structure available for debugging '
              'and dev purposes.')
    parser.add_argument('-o', '--outfile', metavar='<out.json>', 
            help='Name of output JSON file. DEFAULT: "mb_<datestring>.json"')
    parser.add_argument('-v', '--version', action='version', version = '%(prog)s  -  ' + version)
    args = parser.parse_args()
    return args

def main(data,outfile=None):
    # print('args as passed\ndata: {}\noutfile: {}\n'.format(data,outfile))
    sys.stdout.write("Dumping matchbox as a JSON file for easier and faster code testing...")
    sys.stdout.flush()
    data._matchbox_dump(outfile)
    sys.stdout.write("Done!")

if __name__=='__main__':
    if os.path.isfile(os.path.join(os.getcwd(), '/config.json')):
        config_file = os.path.join(os.getcwd(), '/config.json')
    else:
        config_file = os.path.join(os.environ['HOME'], '.mb_utils/config.json')
    
    # config_file = 'config.json'
    # config_file = os.path.join(os.path.dirname(os.path.realpath(__file__)),'config.json')
    try:
        config_data = Config.read_config(config_file)
    except IOError:
        print('ERROR: No configuration file found. Need to create a config file int he current direcotry or use '
              'the system provided one in ~/.mb_utils/config.json')
        sys.exit(1)

    args = get_args()
    if args.raw:
        MatchboxData(config_data['url'],config_data['creds'],raw_dump=True)
        sys.exit()

    outfile = args.outfile
    sys.stdout.write('Retrieving MATCHBox dataset for DB obj creation...\n')
    sys.stdout.flush()

    if args.data:
        data = MatchboxData(config_data['url'],config_data['creds'],dumped_data=args.data)
    else:
        # data = MatchboxData(config_data['url'],config_data['creds'])
        data = MatchboxData(config_data['url'],config_data['creds'],patient=16271)

    sys.stdout.write('Done!')
    main(data,outfile)

