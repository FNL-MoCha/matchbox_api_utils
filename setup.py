#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys, os
import re
from setuptools import setup
from setuptools.command.install import install as _install
from subprocess import call

version_file = 'matchbox_api_utils/_version.py'
exec(open(version_file).read())

def _post_install(dir):
    call([sys.executable, 'postinstall.py'])
        

class install(_install):
    def run(self):
        _install.do_egg_install(self)
        self.execute(_post_install, (self.install_lib,), 
                msg="Running post install task")
        
def readme():
    with open('README.rst') as fh:
        return fh.read()

config = {
    'name'                 : 'matchbox_api_utils',
    'description'          : ('MATCHBox API Utlilites Package'),
    'long_description'     : readme(),
    'version'              : __version__,
    'author'               : 'Dave Sims',
    'author_email'         : 'david.sims2@nih.gov',
    'download_url'         : 'https://github.com/drmrgd/matchbox_api_utils.git',
    'url'                  : 'https://github.com/drmrgd/matchbox_api_utils.git',
    'test_suite'           : 'nose.collector',
    'tests_require'        : ['nose'],
    'packages'             : ['matchbox_api_utils'],
    'python_requires'      : '>=3.6',
    'install_requires'     : ['requests',
                              'asyncio',
                              'termcolor'
                             ],
    'scripts'              : ['bin/map_msn_psn.py',
                              'bin/matchbox_json_dump.py',
                              'bin/match_variant_frequency.py',
                              'bin/matchbox_patient_summary.py',
                             ],
    'include_package_data' : True,
    'zip_safe'             : False,
    'license'              : 'MIT',
    'cmdclass'             : {'install' : install}
}

setup(**config)
