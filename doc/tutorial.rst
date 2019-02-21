***************************
MATCHBox API Utils Tutorial
***************************

Working with MATCHBox API Utils is very easy.  It is simply a matter of loading one
(or all) of the available modules:

    #. ``Matchbox()``
    #. ``MatchData()``
    #. ``TreatmentArms()``

Most often one will be using the ``MatchData()`` module, as that deals directly 
with the majority of the MATCH data that needs to be dealt with.  It directly 
pulls data from ``Matchbox`` and ``TreatmentArms`` where need be, and it allows
for the most flexible parsing and reporting of data.  That's not to say that
the other modules are not useful.  Far from it!  As we'll see a little later 
down, there are a number of useful things that one can do with those as well.

By default modules will load the most recent dataset available in
``$HOME/.mb_utils`` (see API documentation for specifics), and be ready for 
use. 

However, if one wanted to get a live dataset, or one wanted to get data from an 
older snapshot of the database, that is all possible too.  

.. note:: 
    Live queries to MATCHBox can take a long time to perform due to network 
    traffic, and the very large size of the database, and is not the preferred
    way to work with the data. Especially since most of the data is in a final,
    locked state, it's recommended to use a JSON snapshot of data when possible.

.. attention::
    Now that we have multiple MATCHBoxes in production for different studies,
    one will always need to specify which MATCHBox they are intending to 
    connect to when initializing any of these classes.  By default, the Adult
    MATCHBox is loaded since this is the most frequently used.  But, that is 
    likely to change without warning, and you are advised to explicityly 
    specify which system you are interested in calling.

Module: Matchbox
================

The ``Matchbox`` module is a basic data connector to the live instance of the
MATCHBox system.  Apart from a URL to query and credentials, there are not a 
whole lot of options.  

In general this module is called by ``MatchData`` and ``TreatmentArms`` to make
the connection to the live system and pull data.  I've included some documentation 
of this module, though, in the event that one needs to call on it at some point.  

For example, on occassion one might want to get a complete raw MATCHBox dataset,
which has not been parse and filtered, and can be accepted into the other 
modules as if they were making a live call.  In this case, one could run: ::

    >>> from matchbox_api_utils import Matchbox
    >>> Matchbox(matchbox='adult', method='mongo', mongo_collection='patient',
    ...     make_raw='mb')

This will create a complete raw JSON dump of MATCHBox.

.. warn:
    A raw MATCHBox data dump like this might be very large!

Without dumping that data to a JSON file, one could assign a variable to the 
Matchbox obj, and then pass it around.  However, as one can see with regard to
how many required arguments there are to configure the API call, most of which 
are set up in the configuration file generated upon installation, ``class 
MatchData()`` is a much better entry point, and only requires one argument to
generate the same file, as shown below.


Module: MatchData
=================

This is by far the workhorse module of the package.  In its most basic form, 
one needs only load the object into a variable, and then run the host of 
methods available: ::

    >>> from matchbox_api_utils import MatchData
    >>> data = MatchData(matchbox='adult')
    >>> data.get_biopsy_summary(category='progression', ret_type='counts')
    {'progression': 19}

.. note::
    The resultant data above may be different than your result depending on 
    when the dataset was generated!

This simply works by loading a processed version of MATCHBox, which has been 
optimized to be smaller and more efficient than the raw MATCHBox dataset, and 
then having a set of methods to extract portions of the data for cohort type 
analysis. 

As mentioned above, one can either choose to use the ``sys_default`` JSON option
for ``MatchData``, in which case the latest version of the MATCHBox JSON dump 
will be loaded, or one can load their own custom file (e.g. if one wanted to 
load an old version of the data to see how things changed).  Alternatively 
(and with the same warning as above), one can make a live query at the cost of 
a long load time. 

There is also the possibility of loading just one or more patient IDs into the
API and limiting data to that cohort. In this case passing a PSN to the 
``patient`` argument will allow one to filter data to only that patient when 
reading the ``sys_default`` JSON file, or, and arguably better, getting live
and up to date data for only that patient from MATCHBox.

Toy Example #1
--------------
You would like to know the disease state of the progression biopsies indicated 
above.  You don't have any identifiers or other information to go on.

