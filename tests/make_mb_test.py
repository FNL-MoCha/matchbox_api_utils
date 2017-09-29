#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys,os
import unittest

from datetime import datetime
from matchbox_api_utils import MatchData

class TestImport(unittest.TestCase):
    default_keys = ['concordance', 'psn', 'ta_arms', 'last_msg', 'current_trial_status', 'gender', 'progressed', 
        'all_biopsies', 'source', 'race', 'medra_code', 'ctep_term', 'all_msns', 'biopsies', 'ethnicity']

    @unittest.skip('Skip create live connection test.')
    def test_can_create_live_connection(self):
        """
        Test that we can make a connection to the live MATCHBox instance and get the API data.

        """
        data = MatchData(json_db=None)
        today = datetime.today().date()
        mb_born_on = datetime.strptime(data.db_date, '%m/%d/%Y').date()

        # DB Date should be same as today if we did a live query.
        self.assertEqual(today,mb_born_on)

        # Check early patient in DB has proper keys for this vesion
        self.assertListEqual(sorted(self.default_keys), sorted(data.data['10002'].keys()))

        # Load up one discrete patient and check keys.
        patient_data = MatchData(json_db=None, patient=11583)
        self.assertListEqual(sorted(self.default_keys), sorted(patient_data.data['11583'].keys()))

    # @unittest.skip('Skip load raw obj test')
    def test_can_load_raw_db(self):
        """
        Test that we can load the raw API dataset rather than making a live MB call and proc that.

        """
        raw_api_data = os.path.join(os.path.dirname(__file__),'../raw_mb_dump_092517.json')
        data = MatchData(load_raw=raw_api_data)
        self.assertListEqual(sorted(self.default_keys),sorted(data.data['14652'].keys()))
        
    # @unittest.skip('Skip load system proc obj test')
    def test_can_load_sys_json(self):
        """
        Test that we can load the system default dataset. In other words, run as the default condition would require.

        """
        data = MatchData()
        self.assertListEqual(sorted(self.default_keys),sorted(data.data['12376'].keys()))
