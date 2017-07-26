#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys,os
import unittest
from matchbox_api_utils import MatchData

class TestImport(unittest.TestCase):
    keys = ['sequenced', 'psn', 'msn', 'outside', 'no_biopsy', 'failed_biopsy', 'passed_biopsy']
    def get_keys(self,data):
        ret = data.get_biopsy_summary()
        print ret 
        return ret.keys()

    @unittest.skip('Skip create live conn test')
    def test_can_create_live_connection(self):
        """
        Test that we can make a connection to the live MATCHBox instance and get the API data.

        """
        data = MatchData(dumped_data = None)
        self.assertListEqual(self.keys,self.get_keys(data))

    # @unittest.skip('Skip load raw obj test')
    def test_can_load_raw_db(self):
        """
        Test that we can load the raw API dataset rather than making a live MB call and proc that.

        """
        raw_api_data = os.path.join(os.path.dirname(__file__),'../raw_mb_dump_071717.json')
        data = MatchData(load_raw=raw_api_data)
        self.assertListEqual(self.keys,self.get_keys(data))
        
    # @unittest.skip('Skip load proc obj test')
    def test_can_load_json_db(self):
        """
        Test that we can load a custom proc'd JSON dataset rather than a full API call and creation of JSON dataset.

        """
        proc_api_data = os.path.join(os.environ['HOME'], '.mb_utils/mb_obj.json')
        data = MatchData(dumped_data=proc_api_data)
        self.assertListEqual(self.keys,self.get_keys(data))

    # @unittest.skip('Skip load proc obj test')
    def test_can_load_sys_json(self):
        """
        Test that we can load the system default dataset. In other words, run as the default condition would require.
        This is the most important test, and the one that will likely remain in production.

        """
        data = MatchData()
        self.assertListEqual(self.keys,self.get_keys(data))
