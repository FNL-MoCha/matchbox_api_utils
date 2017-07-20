import sys
import os
import re
import matchbox_api_utils
from matchbox import MatchboxData, Matchbox

__all__ = ['matchbox','matchbox_conf']

#mb_config_file = os.path.join(mb_utils_root, 'config.json' 
#mb_json_data = os.path.join(mb_utils_root, 'mb_obj.json')

def get_latest_data(dfiles):
    largest = 0
    for f in dfiles:
        datestring = re.search('mb_obj_([0-9]{6})\.json',f).group(1)
        if int(datestring) > int(largest):
            largest = datestring
    for f in dfiles:
        if largest in f:
            return f

mb_utils_root = os.path.join(os.environ['HOME'], '.mb_utils/')

dir_contents = os.listdir(mb_utils_root)
json_files = [f for f in dir_contents if f.endswith('.json')]

mb_data_files = []
for f in json_files:
    if f == 'config.json':
        mb_config_file = os.path.join(mb_utils_root,f)
    elif f.startswith('mb_obj'):
        mb_data_files.append(f)

mb_json_data = os.path.join(mb_utils_root,get_latest_data(mb_data_files))

__version__ = '0.11.1'
