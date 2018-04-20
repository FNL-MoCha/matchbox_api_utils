MATCHBox API Utils
++++++++++++++++++

Introduction
============

Retrieving results from the MATCHBox, an NCI derived system to collect, collate,
and report data from the NCI-MATCH study can be a difficult task.  While there is
a rich API and set of tools underlying the user interfact (UI), it can be very 
difficult at times to quickly gleen the information one is looking for from clicking
through all of the web pages.  This is where MATCHBox API Utils comes in.

The system is designed to directly pull data from a live MATCHBox instance, and 
build a simple JSON file, from which a whole host of methods have been created
to access, filter, interrogate, report, etc. the data.  For example, if you wanted
to know which MSNs were associated with patient identifier (PSN) 13070, you could 
click through the GUI, and find the correct data.  Or, with this tool, you can 
simply run: ::

    >>> from matchbox_api_utils import MatchData
    >>> data = MatchData(matchbox='adult-matchbox')
    >>> data.get_msn(psn=13070)
    [u'MSN31054', u'MSN59774']

More on the specifics of how to use these modules and methods a little later.

Also, along with the set of Python modules and methods, included is a set of 
`helper` scripts that will act as nice wrappers around some of these basic 
methods.  For example, running the ``map_msn_psn.py`` script that's a part of this
package will generate really nice tables of data, allow for batch processing from
either a list input on the commandline or a file containing a set of identifiers
of interest. ::

    $ map_msn_psn.py -t MSN MSN31054,MSN12724,MSN37895,MSN12104

    Getting MSN / PSN mapping data...

    PSN,BSN,MSN
    PSN10818,T-16-000029,MSN12104
    PSN10955,T-16-000213,MSN12724
    PSN13070,T-16-002251,MSN31054
    PSN13948,T-16-003010,MSN37895


Installation
============

At this time, the most simple installation is to unzip the provided tarball, and 
run: ::

    python setup.py install

From here, the installer will add the library modules to your standard Python
library location, put the helper scripts into the standard binary direcotry in
your ``$PATH``, and run a post installation script that will set up the appropriate
URLs, username, and password for your system and user.  At the end, a new set of 
JSON files will be created in ``$HOME/.mb_utils/`` which will contain the initial
MATCH dataset for use.  

.. note::
    Alternatively, one can install with Python ``easy_install``, but there may 
    be some issues with the postinstaller script, and so this method is not 
    preferred.

We recommend re-building this dataset on occassion using the 
``matchbox_json_dump.py`` program included in the package for up to date data,
especially as the dataset is not yet locked down. Additionally, one can keep old
sets of these JSON databases for use at any time (e.g comparing version data), by
inputting the custom JSON into the MatchData object (see: ``matchbox_api_utils``
API documentation for details).


Requirements
============

These modules require Python >=3.5 to run, although backwards compatible Python
v2.7 was used where possible. Your mileage may vary with the helper scripts 
somewhat.  

In addition to the above, the package requires the installation of:

    - `requests <http://docs.python-requests.org/en/master/>`_
    - `asyncio <https://docs.python.org/3/library/asyncio.html>`_
    - `termcolor <https://pypi.org/project/termcolor/>`_

The setup script should take care of this dependency upon installation.  

.. todo::
    Verify in a clean environment that we added all required packages and 
    environment defaults.

Using MATCHBox API Utils
========================

Once the installation is run, one can either use the pre-built scripts 
available in your systems binary directory (see Helper Scripts documentation
), or write your own scripts using any one of the included methods (see the 
MATCHBox API Utils API documentation).