Here's a way one might work through it: ::

    .. note::
        I am listing all of the options to call these methods, even when some 
        of them are default, just to give a sense of what is possible.  See the 
        detailed docs for a list of default args.

    >>> from matchbox_api_utils import MatchData
    >>> from pprint import pprint as pp
    >>> data = MatchData(matchbox='adult', method='mongo', json_db=None, 
    ...    quiet=False)
    >>> results = {}  # Let's create a dict to put the results in.
    >>> biopsies = data.get_biopsy_summary(category='progression', ret_type='ids')
    >>> pp(biopsies)
    {'progression': [u'T-17-002064',
                     u'T-17-002755',
                     u'T-18-000071',
                     u'T-17-002680',
                     u'T-17-000787',
                     u'T-17-002621',
                     u'T-17-002657',
                     u'T-17-001275',
                     u'T-17-001175',
                     u'T-17-002564',
                     u'T-17-002556',
                     u'T-17-002730',
                     u'T-17-002600',
                     u'T-18-000005',
                     u'T-17-000333',
                     u'T-18-000031']}

Notice that we changed the return type of the ``get_biopsy_summary()`` call to
`ids`, which allows us to get ids rather than counts.  Now that we have those 
biopsy IDs, we can get some PSNs , which will be helpful in getting the disease
data ultimately: ::

    >>> for bsn in biopsies['progression']:
    ...     psn = data.get_psn(bsn=bsn)
    ...     msn = data.get_msn(bsn=bsn)
    ...     print('%s: %s' % (psn, msn))
    PSN13070: [u'MSN59774']
    PSN13670: [u'MSN62646']
    PSN15436: None
    PSN15362: [u'MSN62489']
    PSN10955: [u'MSN46367']
    PSN13948: [u'MSN62208']
    PSN11347: [u'MSN62398']
    PSN10818: [u'MSN51268']
    PSN11083: [u'MSN50799']
    PSN11707: [u'MSN62042']
    PSN11769: [u'MSN62018']
    PSN11127: [u'MSN62547']
    PSN12471: [u'MSN62109']
    PSN14705: [u'MSN62687']
    PSN11583: [u'MSN41897']
    PSN15971: None

Looks like there are a couple issues here.  

    #. First, results from the ``get_msn()`` method are always lists.  We can 
       have multiple MSNs per BSN unfortunately, and so we need to output more 
       than one on occassion.  In this case, for what we want to do, we can 
       just output them all as a comma separated list.  

    #. Second some results to not have a MSN returned!  This can happen.  In 
       this case, there was a progression biopsy collected, but no valid MSN 
       was yet generated for the case.  Since we would prefer to only work with
       complete data for now, we'll skip those cases.

So, now that we know which are progression cases from the whole dataset, and 
know their PSN, BSN, and MSN identifiers, let's get the disease for each, and 
store it in our ``results`` dict above.  We'll rewrite a little bit of the code
above to help with some of the processing: ::

    >>> for bsn in biopsies['progression']:
    ...     psn = data.get_psn(bsn=bsn)
    ...     msn = data.get_msn(bsn=bsn)
    ...     if msn is not None:
    ...         results[psn] = [bsn, ','.join(msn)]
    ...
    >>> pp(results)
    {'PSN10818': [u'T-17-001275', u'MSN51268'],
     'PSN10955': [u'T-17-000787', u'MSN46367'],
     'PSN11083': [u'T-17-001175', u'MSN50799'],
     'PSN11127': [u'T-17-002730', u'MSN62547'],
     'PSN11347': [u'T-17-002657', u'MSN62398'],
     'PSN11583': [u'T-17-000333', u'MSN41897'],
     'PSN11707': [u'T-17-002564', u'MSN62042'],
     'PSN11769': [u'T-17-002556', u'MSN62018'],
     'PSN12471': [u'T-17-002600', u'MSN62109'],
     'PSN13070': [u'T-17-002064', u'MSN59774'],
     'PSN13670': [u'T-17-002755', u'MSN62646'],
     'PSN13948': [u'T-17-002621', u'MSN62208'],
     'PSN14705': [u'T-18-000005', u'MSN62687'],
     'PSN15362': [u'T-17-002680', u'MSN62489']}

Much better!  Now, let's leverage another method ``get_hisology()`` to get the 
patient's disease and add it to the data: ::

    >>> for p in results:
    ...     print(data.get_histology(psn=p))
    {'PSN15362': u'Salivary gland cancer'}
    {'PSN11583': u'Salivary gland cancer'}
    {'PSN13070': u'Cholangiocarcinoma, intrahepatic and extrahepatic bile ducts (adenocarcinoma)'}
    {'PSN10955': u'Squamous cell carcinoma of the anus'}
    {'PSN12471': u'Carcinosarcoma of the uterus'}
    {'PSN10818': u'Colorectal cancer, NOS'}
    {'PSN11769': u'Renal cell carcinoma, clear cell adenocarcinoma'}
    {'PSN11347': u'Salivary gland cancer'}
    {'PSN13948': u'Adenocarcinoma of the rectum'}
    {'PSN13670': u'Ovarian epithelial cancer'}
    {'PSN11707': u'Cholangiocarcinoma, intrahepatic and extrahepatic bile ducts (adenocarcinoma)'}
    {'PSN11083': u'Adenocarcinoma of the colon'}
    {'PSN14705': u'Laryngeal squamous cell carcinoma'}
    {'PSN11127': u'Invasive breast carcinoma'}

