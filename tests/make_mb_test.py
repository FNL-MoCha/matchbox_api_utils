#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import os
import json
import unittest

from matchbox_api_utils import MatchData
from matchbox_api_utils import TreatmentArms
from matchbox_api_utils import utils

class TestImport(unittest.TestCase):
    # These are root record keys each record has to have.
    default_keys = ['all_biopsies', 'all_msns', 'biopsies', 'concordance',
        'ctep_term', 'current_trial_status', 'ethnicity', 'gender', 'last_msg',
        'medra_code', 'progressed', 'psn', 'race', 'source', 'ta_arms']
    today_long = utils.get_today('long')
    today_short = utils.get_today('short')

    raw_mb_file = 'raw_mb_dump_' + today_short + '.json'
    proc_mb_file = 'mb_obj_' + today_short + '.json'
    raw_ta_file = 'raw_ta_dump_' + today_short + '.json'
    proc_ta_file = 'ta_obj_' + today_short + '.json'
    amoi_lookup = 'amoi_lookup_' + today_short + '.json'

    # @unittest.skip('Skip create live connection test.')
    def test_can_create_live_connection(self):
        data = MatchData(matchbox='adult', json_db=None, make_raw=True,
            quiet=False)

        # DB Date should be same as today if we did a live query.
        self.assertEqual(self.today_long, data.db_date)

        # Test that we made a raw DB file.
        self.assertTrue(os.path.isfile(self.raw_mb_file))

        # Test that there are no patient records missing, assuming the first
        # record is 10001 and we will look for gaps in the set until the last 
        # record. Work with dumped JSON since it's a little easier and we need
        # it later anyway.
        with open(self.raw_mb_file) as fh:
            jdata = json.load(fh)

        psns = list(map(int, [rec['patientSequenceNumber'] for rec in jdata]))
        start = 10001
        end = sorted(psns)[-1]
        missing = sorted(set(range(start, end, 1)).difference(psns))

        print("Total Records: {}; Total Unique: {}; Last Record: {}; Total "
            "Missing: {}".format(len(psns), len(set(psns)), end, len(missing)))

        self.assertTrue(len(missing) < 1, print('Missing: {}'.format(missing)))

        # Check early patient in DB has proper keys for this vesion
        self.assertListEqual(sorted(self.default_keys), 
            sorted(data.data['10001'].keys()))

        # Load up one discrete patient and check keys.
        patient_data = MatchData(matchbox='adult', json_db=None, 
                patient=11583)
        self.assertListEqual(sorted(self.default_keys), 
            sorted(patient_data.data['11583'].keys()))

        # Test that we can make a proc MB obj.
        data.matchbox_dump()
        self.assertTrue(os.path.isfile(self.proc_mb_file))

    # @unittest.skip('Skip create TreatmentArms DB.')
    def test_can_create_treatment_arms_db(self):
        ta_data = TreatmentArms(matchbox='adult', json_db=None,
            make_raw=True, quiet=False)
        self.assertTrue(os.path.isfile(self.raw_ta_file))

        ta_data.ta_json_dump()
        self.assertTrue(os.path.isfile(self.proc_ta_file))
        
    def tearDown(self):
        sys.stderr.write('Cleaning up extra test files.\n')
        for f in (self.raw_ta_file, self.raw_mb_file, self.proc_mb_file, 
            self.proc_ta_file, self.amoi_lookup):
            if os.path.exists(f):
                os.remove(f)
