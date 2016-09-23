#!/usr/bin/python
import sys
import os
import json
import csv
from pprint import pprint as pp
from Matchbox import *

def jprint(data):
    print json.dumps(data, indent=4, sort_keys=True)

def summary(mb_data):
    '''
    Generate a quickie summary report of MATCH patients that have been biopsied and the counts for each disease type.
    '''
    total, diseases = mb_data.get_patient_summary()
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
    print "Testing from {}...".format(os.path.basename(__file__))
    url = 'https://matchbox.nci.nih.gov/match/common/rs/getPatients'
    creds = {
        'username' : 'trametinib',
        'password' : 'COSM478K601E',
    }
    # data = MatchboxData(url,creds)
    # Uncomment if we need to just dump MATCHBox in to a JSON
    # data._matchbox_dump()
    # sys.exit()
    data = MatchboxData(url,creds,'mb.json')
    
    query_list = {
        'indels' : ['BRCA1','BRCA2','ATM'],
        'snvs'   : ['IDH1'],
        'cnvs'   : ['CCNE1','EGFR']
    }
    query_data = data.find_variant_frequency(query_list)
    # jprint(query_data)
    # sys.exit()

    outfile = open('test.csv', 'w')
    csv_writer = csv.writer(outfile,delimiter=',',quotechar='"')
    header = ['Patient','Disease','Gene','Type','Measurement','Transcript','CDS','AA','Function']
    csv_writer.writerow(header)

    for patient in query_data:
        for moi in query_data[patient]['mois']:
            if moi['type'] == 'snvs_indels':
                var_data = parse_query_results(moi,'snv')
                csv_writer.writerow([query_data[patient]['psn'],query_data[patient]['disease']]+var_data)
            elif moi['type'] == 'cnvs':
                var_data = parse_query_results(moi,'cnv')
                csv_writer.writerow([query_data[patient]['psn'],query_data[patient]['disease']]+var_data)
            elif moi['type'] == 'fusions':
                var_data = parse_query_results(moi,'fusion')
                csv_writer.writerow([query_data[patient]['psn'],query_data[patient]['disease']]+var_data)