As we can see the results for this method call are all dicts of `PSN : Disease`
mappings.  So, we can use the PSN to pull the disease and add it to the 
results: ::

    >>> for p in results:
    ...     results[p].append(data.get_histology(psn=p)[p])
    >>> pp(results)
    {'PSN10818': [u'T-17-001275', u'MSN51268', u'Colorectal cancer, NOS'],
     'PSN10955': [u'T-17-000787', 
                  u'MSN46367',
                  u'Squamous cell carcinoma of the anus'],
    'PSN11083': [u'T-17-001175', u'MSN50799', u'Adenocarcinoma of the colon'],
    'PSN11127': [u'T-17-002730', u'MSN62547', u'Invasive breast carcinoma'],
    'PSN11347': [u'T-17-002657', u'MSN62398', u'Salivary gland cancer'],
    'PSN11583': [u'T-17-000333', u'MSN41897', u'Salivary gland cancer'],
    'PSN11707': [u'T-17-002564',
                 u'MSN62042',
                 u'Cholangiocarcinoma, intrahepatic and extrahepatic bile ducts (adenocarcinoma)'],
    'PSN11769': [u'T-17-002556',
                 u'MSN62018',
                 u'Renal cell carcinoma, clear cell adenocarcinoma'],
    'PSN12471': [u'T-17-002600', u'MSN62109', u'Carcinosarcoma of the uterus'],
    'PSN13070': [u'T-17-002064',
                 u'MSN59774',
                 u'Cholangiocarcinoma, intrahepatic and extrahepatic bile ducts (adenocarcinoma)'],
    'PSN13670': [u'T-17-002755', u'MSN62646', u'Ovarian epithelial cancer'],
    'PSN13948': [u'T-17-002621', u'MSN62208', u'Adenocarcinoma of the rectum'],
    'PSN14705': [u'T-18-000005',
                 u'MSN62687',
                 u'Laryngeal squamous cell carcinoma'],
    'PSN15362': [u'T-17-002680', u'MSN62489', u'Salivary gland cancer']}

And finally we have a nice list of collected data for each progression case, 
which is ready to print out for downstream use: ::

    >>> for patient in results:
    ...     print('\t'.join([patient] + results[patient]))
    PSN15362    T-17-002680    MSN62489    Salivary gland cancer
    PSN11583    T-17-000333    MSN41897    Salivary gland cancer
    PSN13070    T-17-002064    MSN59774    Cholangiocarcinoma, intrahepatic and extrahepatic bile ducts (adenocarcinoma)
    PSN10955    T-17-000787    MSN46367    Squamous cell carcinoma of the anus
    PSN12471    T-17-002600    MSN62109    Carcinosarcoma of the uterus
    PSN10818    T-17-001275    MSN51268    Colorectal cancer, NOS
    PSN11769    T-17-002556    MSN62018    Renal cell carcinoma, clear cell adenocarcinoma
    PSN11347    T-17-002657    MSN62398    Salivary gland cancer
    PSN13948    T-17-002621    MSN62208    Adenocarcinoma of the rectum
    PSN13670    T-17-002755    MSN62646    Ovarian epithelial cancer
    PSN11707    T-17-002564    MSN62042    Cholangiocarcinoma, intrahepatic and extrahepatic bile ducts (adenocarcinoma)
    PSN11083    T-17-001175    MSN50799    Adenocarcinoma of the colon
    PSN14705    T-18-000005    MSN62687    Laryngeal squamous cell carcinoma
    PSN11127    T-17-002730    MSN62547    Invasive breast carcinoma

.. note:
    It is recommended that you use the 
    `CSV <https://docs.python.org/2/library/csv.html>`_ module for printing 
    data, since it is much better equipped to handle commas and spaces in 
    names, and makes the data much more portable into things like Excel or R

So, there you have it.  Very simple toy case, but hopefully one that highlights
some of the features of the MatchData module.  See the API documentation 
section for more information about the included modules and their usage.


Module: TreatmentArms
=====================

The ``TreatmentArms`` module will handle all NCI-MATCH treatment arm related 
data, including the handling of a "rules engine" to categorize mutations of 
interest (MOIs) as being actionable (aMOIs) or not.  This class has a set of 
useful functions to generate arm related data, including mapping patients to
arms and variants to arms.

