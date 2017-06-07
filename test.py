#!/usr/bin/env python
import sys
import os
import json
import csv
from pprint import pprint as pp
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

def jprint(data):
    print json.dumps(data, indent=4, sort_keys=True)

def summary(mb_data):
    '''
    Generate a quickie summary report of MATCH patients that have been biopsied and the counts for each disease type.
    '''
    total, diseases = mb_data.get_disease_summary()
    print ":::  MATCH Patient Summary as of 9/21/2016  (Total Screened: {})  :::\n".format(total)
    print "DISEASE STATS"
    for elem in diseases:
        print "\t".join([elem,str(diseases[elem])])
    return

def parse_query_results(data,vartype):
    wanted_data = []
    if vartype == 'snv':
        wanted_data = ['gene','type','alleleFrequency','transcript','hgvs','protein','oncominevariantclass']
    elif vartype == 'cnv':
        wanted_data = ['gene','type','copyNumber']
    elif vartype == 'fusion':
        wanted_data = ['gene','type','driverReadCount']
    return map(data.get,wanted_data)


if __name__=='__main__':
    config_file = 'config.json'
    config_data = Config.read_config(config_file)

    '''
    patient = '10896' # PIK3CA_snv, APC_snv, KRAS_snv, METe14_fusion
    patient = '11070' # ETV6-NTRK3_fusion
    plist = [10045,10051,10244,10929,11035,11105,11582]
    patients = map(str,plist) 
    '''

    patient='14032'
    # patient=None
    # NEW: Can dump out a raw unfiltered JSON by passing a raw_dump value to the MatchboxData constructor
    # data = MatchboxData(config_data['url'],config_data['creds'],None,patient,'raw_dump')
    data = MatchboxData(config_data['url'],config_data['creds'],None,patient)
    # data = MatchboxData(config_data['url'],config_data['creds'],'mb_101816.json')
    summary(data)
    sys.exit()

    # filtered = data.get_patients_and_disease(patients)
    filtered = data.get_patients_and_disease()
    for pt in filtered:
        print ','.join(pt)
    sys.exit()
