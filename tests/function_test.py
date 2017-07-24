# TODO: Add some more fail tests.
import sys,os
from unittest import TestCase
from matchbox_api_utils import MatchboxData

class FunctionTests(TestCase):
    data = MatchboxData(dumped_data = os.path.join(os.path.dirname(__file__),'mb_obj.json'))

    def test_get_psn_from_msn(self):
        msn = 'MSN44180'
        self.assertEqual(self.data.get_psn(msn=msn),'PSN14420')
        self.assertFalse(self.data.get_psn(msn='6'),None)

    def test_get_psn_from_bsn(self):
        bsn = 'T-17-000550'
        self.assertEqual(self.data.get_psn(bsn=bsn),'PSN14420')
        self.assertFalse(self.data.get_psn(bsn='no_biopsy'),None)

    def test_get_msn_from_psn(self):
        psn = '14420'
        self.assertEqual(self.data.get_msn(psn=psn),'MSN44180')

    def test_get_msn_from_bsn(self):
        bsn = 'T-17-000550'
        self.assertEqual(self.data.get_msn(bsn=bsn),'MSN44180')

    def test_get_msn_from_psn_multiple(self):
        psn = '11926'
        self.assertEqual(self.data.get_msn(psn=psn),'MSN19992,MSN21717')

    def test_get_bsn_from_psn(self):
        psn = '14420'
        self.assertEqual(self.data.get_bsn(psn=psn),'T-17-000550')

    def test_get_bsn_from_msn(self):
        msn='44180'
        self.assertEqual(self.data.get_bsn(msn=msn),'T-17-000550')
