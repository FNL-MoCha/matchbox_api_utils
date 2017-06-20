#!/usr/bin/env python
# From MATHCBox API generate a current list of all MSNs and some parent information (PSN, BSN, collection Date,
# site to which nucleic acid sent, etc.).  
#
# 12/15/2016 - D Sims
################################################################################################################
import sys
import os
import json
import requests
from pprint import pprint as pp
from collections import defaultdict

from matchbox_api_utils.Matchbox import MatchboxData

version = '1.0.0_121616'

class Config(object):
    '''Read in a config file and return JSON obj that we can use to modify our credentials and whatnot.'''
    def __init__(self,config_file):
        self.config_file = config_file
        self.config_data = Config.read_config(self.config_file)

    def __repr__(self):
        return '%s:%s' % (self.__class__,self.__dict__)

    def __str__(self):
        return json.dumps(self.config_data,sort_keys=True,indent=4)

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

def trim_timestamp(val):
    return val.split('T')[0]

def parse_json(data):
    results = defaultdict(dict)

    for patient in data:
        for biopsy in patient['biopsies']:
            for sample in biopsy['samples']:
                msn = sample['molecularSequenceNumber']
                results[msn]['msn']       = msn
                results[msn]['psn']       = patient['patientSequenceNumber']
                results[msn]['lab']       = sample['lab']
                results[msn]['ship_date'] = trim_timestamp(sample['dnaShippedDate'])
                results[msn]['bsn']       = biopsy['biopsySequenceNumber']
                results[msn]['col_date']  = trim_timestamp(biopsy['specimenReceivedDate'])
    return results

def print_results(data):
    '''For now just make it comma delimited so that we can import in Excel. Can get fancy later'''
    want_list = ['msn','bsn','psn','lab','col_date','ship_date']
    print(','.join(want_list))
    for msn in data:
        out_data = [data[msn][x] for x in want_list]
        print(','.join(out_data))

def main():
    #TODO: Let's make this a part of the setup package.  We can enforce a config file in 
    #      $HOME, but if not there, then one in the cwd.  Else throw an error and encourage
    #      to re-run setup.
    config_file = os.path.join(os.environ['HOME'], '.mb_utils/config.json')
    if not os.path.isfile(config_file):
        config_file = os.path.join(os.getcwd(), '/config.json')

    try:
        config_data = Config(config_file)
    except IOError:
        sys.stderr.write('ERROR: Can not find a config file in $HOME/.mb_utils or the current working directory.  You must create a config file to continue!\n')
        sys.exit(1)
    except:
        sys.stderr.write('ERROR: Can not read file %s. Check that file is intact and recreate if necessary!\n' % config_file)
        sys.exit(1)

    sys.stdout.write('Retrieving a JSON of MATCH specimen tracking info...')
    sys.stdout.flush()

    match_data = MatchboxData(config_data['manifest_url'],config_data['creds'])
    sys.stdout.write('Done!\n')
    parsed_data = parse_json(match_data)
    print_results(parsed_data)
    
    '''
    This is test case with outside JSON file to save dev time.  Can delete once this all works
    jfile = 'specimen_tracking.json'
    with open(jfile) as fh:
        match_data = json.load(fh)
        parsed_data = parse_json(match_data)
    print_results(parsed_data)
    '''
if __name__=='__main__':
    print(
        '''This script has some issues.  I am accessing MATCHBox through a different URL this time for some reasont that I don't remember.  I think I need to 
           revisit this in a big way ti remmember just what I was trying to do here.  For now, just bail on this.
        '''
    )
    sys.exit()
    main()
