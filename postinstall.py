#!/usr/bin/env python
import sys
import os
import json
from subprocess import call

def write_json(user,passwd,root_dir):
    config_data = {
        'name' : 'MATCHBox API config file',
        'version' : '1.0',
        'description' : 'Config file for MATCHBox API script in order to access '
                        'system with appropriate credentials',
        'creds' : {
            'username' : user,
            'password' : passwd,
        },
        'url' : 'https://matchbox.nci.nih.gov/match/common/rs/getPatients',
        'manifest_url' : 'https://matchbox.nci.nih.gov/reportapi/patientSpecimenTrackingSummary'
    }
    with open(os.path.join(root_dir,'config.json'), 'w') as fh:
        json.dump(config_data, fh, indent=4)
    sys.stdout.write('Done with config creation!\n')
    

def make_config_file(root_dir):
    '''Create a config file for use in connecting with MATCHBox.'''
    sys.stdout.write('Getting info and creating a config.json file '
                     'in %s...\n' % root_dir)
    user = raw_input('\tEnter the MATCHbox username: ')
    passwd = raw_input('\tEnter the password for %s: '% user)
    write_json(user,passwd,root_dir)

def pre_build_mb_obj(root_dir):
    '''First time launch, build a matchbox json dump file and put it into 
       $HOME/.mb_utils.
    '''
    sys.stdout.write('Creating a MATCHBox data dump for quicker lookups. This '
        'will take a few minutes...')
    sys.stdout.write('(NOTE: can do live queries at any time, but this can take '
        'quite a while and the use of routinely collected data dumps using '
        'matchbox_data_dump.py is preferred and encouraged.')

    call(['bin/matchbox_json_dump.py','-o', os.path.join(root_dir,'mb_obj.json')])
    #call(['bin/matchbox_json_dump.py','-d', 'raw_mb_dump_062117.json','-o',
          #'mb_obj.json'])
    sys.stdout.write('Done!\n\n@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@\n')
    sys.stdout.write('  We recommend you run the matchbox_data_dump.py program '
        'routintely to pick up any new data\n')
    sys.stdout.write('@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@\n')

if __name__=='__main__':
    root_dir = os.path.join(os.environ['HOME'], '.mb_utils/')
    sys.stdout.write('\n' + '-'*25 +'  MATCHBox API Utils Setup  '+ '-'*25 + '\n')

    make_config_file(root_dir)
    pre_build_mb_obj(root_dir)

    sys.stdout.write('Done with post-install config tasks.\n' + '-'*78 + '\n\n')
