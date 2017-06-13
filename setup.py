import sys, os
try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

def readme():
    with open('README.rst') as fh:
        return fh.read()

version = '0.9.14a1'

config = {
    'name'                   : 'matchbox_api_utils',
    'description'            : ('MATCHBox API utlilites package to retrieve variant, patient, and disease information'
                                'from MATCHBox in a quick and informative way.'),
    'long_description'       : readme(),
    'version'                : version,
    'author'                 : 'Dave Sims',
    'author_email'           : 'simsdj@mail.nih.gov',
    'download_url'           : 'https://github.com/drmrgd/matchbox_api_utils.git',
    'url'                    : 'https://github.com/drmrgd/matchbox_api_utils.git',
    'test_suite'             : 'nose.collector',
    'tests_require'          : ['nose'],
    'packages'               : ['matchbox_api_utils'],
    'install_requires'       : ['setuptools', 'requests'],
    'scripts'                : ['bin/map_msn_psn.py',
                                'bin/matchbox_json_dump.py',
                                'bin/match_specimen_tracking.py',
                                'bin/match_variant_frequency.py',
                                'bin/matchbox_patient_summary.py',
                               ],
    'data_files'             : [(os.environ['HOME']+'/.mb_utils/', ['config.json'])],
    'include_package_data'   : True,
    'zip_safe'               : False,
    'license'                : 'MIT',
    'classifiers'            : [
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Development Status :: 2 - Alpha',
    ],
}

setup(**config)
