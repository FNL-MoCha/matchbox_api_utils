import sys,os
__all__ = ['matchbox','matchbox_conf']
import matchbox_api_utils
from matchbox import MatchboxData, Matchbox

mb_utils_root = os.path.join(os.environ['HOME'], '.mb_utils/')
mb_config_file = os.path.join(mb_utils_root, 'config.json')
mb_json_data = os.path.join(mb_utils_root, 'mb_obj.json')

__version__ = '0.11.0'
