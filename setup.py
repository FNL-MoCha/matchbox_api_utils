try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

def readme():
    with open('README.rst') as fh:
        return fh.read()

config = {
    'name'                   : 'matchbox_api_utils',
    'description'            : ('MATCHBox API utlilites package to retrieve and analyze variant, patient, and disease information'
                                'from MATCHBox in a quick and informative way.'),
    'long_description'       : readme(),
    'version'                : '0.9.8a1',
    'author'                 : 'Dave Sims',
    'author_email'           : 'simsdj@mail.nih.gov',
    'download_url'           : 'https://github.com/drmrgd/matchbox_api_utils.git',
    'url'                    : 'https://github.com/drmrgd/matchbox_api_utils.git',
    'test_suite'             : 'nose.collector',
    'tests_require'          : ['nose'],
    'packages'               : ['matchbox_api_utils'],
    'scripts'                : ['bin/map_msn_psn.py'],
    'include_package_data'   : True,
    'zip_safe'               : False,
    'license'                : 'MIT',
    'classifiers'            : [
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Development Status :: 2 - Alpha',
    ],
}

setup(**config)
