try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

config = {
    'name'                   : 'matchbox_api_utils',
    'description'            : ('MATCHBox API utlilites package to retrieve and analyze variant, patient, and disease information'
                                'from MATCHBox in a quick and informative way.'),
    'version'                : '0.9.8_032817',
    'author'                 : 'Dave Sims',
    'author_email'           : 'simsdj@mail.nih.gov',
    'download_url'           : 'https://github.com/drmrgd/matchbox_api_utils.git',
    'install_requires'       : ['nose'],
    'packages'               : ['Matchbox'],
    'scripts'                : [],
}

setup(**config)
