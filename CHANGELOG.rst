#########
Changelog
#########

List of notable changes to master release of this code should be documented 
here. Hopefully I can keep up with this!

-------------------------
[1.3.030118] - 2018-03-01
-------------------------

    - Added full set of documentation, including a html version (to be hosted 
      on readthedocs in the near future and as a part of the upcoming Github 
      repository), as well as a PDF and Man pages version.

    - Minor code tweaks to fix a few bugs here and there. 

    - Code cleanup to help better adhere to standard PEP requirements.

-------------------------
[1.2.021418] - 2018-02-14
-------------------------
    
    - Fixed some issues with `setup.py`. Was not properly configuring every 
      component, especially with regard to setting up requirements.

    - Changed location of `root_dir` definition from `postinstaller` to 
      `__init__`. Was having problems with `setup.py` when not defined in
      `__init__`.

    - Minor code refactoring and cleanup.

-------------------------
[1.0.021418] - 2018-02-14
-------------------------

    - Removed failed biopsies from output when calling ``MatchData.get_bsn()``.
    - Fixed PSN mapping if one does not use PSN string in name.
    - Fixed bug with file handle creation for output.

--------------------------
[0.22.012218] - 2018-01-22
--------------------------

    - Added ``MatchData.get_ihc_results()``. This method will return IHC data 
      results based on an input patient identifier.
    - Added back variant measurements (VAF, CN, Read Counts) to 
      ``MatchData.find_variant_frequency()``.  Not sure anymore why I dropped it 
      in the first place!

--------------------------
[0.21.011818] - 2018-01-18
--------------------------

    - Added "outside confirmation" to list of things to skip in processing / output.
    - Fixed all method calls to new versions in the ``match_data`` module.
    - Fixed ``MatchData.find_variant_frequency()`` for the following:
          * Better handle outside assay results; we now skip them!
          * Changed order of counts in output.
          * Output a patient based conter and biopsy based counter. This is to help
            discern between progression biopsy cases.
    - Added MEDRA code to CTEP Disease identifier lookup method.
    - Completely overhauled ``MatchData.get_disease_summary()``.  Method now:
          * Handles queries better and more efficiently.
          * Now outputs MEDRA code information.
          * Output format cleaned up 
    - Added ID and counts output for ``MatchData.get_biopsy_summary()``.
    - Fixed bug with PSN string stripping in ``MatchData.find_variant_frequency()``

---------------------
[0.20.0] - 2017-10-27
---------------------

    - Updated and wrote package tests.
    - Added warning for no matches when looking at non-outside assay cases. Not
      ideal, but as the backend of MATCHBox becomes less and less reliable due to 
      this really dumb Outside Assays thing, I need better messages than just 
      generic Python stack trace errors.
    - Added Python 3 compatibility.  At the moment don't want to force python3 on
      to users (some may find it difficult to install), but I want this to 
      ultimately be totally run under Python 3. Should only need some small tweaks
      once this goes full python 3.
    - Change main ``MatchData`` api constuctor to use `sys_default` JSON file of 
      data rather than doing a live query.  This will really speed things up, and 
      now that MATCHBox data is becoming more and more stable as incoming data 
      slows down, this is perfectly fine.
    - Added ``MatchData.get_patient_by_disease()`` method to, well, get patient
      by disease!
    
---------------------
[0.19.1] - 2017-10-03
---------------------

    - Updated tests.
    - Some minor tweaks to new data structure added.
    - Complete overhaul on ``MatchData.get_histology()``. Working much more smoothly
      now!
    - Changed some internal private methods to better handle new data formats and 
      add better functionality to internal queries. 

---------------------
[0.18.0] - 2017-09-28
---------------------

    - Completely overhauled the data structure so that we can now better handle
      multiple biopsies and NGS results (i.e. MSNs) for the same patient. Cases
      where there were progression biopsies and the like were breaking methods.
    - Refactored key methods like:

          * ``MatchData.get_psn()``
          * ``MatchData.get_bsn()``
          * ``MatchData.get_msn()``
          * ``MatchData.variant_frequencey()``
          * ``MatchData.get_biopsy_summary()``

      Not a complete list, but good representation.  These methods now use the new
      data structure to better represent results, and in cases like MSN return,
      output data as lists since we know we can have multiple MSNs / PSN.

---------------------
[0.17.0] - 2017-09-22
---------------------

    - Updated tests.
    - Fixed some status reporting bugs, including a hardcoded (and not ideal!) fix
      for 4 odd `compassionate care` cases for Arm P. Still need to remove soem 
      debugging code, but will leave that until 100% sure this is all correct.
    - Added ``MatchData.get_patient_meta()`` a method to just return raw chunks
      of JSON file data for a patient based on an input key. This is mainly for 
      debugging and devlopment and may end up being privatized in release versions.
    - Code clean up and finishing patient level TA data in method calls.

---------------------
[0.16.0] - 2017-09-19
---------------------

    - Created a new ``treatment_arms`` module with a ``TreatmentArms()`` class
      that will allow for adding treatment arm data and aMOI rules assignment. As
      a part of arm compilation work, needed to know what was an aMOI and what was
      not!
    - Started project documentation by adding better python docstrings to code
      (really just updating and making better what I had already written), and 
      adding things in like this CHANGELOG.  Will begin experimenting with the
      Sphinx documentation system soon to figure out how to make really nice
      release docs as I'm anticipating many people ultimately using these tools.
      Well...hopefully!
