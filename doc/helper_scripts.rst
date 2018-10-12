MATCHBox API Utils Helper Scripts
=================================
Included in the package are a few pre-made helper scripts for routine work. In
general you'll get more mileage out of just loading the modules and rolling 
your own.  However, there are some very frequent use cases where one of these 
pre-made scripts might be helpful.

MATCHBox JSON Dump (matchbox_json_dump.py)
------------------------------------------
Get a dataset from MATCHBox and dump as a JSON object that we can use
later on to speed up development and periodic searching for data.

This is the script that is run during the post installer, and something that 
should be run on a periodic basis to take advantage of new MATCHBox data entered
into the system (at least until lockdown occurs).  This will put the resultant
JSON file into the current directory, where it should probably be migrated into 
``$HOME/.mb_utils/`` to be picked up by the rest of the system.

.. note::
    The older JSON database files are retained with the new one, and as such
    can be loaded into the API at any time, in the event that one requires
    older data.

MATCHBox JSON Dump Help Doc
***************************
.. code-block:: python

    usage: matchbox_json_dump.py [-h] [-d <raw_mb_datafile.json>] [-r] [-p <psn>]
                                 [-t <ta_obj.json>] [-a <amoi_obj.json>]
                                 [-m <mb_obj.json>] [-c <connection_method>] [-v]
                                 <matchbox>

    positional arguments:
      <matchbox>            Name of MATCHBox to which we make the file. Valid
                            systems are: "adult", "adult-uat", "ped".

    optional arguments:
      -h, --help            show this help message and exit
      -d <raw_mb_datafile.json>, --data <raw_mb_datafile.json>
                            Load a raw MATCHBox database file (usually after
                            running with the -r option).
      -r, --raw             Generate a raw dump of MATCHbox for debugging and dev
                            purposes.
      -p <psn>, --patient <psn>
                            Patient sequence number used to limit output for
                            testing and dev purposes
      -t <ta_obj.json>, --ta_json <ta_obj.json>
                            Treatment Arms obj JSON filename. DEFAULT:
                            ta_obj_<datestring>.json
      -a <amoi_obj.json>, --amoi_json <amoi_obj.json>
                            aMOIs lookup filename. DEFAULT:
                            "amois_lookup_<datestring>.json".
      -m <mb_obj.json>, --mb_json <mb_obj.json>
                            Name of Match Data obj JSON file. DEFAULT:
                            "mb_obj_<datestring>.json".
      -c <connection_method>, --connection <connection_method>
                            Connection method used to access MATCHBox data. Choose
                            from either "api" or "mongo". DEFAULT: mongo
      -v, --version         show program\'s version number and exit
      

Note that we can either retrieve a small, parsed JSON object of data, or we can 
get an entire dump of the raw MATCHBox for things like development and testing, 
or troubleshooting.


MAP MSN PSN (map_msn_psn.py)
----------------------------

Input a MSN, BSN, or PSN, and return the other identifiers. Useful when trying
to retrieve the correct dataset and you only know one piece of information.
Note: We are only working with internal BSN, MSN, and PSN numbers for now and
can not return Outside Assay identifiers at this time.

.. note::
    We are only working with internal BSN, MSN, and PSN numbers for now and
    can not return Outside Assay identifiers at this time.

MAP MSN PSN Help Doc
********************

.. code-block:: python

    usage: map_msn_psn.py [-h] -t {psn,msn,bsn} [-l] [-f <input_file>]
                          [-o <outfile>] [-v]
                          <matchbox> [<IDs>]

    positional arguments:
      <matchbox>            Name of MATCHBox to which we make the connection.
                            Valid systems are: "adult", "adult-uat", "ped".
      <IDs>                 MATCH IDs to query. Can be single or comma separated
                            list. Must be used with PSN or MSN option.

    optional arguments:
      -h, --help            show this help message and exit
      -t {psn,msn,bsn}, --type {psn,msn,bsn}
                            Type of query string input. Can be MSN, PSN, or BSN
      -l, --live            Make a live call to MATCHbox instead of relying on
                            local JSON database. This is especially helpful for
                            newly sequenced patients since the last dump.
      -f <input_file>, --file <input_file>
                            Load a batch file of all MSNs or PSNs to proc
      -o <outfile>, --outfile <outfile>
                            File to which output should be written. Default:
                            STDOUT.
      -v, --version         show program\'s version number and exit

