##################
MATCHBox API Utils
##################

MATCHBox API Utils is a Python3 package designed to interact with the NCI-MATCHBox
system, and is intended to offer a simple, programmatic way to retrieve results
from the system for larger scale cohort analyses.  While the UI of the system is 
quite nice and robust, clicking through many windows to gather data one wants can
be challenging, and the hope is that this tool will fill in the gaps.

Note that access to this system is limited to authorized users, and access 
credentials must be obtained and configured in order to use this package.  A full
set of documentation on this package can be found `here 
<http://matchbox_api_utils.readthedocs.io>`_.  

Installation
------------

The most simple way to install this is using the included Python ``setup.py`` 
script by running: ::

    $ sudo python3 setup.py install

.. note:
    Only will need `sudo` for system wide isntalls of course. Also, note that PIP
    will not work for this package at the moment since it seems to get a little 
    crabby with the postinstaller scripts.

Once setup is running, you'll have to configure the package with a postinstaller
script. Again, consult the larger documentation for specifics.
