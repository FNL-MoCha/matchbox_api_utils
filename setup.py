import sys, os
from setuptools import setup
# from distutils.command.install import install as _install
from setuptools.command.install import install as _install

version = '0.9.19a1'

class install(_install):
    def run(self):
        pass
        _install.run(self)
        self.execute(_post_install, (self.install_lib,),
        msg="Running post install task")
        
def _post_install(dir):
    from subprocess import call
    call([sys.executable, 'postinstall.py'])

def readme():
    with open('README.rst') as fh:
        return fh.read()

config = {
    'name'                   : 'matchbox_api_utils',
    'description'            : ('MATCHBox API Utlilites Package'),
    'long_description'       : readme(),
    'version'                : version,
    'author'                 : 'Dave Sims',
    'author_email'           : 'david.sims2@nih.gov',
    'download_url'           : 'https://github.com/drmrgd/matchbox_api_utils.git',
    'url'                    : 'https://github.com/drmrgd/matchbox_api_utils.git',
    'test_suite'             : 'nose.collector',
    'tests_require'          : ['nose'],
    'packages'               : ['matchbox_api_utils'],
    'install_requires'       : ['setuptools', 'requests'],
    'cmdclass'               : {'install' : install},
    'scripts'                : ['bin/map_msn_psn.py',
                                'bin/matchbox_json_dump.py',
                                'bin/match_specimen_tracking.py',
                                'bin/match_variant_frequency.py',
                                'bin/matchbox_patient_summary.py',
                               ],
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
