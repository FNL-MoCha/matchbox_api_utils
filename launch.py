#!/usr/local/bin/python3
import sys
import os
import argparse
import subprocess
import json
import importlib
import shlex
from pprint import pprint as pp

bin_path = os.path.dirname(os.path.realpath(__file__)) + '/bin/'
sys.path.append(bin_path)

import make_mb_obj
import matchbox_patient_summary as summary

version = '0.4.0_111816'

class Launcher(object):
    def __init__(self,prog,opts,input_data):
        self.program = {k : v for k,v in opts.items()}
        self.program['prog'] = prog
        self.program['data'] = input_data
        pp(self.program)
        
    def __repr__(self):
        return '%s:%s' % (self.__class__,self.__dict__)

    def __getitem__(self,key):
        return self.program[key]

    def launch(self):
        '''
        Launch the target script with the inserted CLI args.  Would like to do this as a module, but too complicated
        to do since there are too many different permutations of args and whatnot that are needed for this.
        '''
        sys.stdout.write('Running program {}...\n'.format(self.program['prog']))
        sys.stdout.flush()

        # for example: summary.patient_summary(match_data,args['psn'])
        # How to get entry point for each?
        # print('{} => {}'.format(func, type(func)))
        # sys.exit()
        # func = getattr(self.program['prog'],func)
        # TODO:  This totally works!  The idea is to use the getattr below to define 'func' as mod.func() so that we 
        # can use this here.  Question:  Do we want to pass that to this launch method, or do we want to define that
        # in the launcher class.
        self.program['prog'](self.program['data'],self.program['psn'])
        # self.program['prog'].func(self.program['data'],self.program['psn'])

        # print('options passed to prog: {}'.format(self.program['opts']))
        # cmd = [self.program['prog']] + shlex.split(self.program['opts'])
        # print('full cmd: %s' % cmd)
        # for i in self.program:
            # print("{}  => {}".format(i, type(self.program[i])))
        # sys.exit()
        # subprocess.call([cmd,self.program['data']])
        sys.stdout.write('Done!\n')

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
    parser.add_argument('--modhelp', action='store_true', help='Show help message for individual mod')
    parser.add_argument('-v', '--version', action='version', version='%(prog)s - ' + version)
    parser.add_argument('-o', '--outfile', metavar='<output_file>', help='Where to store the data!')
    parser.add_argument('-p', '--psn', help='Filter data to this PSN')
    args = parser.parse_args()
    return args

def prog_list(prog):
    '''Test to make sure the input program is correct and / or print out a list of acceptable progs.  Import module if
    it's in the list and return the module obj and entry func.'''
    utils_list = {
        'var_freq' : ('match_variant_frequency', ''),
        'dump'     : ('matchbox_json_dump', 'main'),
        'get_vcf'  : ('get_match_vcfs',''),
        'patient_summary'  : ('matchbox_patient_summary','patient_summary'),
        'disease_summary'  : ('matchbox_patient_summary','disease_summary'),
    }

    if prog == '?':
        print('Available programs:')
        for prog in utils_list:
            print('\t{}'.format(prog))
    elif prog not in utils_list:
        sys.stderr.write('ERROR: You must choose a program to run from the list\n')
        prog_list('?')
        sys.exit(1)
    else:
        try:
            # Use importlib if we go the import route. Mod name if we use subprocess.
            mod    = importlib.import_module(utils_list[prog][0])
            func   = getattr(mod,utils_list[prog][1])
            script = '{}{}.py'.format(bin_path,utils_list[prog][0])
            return func,script
        except:
            sys.stderr.write("ERROR: no such module {}!\n".format(utils_list[prog]))
            sys.exit(1)

def parse_sub_args(args):
    '''Format a normal arg string from all passed args so that we can make a reasonable executable string. Kludgy way to
    try to get around the way argparse has to handle this.'''
    excluded_args = ('json', 'list_progs', 'program', 'modhelp')
    return ['--{} {}'.format(k,v) for k,v in args.items() if k not in excluded_args]

if __name__=='__main__':
    args = vars(get_args()) # convert Namespace into dict

    # Test the program arg to either print a list or validate the input prog name.
    if args['list_progs']:
        prog_list('?')
        sys.exit()

    # prog,func,script = prog_list(args['program'])
    func,script = prog_list(args['program'])

    # If we just want help docs for individual program
    if args['modhelp']:
        subprocess.run([script, '--help'])
        sys.exit()

    # Get only the args we want to pass to the child program.
    # TODO: probably remove this.
    args_list = parse_sub_args(args)
    pp(args_list)
    filtered_args = [x for x in args_list if not x.endswith('None')]
    pp(filtered_args)
    # sys.exit()

    # Generate a MB data obj to pass to helper script.
    match_data = make_mb_obj.main(args['json'],None)

    # Launch program with appropriate args
    prog_config = Launcher(func,args,match_data)
    prog_config.launch()
