#!/usr/local/bin/python3
import sys
import os
import argparse
import subprocess
import json
import importlib
from pprint import pprint as pp

import get_mb_data
#import matchbox_patient_summary as summary

version = '0.2.0_111816'

class Config(object):
    '''Read in a config file and generate a configuration object for the whole package.'''
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

class Launcher(object):
    def __init__(self,prog,opts,input_data):
        opt_string = ' '.join(opts)
        self.program = {
            'prog' : prog,
            'opts' : opt_string,
            'data' : input_data,
        }
        
    def __str__(self):
        return '{} {} {}'.format(self.program['prog'],self.program['opts'],self.program['data'])

    def __repr__(self):
        return '%s:%s' % (self.__class__,self.__dict__)

    def __getitem__(self,key):
        return self.program[key]

    def launch(self):
        '''TODO:  I think we want to use a subprocess call here.  There are too many different types of opts and calls that would need to be 
        configured in this obj to be universal.  If I use subprocess, then I can leverage the normal arg parsing functionality of the module.

        In this case need to recovert the module back into a script name.
        '''
        sys.stdout.write('Running program {}...\n'.format(self.program['prog']))
        sys.stdout.flush()
        print(self.program['opts'])
        sys.exit()
        p = subprocess.Popen([self.program['prog'], self.program['opts'], self.program['data'])

        #self.program['prog'].patient_summary(self.program['opts'],self.program['data'])
        self.program['prog'].patient_summary(self.program['data'])
        sys.stdout.write('Done!\n')
        #print(type(self.program['prog']))

def get_args():
    parser = argparse.ArgumentParser(
        formatter_class = lambda prog: argparse.HelpFormatter(prog, max_help_position=100, width=150),
        description=
        '''
        Wrapper for matchbox_api_utilities. Run <program> 'help' to get help documentation for an each
        program in the list.  
        ''',
    )
    parser.add_argument('program', nargs='?',
            help='Specific MATCHBox script to run.  Run <program> -h to get individual help.')
    parser.add_argument('-j', '--json', metavar='<mb.json>', 
            help='MATCHBox JSON file to load rather than getting a new dataset in real time.')
    parser.add_argument('-l', '--list', action='store_true', dest='list_progs', help='List available programs and exit')
    parser.add_argument('-v', '--version', action='version', version='%(prog)s - ' + version)
    parser.add_argument('-o', '--outfile', metavar='<output_file>', help='Where to store the data!')
    parser.add_argument('-p', '--psn', help='Filter data to this PSN')

    # subparsers = parser.add_subparsers(dest='program')
    # summary_parser = subparsers.add_parser('summary')

    args = parser.parse_args()
    return args

def prog_list(prog):
    '''Test to make sure the input program is correct and / or print out a list of acceptable progs.  Import module if
    it's in the list and return the module obj.'''
    utils_list = {
        'var_freq' : 'match_variant_frequency',
        'dump'     : 'matchbox_json_dump',
        'get_vcf'  : 'get_match_vcfs',
        'summary'  : 'matchbox_patient_summary'
    }

    if prog == '?':
        print('Available programs:')
        for prog in utils_list:
            print('\t{}'.format(prog))
    elif prog not in utils_list:
        sys.stderr.write('ERROR: You must choose a program to run from the list\n')
        prog_list('?')
        return False
    else:
        try:
            mod = importlib.import_module(utils_list[prog])
            return mod
        except:
            sys.stderr.write("ERROR: no such module {}!\n".format(utils_list[prog]))
            sys.exit(1)

def parse_sub_args(args):
    '''Format a normal arg string from all passed args so that we can make a reasonable executable string. Kludgy way to
    try to get around the way argparse has to handle this.'''
    excluded_args = ('json', 'list_progs', 'program')
    return ['--{} {}'.format(k,v) for k,v in args.items() if k not in excluded_args]

if __name__=='__main__':
    args = vars(get_args()) # convert Namespace into dict

    # Test the program arg to either print a list or validate the input prog name.
    if args['list_progs']:
        prog_list('?')
        sys.exit()

    prog = prog_list(args['program'])

    # Generate a MB data obj to pass to helper script.
    match_data = get_mb_data.main(args['json'],None)

    # Get only the args we want to pass to the child program.
    args_list = parse_sub_args(args)

    # Launch program with appropriate args
    prog_config = Launcher(prog,args_list,match_data)
    prog_config.launch()
