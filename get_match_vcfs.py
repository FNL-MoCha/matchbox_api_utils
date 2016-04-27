#!/usr/bin/python
# Starting with a data dump from MATCHBox, which should contain the path to the VCF file as the last column,  using the api script
# copy all VCFs to a new directory.  
#
# TODO: 
#   We can add some more functionality by calling matchbox_api_retrieve.py directly and getting the data dump file, 
#   Also add input for dest directory as a CLI opt.
#
# 4/27/2016 - D Sims
#######################################################################################################################################
import sys
import os
import re
import shutil
from pprint import pprint

version = 'v1.0.042716'

def read_file(input_file):
    paths = []
    with open(input_file) as fh:
        for line in fh:
            elems = line.rstrip('\n').split('\t')
            paths.append(elems[8])
    return paths

def munge_paths(paths):
    picklist = []
    for path in paths:
        path_elems = path.split('/')
        patient = path_elems[5]
        psn = 'PSN'+patient.split('-')[1]
        vcf_name = path_elems[8]
        msn,version = re.match('^(MSN[0-9]+).*(v[0-9]).*$',vcf_name).group(1,2)
        new_vcf_name = '_'.join([psn, msn, version]) + '.vcf'
        source_path = '/Volumes/prod/' + '/'.join(path_elems[5:])
        final_path = '/Users/simsdj/match_vcfs/{}'.format(new_vcf_name)
        picklist.append((source_path,final_path))
    return picklist

def copy_files(picklist):
    for items in picklist:
        sys.stdout.write("copying {} -> {}...".format(items[0], items[1]))
        shutil.copy(items[0],items[1])
        sys.stdout.write('Done!\n')

def main():
    picklist = [] 
    try:
        file_paths = read_file(sys.argv[1])
    except IndexError:
        sys.stderr.write("ERROR: No data dump file loaded!\n")
        sys.exit(1)

    picklist = munge_paths(file_paths)
    copy_files(picklist)

if __name__=='__main__':
    main()