MATCH Variant Frequency (match_variant_frequency.py)
----------------------------------------------------

Input a list of genes by variant type and get back a table of NCI-MATCH hits
that can be further analyzed in Excel. Can either input a patient (or comma
separated list of patients) to query, or query the entire dataset. Will limit
the patient set to the non-outside assay results only.

MATCH Variant Frequency Help Docs
*********************************

.. code-block:: python

    usage: match_variant_frequency.py [-h] [-l] [-p <PSN>] [-s <gene_list>]
                                      [-c <gene_list>] [-f <gene_list>]
                                      [-i <gene_list>] [-a <all_types>]
                                      [--style <pp,csv,tsv>] [-o <output_file>]
                                      [-v]
                                      <matchbox>
    positional arguments:
      <matchbox>            Name of MATCHBox system to which the connection should
                            be made. Valid names are "adult", "ped", "adult-uat".

    optional arguments:
      -h, --help            show this help message and exit
      -l, --live            Get a live MATCHBox query instead of loading a local
                            JSON filederived from "matchbox_json_dump.py"
      -p <PSN>, --psn <PSN>
                            Only output data for a specific patient or comma
                            separated list of patients
      -s <gene_list>, --snv <gene_list>
                            Comma separated list of SNVs to look up in MATCHBox
                            data.
      -c <gene_list>, --cnv <gene_list>
                            Comma separated list of CNVs to look up in MATCHBox
                            data.
      -f <gene_list>, --fusion <gene_list>
                            Comma separated list of Fusions to look up in MATCHBox
                            data.
      -i <gene_list>, --indel <gene_list>
                            Comma separated list of Fusions to look up in MATCHBox
                            data.
      -a <all_types>, --all <all_types>
                            Query variants across all variant types for a set of
                            genes, rather than one by one. Helpful if one wants to
                            find any BRAF MOIs, no matter what type, for example.
      --style <pp,csv,tsv>  Format for output. Can choose pretty print (pp), CSV,
                            or TSV
      -o <output_file>, --output <output_file>
                            Output file to which to write data Default is stdout
      -v, --version         show program\'s version number and exit


MATCHBox Patient Summary (matchbox_patient_summary.py)
------------------------------------------------------

Get patient or disease summary statistics and data from the MATCH dataset.
Choosing the ``patient`` option will allow one to get a listing of patients in
the study and their respective disease. One can also filter that list down by
specifying a PSN (or comma separated list of PSNs) of interest Choosing the
``disease`` option will give a summary of the types and counts of each disease
in the study. Similar to the patients query, one can filter the list down by
inputting MEDDRA codes or tumor hisologies. 

.. note:: 
    Note that you must quote tumor names with spaces in them, and they must 
    exactly match the string indicated in MATCHBox. The use of MEDDRA codes 
    is recommended and preferred.

MATCHBox Patient Summary Help Docs
**********************************

.. code-block:: python

    usage: matchbox_patient_summary.py [-h] [-l] [-p PSN] [-t <tumor_type>]
                                       [-m <meddra_code>] [-O] [-o <output csv>]
                                       [-v]
                                       <matchbox> {patient,disease}
    positional arguments:
      <matchbox>            Name of MATCHBox system to which the connection will
                            be made. Valid systems are "adult", "ped", "adult-
                            uat".
      {patient,disease}     Category of data to output. Can either be patient or
                            disease level.

    optional arguments:
      -h, --help            show this help message and exit
      -l, --live            Make a live call to MATCHBox rather than loading a
                            local JSON containing patient data, usually from
                            matchbox_json_dump.py
      -p PSN, --psn PSN     Filter patient summary to only these patients. Can be
                            a comma separated list
      -t <tumor_type>, --tumor <tumor_type>
                            Retrieve data for only this tumor type or comma
                            separate list of tumors. Note that you must quote
                            tumors with names containing spaces.
      -m <meddra_code>, --meddra <meddra_code>
                            MEDDRA Code or comma separated list of codes to
                            search.
      -O, --Outside         Include Outside Assay study data (DEFAULT: False).
      -o <output csv>, --outfile <output csv>
                            Name of output file. Output will be in CSV format.
                            DEFAULT: STDOUT.
      -v, --version         show program\'s version number and exit