As with the other modules, one can either make a live query to MATCHBox to 
generate a dataset: ::

    >>> from matchbox_api_utils import TreatmentArms
    >>> ta_data = TreatmentArms(matchbox='adult', method='mongo', json_db=None,
    ...    quiet=False)
    
Or, as with ``MatchData``, not specifying a JSON database will result in
loading the ``sys_default`` database which is built at the same time as the 
``MatchData`` JSON database.  You'll see this file in 
``$HOME/.mb_utils/ta_obj_<date>.json``.  

Once you have object loaded, then you can run one of the public methods 
available, including ``map_amoi()``, ``map_drug_arm()``, or 
``get_exclusion_disease()``.

Toy Example #2
--------------

Let's say you have a *`BRAF p.V600E`* mutation that you discovered in a patient 
diagnosed with *`Melanoma`* , but you are not sure whether or not any arms 
cover the patient, and if there is a qualifying arm, whether or not the patient
has an exclusionary disease (i.e. a histological subtype that is excluded from
arm eligibility).  

The first step is to try to map that aMOI to the study arms.  You need to have 
some NCI-MATCH level variant data (typically from Ion Reporter / OVAT) since 
there are some extra rules to map.  We always need to know the following 
(dict_key: accepted_values):

    ====================   ====================================================
    Variant Key            Acceptable Values
    ====================   ====================================================
    type                   | { snvs_indels, cnvs, fusions }
    oncomineVariantClass   | { Hotspot, Deleterious }
    gene                   | Any acceptable HUGO gene name (e.g. BRAF)
    identifier             | Any variant identifier, usually from COSMIC 
                           | (e.g. COSM476)
    exon                   | The numeric value for the exon in which the 
                           | variant is found. For example, if the variant is
                           | in Exon 15, you would indicate 15 in this field. 
                           | you would indicate 15 in this field.
    function               | {'missense', 'nonsense', 'frameshiftInsertion', 
                           | 'frameshiftDeletion', 'nonframeshiftDeletion', 
                           | 'nonframeshiftInsertion', 
                           | 'frameshiftBlockSubstitution'}
    ====================   ====================================================

In the case of a typical BRAF p.V600E variant, we would set up our environment 
as follows: ::

    >>> from matchbox_api_utils import TreatmentArms
    >>> from pprint import pprint as pp
    >>> ta_data = TreatmentArms(matchbox='adult', method='mongo', json_db=None, 
    ...   quiet=False)
    >>> variant = {
    ...    'type' : 'snvs_indels',
    ...    'gene' : 'BRAF',
    ...    'identifier' : 'COSM476',
    ...    'exon' : '15',
    ...    'function' : 'missense',
    ...    'oncominevariantclass' : 'Hotspot' }

Now to find out if our variant would qualify for any arms, we'll run 
``map_amoi()`` to check: ::

    >>> v600e_arms = ta_data.map_amoi(variant)
    >>> pp(v600e_arms)
    ['EAY131-Y(e)', 'EAY131-P(e)', 'EAY131-N(e)', 'EAY131-H(i)']

So we see that there are 4 arms that have identified this variant as being an 
aMOI. But, based on the notation in parenthesis (e.g. `'(e)'`), we can see that
Arms Y, P, and N consider this aMOI to be exclusionary, while arm H consider 
this aMOI to be inclusionary.  So, it looks like so far the patient is a 
potential match for Arm H only.  Now, let's see if their disease would qualify 
them for this arm: ::

    >>> pp(ta_data.get_exclusion_disease('EAY131-H'))
    ['Papillary thyroid carcinoma',
     'Melanoma',
     'Malignant Melanoma of sites other than skin or eye',
     'Acral Lentiginous Melanoma',
     'Adenocarcinoma of the colon',
     'Adenocarcinoma of the rectum',
     'Colorectal cancer, NOS',
     'Bronchioloalveolar carcinoma',
     'Lung adenocarcinoma',
     'Lung adenocarcinoma with bronchioloalveolar features',
     'Non-small cell lung cancer, NOS',
     'Squamous cell lung carcinoma']

Well, that's bad news!  Based on the fact that the patient has `Melanoma` and 
it is an exclusionary disease for Arm H, the patient would not currently 
qualify for any NCI-MATCH Arm.  

.. note::
    This mapping functionality is very simple and only relies on the reported
    histology and the input biomarker.  There are many other NCI-MATCH trial 
    factors that determine eligibility, which are way outside the scope of this 
    utility.  In essence, this is not meant to be a treatment assignment 
    utility and is only meant to help classify variants.  

For more detailed descriptions of the methods in the module and their use, see 
the TreatmentArms API documention section.
