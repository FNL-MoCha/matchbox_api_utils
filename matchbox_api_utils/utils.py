# -*- coding:utf-8 -*-
# Set of functions that I am commonly using across all classes.
import os
import sys
import re
import json
import datetime
import inspect

from termcolor import colored, cprint
from pprint import pprint

from matchbox_api_utils import matchbox_conf


def load_dumped_json(json_file):
    # Load in a JSON DB file (raw or proc) and return JSON obj and file ctime.
    try:
        date_string = re.search(r'.*?([0-9]+).json$',json_file).group(1)
        formatted_date=datetime.datetime.strptime(
            date_string,'%m%d%y').strftime('%m/%d/%Y')
    except (AttributeError,ValueError):
        creation_date = os.path.getctime(json_file)
        formatted_date=datetime.datetime.fromtimestamp(
                creation_date).strftime('%m/%d/%Y')
    with open(json_file) as fh:
        return formatted_date,json.load(fh)

def get_today(outtype):
    if outtype == 'long':
        return datetime.date.today().strftime('%Y-%m-%d')
    elif outtype == 'short':
        return datetime.date.today().strftime('%m%d%y')

def epoch_to_hr_date(epoch_date):
    return datetime.datetime.fromtimestamp(epoch_date).strftime('%Y-%m-%d')

def get_vals(d, *v):
    # return a value or list of values
    return [d.get(i, '---') for i in v]

def map_histology(data, *, medra=None, histology=None):
    if medra:
        ctep_name = data.get(medra, None)
        if ctep_name is None:
            sys.stderr.write('No disease with MEDRA code "%s" was found in '
                'the MATCH dataset.\n')
            return None
        else:
            return ctep_name
    elif histology:
        for key, val in data.items():
            if val == histology:
                # OK to just assign it here, since I know the codes have to 
                # be unique
                return key
    else:
        return data
                    
def make_json(*, outfile, data, sort=True):
    with open(outfile, 'w') as fh:
        json.dump(data, fh, sort_keys=sort, indent=4)

def print_json(data):
    return json.dumps(data, sort_keys=True, indent=4)

def read_json(json_file):
    with open(json_file) as fh:
        return json.load(fh)

def pp(data):
    pprint(data, stream=sys.stderr)

def map_fusion_driver(gene1, gene2):
    # From two gene ids derived from a fusion identifier or the like, determine
    # which is the driver and which is the partner.
    drivers = ['ABL1', 'AKT2', 'AKT3', 'ALK', 'AR', 'AXL', 'BRAF', 'BRCA1', 
        'BRCA2', 'CDKN2A', 'EGFR', 'ERBB2', 'ERBB4', 'ERG', 'ETV1', 'ETV1a',
        'ETV1b', 'ETV4', 'ETV4a', 'ETV5', 'ETV5a', 'ETV5d', 'FGFR1', 
        'FGFR2', 'FGFR3', 'FGR', 'FLT3', 'JAK2', 'KRAS', 'MDM4', 'MET', 
        'MYB', 'MYBL1', 'NF1', 'NOTCH1', 'NOTCH4', 'NRG1', 'NTRK1', 'NTRK2',
        'NTRK3', 'NUTM1', 'PDGFRA', 'PDGFRB', 'PIK3CA', 'PPARG', 'PRKACA',
        'PRKACB', 'PTEN', 'RAD51B', 'RAF1', 'RB1', 'RELA', 'RET', 'ROS1', 
        'RSPO2', 'RSPO3', 'TERT']

    # handle intragenic fusions
    if gene1 in ['MET','EGFR']:
        driver = partner = gene1

    # figure out others.
    if gene1 in drivers:
        (driver, partner) = (gene1, gene2)
    elif gene2 in drivers:
        (driver, partner) = (gene2, gene1)
    elif gene1 in drivers and gene2 in drivers:
        driver = partner = 'NA'
    elif gene1 not in drivers and gene2 not in drivers:
        driver = partner = 'NA'
    return driver, partner

def __exit__(line=None, msg=None):
    '''
    Better exit method than sys.exit() since we can determine just where the 
    exit was called in the script.  This is useful for development where we 
    want to term the script at various phases during writing / testing, and can
    often lose track.
    '''
    if line is None:
        # filename = inspect.stack()[1][1]
        # line = inspect.stack()[1][2]
        # function = inspect.stack()[1][3]
        filename, line, function = inspect.stack()[1][1:4]
    output = ('Script "{}" stopped in `{}()` at line: {} with message: '
       '"{}".'.format(os.path.basename(filename), function, line, msg))
    sys.stderr.write('\n')
    cprint(output, 'white', 'on_green', attrs=['bold'], file=sys.stderr)
    sys.exit()

def msg(msg, verbosity):
    if verbosity == 0:
        return
    else:
        sys.stderr.write(msg)
        sys.stderr.flush()
