#!/usr/local/bin/python3
# Starting with a data dump from MATCHBox, which should contain the path to the VCF file as the last column,  using 
# the api script copy all VCFs to a new directory.  
#
# TODO: 
#   We can add some more functionality by calling matchbox_api_retrieve.py directly and getting the data dump file, 
#   Also add input for dest directory as a CLI opt.
#
# 4/27/2016 - D Sims
#########################################################################################################################
import sys
import os
import re
import shutil
import json
from pprint import pprint as pp

version = 'v1.2.121916'

def read_file(input_file):
    paths = []
    with open(input_file) as fh:
        data = json.load(fh)
        for elem in data:
            try:
                vcf_path = data[elem]['vcf_path']
            except KeyError:
                continue
            paths.append(vcf_path)
    return paths

def munge_paths(paths,dest):
    picklist = []
    for path in paths:
        path_elems = path.split('/')
        patient = path_elems[5]
        psn = 'PSN'+patient.split('-')[1]

        vcf_name = path_elems[8]
        # print('name  => {}'.format(vcf_name))
        vcf_elems = vcf_name.split('_')
        if vcf_elems[0].startswith('MSN'):
            msn = vcf_elems[0]
        else:
            print("error handling line: {}".format(vcf_name))
            sys.exit()
        
        version = vcf_elems[1]
        if version.startswith('v'):
            new_vcf_name = '_'.join([psn, msn, version]) + '.vcf'
        else:
            new_vcf_name = '_'.join([psn, msn]) + '.vcf'
        source_path = '/Volumes/Promise_Pegasus/matchbox_prod/' + '/'.join(path_elems[5:])
        final_path = os.path.join(dest,new_vcf_name)
        picklist.append((source_path,final_path))
    return picklist

def copy_files(picklist):
    for items in picklist:
        sys.stdout.write("copying {} -> {}...".format(items[0], items[1]))
        shutil.copy(items[0],items[1])
        sys.stdout.write('Done!\n')

def user_query(query, default='no'):
    valid_reponses = {
        'yes' : True, 
        'y'   : True, 
        'no'  : False, 
        'n'   : False,
        'r'   : 'rename',
        'rename' : 'rename'
     }
    prompt = ' [yes | No | rename]: '

    while True:
        sys.stdout.write(query + prompt)
        choice = input().lower()
        if choice == '':
            return valid_reponses['n']
        elif choice in valid_reponses:
            return valid_reponses[choice]
        else:
            sys.stderr.write('Invalid choice {}! Please choose from "yes", "no", or "rename"\n'.format(choice))

def main():
    picklist = [] 
    try:
        file_paths = read_file(sys.argv[1])
    except IndexError:
        sys.stderr.write("ERROR: No data dump file loaded!\n")
        sys.exit(1)

    # TODO: Rewrite with argparse module.
    try:
        dest_dir = sys.argv[2]
    except IndexError:
        dest_dir = os.getcwd()

    if os.path.exists(dest_dir):
        print("Destination path exists.")
        # for dirpath, dirnames, files in os.walk('.'):
        for dirpath, dirnames, files in os.walk(dest_dir):
            if files:
                sys.stderr.write(
                    "WARN: destination dir '{}' not empty! Continuing will overwrite existing data!".format(dest_dir)
                )
                choice = user_query(' Continue?') 
                if choice == 'rename':
                    new_name = input('new name? ')
                    dest_dir = os.path.join(os.path.dirname(dest_dir),new_name)
                    break
                elif choice:
                    sys.stdout.write("Overwriting old data...\n")
                    break
                else:
                    sys.stderr.write("Exiting to be safe!\n")
                    sys.exit(1)
    else:
        sys.stdout.write("Creating directory for new data...")
        os.mkdir(dest_dir)
        sys.stdout.write("Done!")

    picklist = munge_paths(file_paths,dest_dir)
    copy_files(picklist)

if __name__=='__main__':
    main()
