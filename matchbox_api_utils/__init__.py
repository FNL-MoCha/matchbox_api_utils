# -*- coding: utf-8 -*-
import sys
import os
import re
import datetime

from matchbox_api_utils.matchbox import Matchbox
from matchbox_api_utils.match_data import MatchData
from matchbox_api_utils.match_arms import TreatmentArms

from ._version import __version__ 

__all__ = ['Matchbox','MatchData','TreatmentArms','matchbox_conf', 'utils']

mb_utils_root = os.path.join(os.environ['HOME'], '.mb_utils')
if not os.path.isdir(mb_utils_root):
    # os.mkdir(mb_utils_root)
    sys.stderr.write('WARN: Can not find the MATCHBox API Utils root dir '
        '"%s". You may need to reconfigure your package!\n')

def get_latest_data(dfiles):
    """
    Get the most recent mb_obj file in the utils dir in the event that there are
    mulitple in there.
    """
    largest = 0
    indexed_files = {}

    for f in dfiles:
        filename = os.path.basename(f)
        try:
            datestring = re.search('(mb|ta)_obj_([0-9]{6})\.json', 
                filename).group(1)
        except AttributeError:
            datestring = datetime.datetime.fromtimestamp(
                    os.path.getctime(f)).strftime('%m%d%y')
        indexed_files[datestring] = f

    try:
        largest = sorted(indexed_files.keys())[-1]
    except IndexError:
        # there is no MATCHBox JSON Obj here from setup or whatever.
        sys.stderr.write(
        """
        -> WARN: No system default MATCHBox DB of TA obj location! Recommend
           running "matchbox_json_dump.py" and storing the resultant file in 
           $HOME/.mb_utils/ for easier work later on. Alternatively, you can 
           always do a live query.
        """
        )
        return None
    return indexed_files[largest]

def get_files(string,file_list):
    return [x for x in file_list if os.path.basename(x).startswith(string)]

if os.path.isdir(mb_utils_root):
    json_files = [
        os.path.join(mb_utils_root, f) 
        for f in os.listdir(mb_utils_root) 
        if f.endswith('.json')
    ]

    # Set up default JSON files.
    for f in json_files:
        if 'mb3.0_config.json' in f:
            mb_config_file = f

    mb_data_files = get_files('mb_obj', json_files)
    mb_json_data = get_latest_data(mb_data_files)

    ta_data_files = get_files('ta_obj', json_files)
    ta_json_data = get_latest_data(ta_data_files)

    amois_files = get_files('amoi_lookup', json_files)
    amoi_json_data = get_latest_data(amois_files)
else:
    sys.stderr.write('Can not initialize default config and db JSON files.\n')
