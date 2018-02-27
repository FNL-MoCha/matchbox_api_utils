MATCHBox API Utils Helper Scripts
=================================

MATCHBox JSON Dump (matchbox_json_dump.py)
------------------------------------------
Get parsed dataset from MATCHBox and dump as a JSON object that we can use
later on to speed up development and periodic searching for data.

This is the script that is run during the post installer, and something that 
should be run on a periodic basis to take advantage of new MATCHBox data entered
into the system (at least until lockdown occurs).  This will put the resultant
JSON file into the current directory, where it should probably be migrated into 
``$HOME/.mb_utils/`` to be picked up by the rest of the system.

MATCHBox JSON Dump Help Doc
***************************
.. code-block:: python

    Usage: 
        matchbox_json_dump.py [-h] [-d <raw_mb_datafile.json>] [-r] [-p <psn>]
        [-t <ta_obj.json>] [-a <amoi_obj.json>]
        [-m <mb_obj.json>] [-v]

    Optional Arguments:
        -r, --raw        Generate a raw dump of MATCHBox for debugging and dev 
                         purposes.
                         No filtering or condensing of data at all.
        -d, --data       Load a raw MATCHBox database file (usually after running
                         with the -r option.
        -p, --patient    Patient sequence number used to limit output for testing
                         and dev purposes
        -t, --ta_json    Treatment Arms obj JSON filename. DEFAULT: 
                         ta_obj_<datestring>.json
        -a, --amoi_json  aMOIs lookup filename. DEFAULT: 
                         "amois_lookup_<datestring>.json".
        -m, --mb_json    Name of Match Data obj JSON file. DEFAULT: 
                         "mb_obj_<datestring>.json".

    -h, --help           Show this help message and exit
    -v, --version        Show program's version number and exit

MAP MSN PSN (map_msn_psn.py)
----------------------------
Input a MSN, BSN, or PSN, and return the other identifiers. Useful when trying
to retrieve the correct dataset and you only know one piece of information.

.. note::
    We are only working with internal BSN, MSN, and PSN numbers for now and
    can not return Outside Assay identifiers at this time.

MAP MSN PSN Help Doc
********************

.. code-block:: python

    Usage: 
        map_msn_psn.py [-h] [-j <mb_json_file>] -t {psn,msn,bsn} [-f <input_file>] 
        [-o <outfile>] [-v] [<IDs>]

    Positional Arguments:
    IDs    MATCH IDs to query. Can be single or comma separated list. Must be used 
           with PSN or MSN option.

    Optional Arguments:
    -j, --json     Load a MATCHBox JSON file derived from "matchbox_json_dump.py" 
                   instead of a live query. By default will load the "sys_default" 
                   created during package installation. If you wish to do a live 
                   query (i.e. not load a previously downloaded JSON dump), set
                   -j to "None".
    -t, --type     Type of query string input. Can only be MSN, PSN, or BSN
    -f, --file     Load a batch file of all MSNs or PSNs to proc
    -o, --outfile  File to which output should be written. Default: STDOUT.
    -h, --help     Show this help message and exit
    -v, --version  Show program's version number and exit

MATCH Variant Frequency (match_variant_frequency.py)
----------------------------------------------------

Input a list of genes by variant type and get back a table of NCI-MATCH hits
that can be further analyzed in Excel or some other tool. Can either input a patient
(or comma separated list of patients) to query, or query the entire dataset. Will 
limit the patient set to the non-outside assay results only, as the Outside Assay
data is very unreliable.

MATCH Variant Frequency Help Docs
*********************************

.. code-block:: python

    Usage: 
    match_variant_frequency.py [-h] [-j <mb_json_file>] [-p <PSN>] [-s <gene_list>]
    [-c <gene_list>] [-f <gene_list>] [-i <gene_list>] [--style <pp,csv,tsv>] 
    [-o <output_file>] [-v]

    Optional Arguments:
    -j, --json     Load a MATCHBox JSON file derived from "matchbox_json_dump.py" 
                   instead of a live query
    -p, --psn      Only output data for a specific patient or comma separated list 
                   of patients
    -s, --snv      Comma separated list of SNVs to look up in MATCHBox data.
    -c, --cnv      Comma separated list of CNVs to look up in MATCHBox data.
    -f, --fusion   Comma separated list of Fusions to look up in MATCHBox data.
    -i, --indel    Comma separated list of Fusions to look up in MATCHBox data.

    --style        Format for output. Can choose pretty print (pp), CSV, or TSV
    -o, --output   Output file to which to write data. Default is stdout
    -h, --help     Show this help message and exit
    -v, --version  Show program's version number and exit


MATCHBox Patient Summary (matchbox_patient_summary.py)
------------------------------------------------------

Get patient or disease summary statistics and data from the MATCH dataset.

MATCHBox Patient Summary Help Docs
**********************************

.. code-block:: python

    Usage: 
    matchbox_patient_summary.py [-h] [-j <mb_json_file>] [-p PSN] [-t <tumor_type>]
    [-m <medra_code>] [-O] [-o <results.txt>] [-v] {patient,disease}

    Positional Arguments:
    patient, disease    Category of data to output. Can either be patient or disease
    level.

    Optional Arguments:
    -j, --json     MATCHBox JSON file containing patient data, usually from 
                   matchbox_json_dump.py
    -p, --psn      Filter patient summary to only these patients. Can be a comma 
                   separated list
    -t, --tumor    Retrieve data for only this tumor type or comma separate list of
                   tumors. Note that you must quote tumors with names containing 
                   spaces.
    -m, --medra    MEDRA Code or comma separated list of codes to search.
    -O, --Outside  Include Outside Assay study data (DEFAULT: False).
    -o, --outfile  Name of output file. DEFAULT: STDOUT.

    -h, --help     Show this help message and exit
    -v, --version  Show program's version number and exit


