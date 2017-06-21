#!/usr/bin/env python
import sys
import os
import json
import argparse
from pprint import pprint as pp

from matchbox_api_utils.Matchbox import MatchboxData

version = '1.4.0_060817'


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
        formatter_class = lambda prog: 
            argparse.HelpFormatter(prog, max_help_position=100, width=150),
        description=
        '''
        Get parsed dataset from MATCHBox and dump as a JSON object that we can use 
        later on to speed up development and periodic searching for data.  
        '''
    )
    parser.add_argument('-d', '--data', metavar='<raw_mb_datafile.json>',
            help='Load a raw MATCHBox database file (usually after running with '
                 'the -r option).')
    parser.add_argument('-r', '--raw', action='store_true',
        help='Generate a raw dump of MATCHbox so that we can see the raw data '
             'structure available for debugging and dev purposes.')
    parser.add_argument('-p', '--patient', metavar='<psn>', 
            help='Patient sequence number used to limit output for testing and '
                 'dev purposes')
    parser.add_argument('-o', '--outfile', metavar='<out.json>', 
            help='Name of output JSON file. DEFAULT: "mb_<datestring>.json"')
    parser.add_argument('-v', '--version', action='version', 
            version = '%(prog)s  -  ' + version)
    args = parser.parse_args()
    return args

def main(data,outfile=None):
    data._matchbox_dump(outfile)
    sys.stdout.write("Done!\n")

if __name__=='__main__':
    config_file = os.path.join(os.environ['HOME'], '.mb_utils/config.json')
    if not os.path.isfile(config_file):
        # TODO: Get rid of this and insist on generating a config file. Maybe 
        # need to create a helper script for this?
        config_file = os.path.join(os.getcwd(), 'config.json')

    try:
        config_data = Config.read_config(config_file)
    except IOError:
        sys.stderr.write('ERROR: No configuration file found. Need to create a '
            'config file in the current directory or use the system provided one '
            'in ~/.mb_utils/config.json\n')
        sys.exit(1)

    args = get_args()

    if args.raw:
        sys.stdout.write('\n*** Making a raw dump of MATCHBox for dev / testing '
            'purposes ***\n')
        sys.stdout.flush()
        MatchboxData(config_data['url'],config_data['creds'],make_raw=True)
        sys.stdout.write('Done!\n')
        sys.exit()

    sys.stdout.write("Dumping matchbox as a JSON file for easier and faster code "
        "testing...")
    sys.stdout.flush()

    data = MatchboxData(
        config_data['url'],
        config_data['creds'],
        load_raw=args.data,
        patient=args.patient
    )

    outfile = args.outfile
    main(data,outfile)
