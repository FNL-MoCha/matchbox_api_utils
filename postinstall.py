#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Post install script to set up environment
import sys
import os

from subprocess import call
from pprint import pprint as pp
from getpass import getpass

import matchbox_api_utils

# Want to store data in user's home dir, but if running with `sudo` need to 
# make special consideration.
if 'SUDO_USER' in os.environ:
    system_user = os.environ['SUDO_USER']
else:
    system_user = os.environ['USER']

config_stump = {
    'meta-info' : {
        'name' : 'MATCHBox v2.0 API Tools Config File',
        'version' : 'v2.0',
        'date' : matchbox_api_utils.utils.get_today('long'),
        'description' : 'Config file for MATCHBox v2.0 API Utils package.'
    }
}


def write_json(config_data):
    config_file = os.path.join(root_dir, 'mb2.0_config.json')
    if os.path.exists(config_file):
        sys.stderr.write('WARN: Previously established config file detected. '
            'Making backup before\ncreating a new one.\n')
        os.rename(
            os.path.realpath(config_file), 
            os.path.realpath(config_file) + '.bak'
        )

    matchbox_api_utils.utils.make_json(outfile=config_file, data=config_data, 
        sort=False)
    fix_perms(config_file)

    if test_config_file(config_file) is True:
        sys.stdout.write('Done with config creation!\n')
    else:
        sys.stderr.write('ERROR: There was an issue with the new config '
            'file! You may need to manually create one or try to re-install '
            'this package.\n')
        sys.exit(1)

def test_config_file(config_file):
    sys.stdout.write('\nTesting new configuration file can be loaded.\n')
    try:
        config_data = matchbox_api_utils.matchbox_conf.Config(
            matchbox_name='adult', config_file=config_file)
        matchbox_api_utils.utils.print_json(config_data.config_data)
        return True
    except:
        raise
        return False

def make_config_file(root_dir):
    '''Create a config file for use in connecting with MATCHBox.'''
    sys.stdout.write('Getting info and creating a config JSON file in %s...'
         '\n' % root_dir)
    sys.stdout.write(
        '\nThere are currently three different MATCHBox systems that we can\n'
        'possibly connect to. Enter the username and password for each to\n'
        'make a entry in the config file. If you do not have credentials \n'
        'and / or do not want to make a connection to that system, just leave\n'
        'username and password blank.\n'
    )

    matchboxes = {
        'adult' : {
            'client_name' : 'Adult-MATCH-Production',
            'client_id' : 'xIK6GfCwz87sq2vPd2CJpFtKwaDR32PH',
            'url' : 'https://match.nci.nih.gov/api/v1/patients',
            'arms_url' : 'https://match.nci.nih.gov/api/v1/treatment_arms',
            'version' : '2.0'
        },
        'adult-uat' : {
            'client_name' : 'Adult-MATCH-UAT',
            'client_id' : 'c5dUZ4aL5Bke9DNItN5VzWgcK07Djsh0',
            'url' : 'https://match-uat.nci.nih.gov/api/v1/patients',
            'arms_url' : 'https://match-uat.nci.nih.gov/api/v1/treatment_arms',
            'version' : '2.0'
        },
        'ped' : {
            'client_name' : 'MATCH-Production',
            'client_id' : 'aD7QAC2p8tsR9cd8UZTAMnIEcJrj2tgS',
            'url' : 'https://match-uat.nci.nih.gov/api/v1/patients',
            'arms_url' : 'https://match-uat.nci.nih.gov/api/v1/treatment_arms',
            'version' : '2.0'
        }
    }

    for mb in matchboxes:
        sys.stdout.write('\nConfiguring %s:\n' % mb)
        user = input('\tEnter the username for %s: ' % mb)
        if not user:
            sys.stdout.write('Skipping configuration of %s.\n' % mb)
            continue
        passwd = getpass('\tEnter the password for %s: ' % user)
        matchboxes[mb]['username'] = user
        matchboxes[mb]['password'] = passwd
        config_stump.update({mb : matchboxes[mb]})

    sys.stdout.write('\n')
    write_json(config_stump)

def fix_perms(input_file):
    os.system('chown {} {}'.format(system_user, input_file))

def pre_build_mb_obj(root_dir, matchbox='adult'):
    # TODO: Will need to add a lot more code for handling other systems. For
    # now, we only care about Adult MATCHBox, and so we'll just configure that
    # one.
    """
    First time launch, build a matchbox json dump file and put it into 
    $HOME/.mb_utils.
    """
    datestring=matchbox_api_utils.utils.get_today('short')
    mb_obj_file = os.path.join(root_dir,'mb_obj_' + datestring + '.json')
    ta_obj_file = os.path.join(root_dir,'ta_obj_' + datestring + '.json')
    amoi_lookup_file = os.path.join(root_dir, 
            'amoi_lookup_' + datestring + '.json')
    sys.stdout.write('\nCreating a MATCHBox data dump for quicker lookups.\n')
    sys.stdout.write('NOTE:')
    sys.stdout.write(
        '''
        You can do live queries at any time, but this can take quite a while
        and the use of routinely collected data dumps using matchbox_data_dump
        is preferred and encouraged.

        '''
    )

    call(['bin/matchbox_json_dump.py', matchbox, '-m', mb_obj_file, '-t', 
        ta_obj_file, '-a', amoi_lookup_file])

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
    print('    -> INFO: root dir: %s' % root_dir)
    if not os.path.isdir(root_dir):
        sys.stderr.write('INFO: Creating new MATCHBox API Utils Root dir.\n')
        os.mkdir(root_dir)

        # If we're making the directory here, we have to fix the perms for the
        # system user and not root (called when sudo issued to install pacakge),
        # or else we'll have problems later.
        fix_perms(root_dir)

    sys.stdout.write('\n{0}  MATCHBox API Utils Setup  {0}\n'.format('-'*25))
    make_config_file(root_dir)
    pre_build_mb_obj(root_dir)
    sys.stdout.write('Done with post-install config tasks.\n' + '-'*78 + '\n\n')
