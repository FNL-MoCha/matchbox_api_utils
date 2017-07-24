# -*- coding: utf-8 -*-
import sys
import os
import re
import datetime

import matchbox_api_utils
from matchbox import MatchboxData, Matchbox

__all__ = ['matchbox','matchbox_conf']

mb_utils_root = os.path.join(os.environ['HOME'], '.mb_utils/')

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
            datestring = re.search('mb_obj_([0-9]{6})\.json',filename).group(1)
        except AttributeError:
            datestring = datetime.datetime.fromtimestamp(os.path.getctime(f)).strftime('%m%d%y')
        indexed_files[datestring] = f

    try:
        largest = sorted(indexed_files.keys())[-1]
    except IndexError:
        # there is no MATCHBox JSON Obj here from setup or whatever.
        sys.stderr.write(
            '  -> WARN: No system default MATCHBox DB Obj location. Recommend running "matchbox_json_dump.py" and\n'
            '           storing the resultant file in $HOME/.mb_utils/ for easier work later on.  Alternatively,\n'
            '           you can always do a live query.\n')
        return None
    return indexed_files[largest]


json_files = [os.path.join(mb_utils_root,f) for f in os.listdir(mb_utils_root) if f.endswith('.json')]

mb_data_files = []
for f in json_files:
    if 'config.json' in f:
        mb_config_file = f
    elif os.path.basename(f).startswith('mb_obj'):
        mb_data_files.append(f)

mb_json_data = get_latest_data(mb_data_files)
