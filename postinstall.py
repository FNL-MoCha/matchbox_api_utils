#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Post install script to set up environment
import sys
import os
import json
import datetime
from subprocess import call
from pprint import pprint as pp

import matchbox_api_utils

# Want to store data in user's home dir, but if running with `sudo` need to 
# make special consideration.
if 'SUDO_USER' in os.environ:
    system_user = os.environ['SUDO_USER']
else:
    system_user = os.environ['USER']

def write_json(user,passwd,root_dir):
    config_file = os.path.join(root_dir,'config.json')
    config_data = {
        'name' : 'MATCHBox API config file',
        'version' : '1.0',
        'description' : 'Config file for MATCHBox API script in order to access'
            'system with appropriate credentials',
        'creds' : {
            'username' : user,
            'password' : passwd,
        },
        'url' : 'https://matchbox.nci.nih.gov/match/common/rs/getPatients',
        'manifest_url' : 'https://matchbox.nci.nih.gov/reportapi/patient'
            'SpecimenTrackingSummary',
        'arms_url' : 'https://matchbox.nci.nih.gov/match/common/rs/'
            'getTreatmentArms'
    }
    with open(config_file, 'w') as fh:
        json.dump(config_data, fh, indent=4)
    os.system('chown {} {}'.format(system_user,config_file))
    sys.stdout.write('Done with config creation!\n')

def make_config_file(root_dir):
    '''Create a config file for use in connecting with MATCHBox.'''
    sys.stdout.write('Getting info and creating a config.json file '
                     'in %s...\n' % root_dir)
    user = raw_input('\tEnter the MATCHbox username: ')
    passwd = raw_input('\tEnter the password for %s: '% user)
    write_json(user,passwd,root_dir)

def fix_perms(input_file):
    os.system('chown {} {}'.format(system_user, input_file))

def pre_build_mb_obj(root_dir):
    """
    First time launch, build a matchbox json dump file and put it into 
    $HOME/.mb_utils.
    """
    datestring=datetime.date.today().strftime('%m%d%y')
    mb_obj_file = os.path.join(root_dir,'mb_obj_' + datestring + '.json')
    ta_obj_file = os.path.join(root_dir,'ta_obj_' + datestring + '.json')
    amoi_lookup_file = os.path.join(root_dir, 
            'amoi_lookup_' + datestring + '.json')
    sys.stdout.write('Creating a MATCHBox data dump for quicker lookups.\n')
    sys.stdout.write(
        '''(NOTE: can do live queries at any time, but this can take quite a 
        while and the use of routinely collected data dumps using 
        matchbox_data_dump.py is preferred and encouraged.\n
        '''
    )

    call(['bin/matchbox_json_dump.py', '-m', mb_obj_file, '-t', ta_obj_file, 
        '-a', amoi_lookup_file])

    # Need to make sure that non-root user is owner of these files rather than 
    # root (since probably need sudo to install). 
    for f in (mb_obj_file, ta_obj_file, amoi_lookup_file):
        fix_perms(f)
    
    sys.stdout.write("\n" + '@'*75 + "\n")
    sys.stdout.write('\tWe recommend you run the matchbox_data_dump.py '
        'program\n\troutintely to pick up any new data that has been '
        'generated\n\tsince last polling.\n')
    sys.stdout.write('@'*75 + "\n")

if __name__=='__main__':
    root_dir = matchbox_api_utils.mb_utils_root
    # Just in case we had to make this when setting up the package (i.e. we had
    # to use `sudo`, fix the perms so that the user owns rather than $ROOT
    fix_perms(root_dir)

    sys.stdout.write('\n{0}  MATCHBox API Utils Setup  {0}\n'.format('-'*25))

    make_config_file(root_dir)
    pre_build_mb_obj(root_dir)

    sys.stdout.write('Done with post-install config tasks.\n' + '-'*78 + '\n\n')
