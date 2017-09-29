#!/usr/bin/env python
import sys,os
import unittest
from matchbox_api_utils import MatchData

class FunctionTests(unittest.TestCase):
    data = MatchData(json_db= os.path.join(os.path.dirname(__file__),'mb_obj.json'))

    def test_get_biopsy_summary(self):
        """
        Test get_biopsy_summary()

        """
        self.assertNotEqual(self.data.get_biopsy_summary(category='failed'),0)

        # Total num PSNs must equal to sum(passed_biopsy,failed_biopsy,no_biopsy,outside)
        biopsy_data = self.data.get_biopsy_summary()
        self.assertEqual(
            sum([biopsy_data['initial'],biopsy_data['outside'],biopsy_data['outside_confirmation'],
                biopsy_data['progression']]
            ),
            biopsy_data['pass']
        )

    def test_get_disease_summary(self):
        """
        Test get_disease_summary()

        """
        self.assertIsNone(self.data.get_disease_summary(disease='Not a real disease'))
        # Difficult to get a real count, so just try to get greater than 0
        self.assertGreater(self.data.get_disease_summary(disease='Liposarcoma')['Liposarcoma'],0)

    def test_get_psn_from_msn(self):
        """
        Test get_psn() wiht MSN or BSN input.

        """
        self.assertEqual(self.data.get_psn(msn='MSN44180'),'PSN14420')
        self.assertEqual(self.data.get_psn(msn=19349),'PSN11352')
        self.assertIsNone(self.data.get_psn(msn='6'),None)
        self.assertEqual(self.data.get_psn(bsn='T-17-000550'),'PSN14420')
        self.assertIsNone(self.data.get_psn(bsn='no_biopsy'),None)

    def test_get_msn(self):
        """
        Test get_msn() with PSN or BSN input. Also look for multiple MSN output.

        """
        self.assertTrue('MSN44180' in self.data.get_msn(psn='14420'))
        self.assertTrue('MSN19349' in self.data.get_msn(psn=11352))
        self.assertTrue('MSN44180' in self.data.get_msn(bsn='T-17-000550'))
        self.assertEqual(self.data.get_msn(psn='11583'),['MSN18184','MSN41897'])

    def test_get_bsn(self):
        """
        Test get_bsn() with PSN or MSN input.

        """
        self.assertTrue('T-17-000550' in self.data.get_bsn(psn='14420'))
        self.assertTrue('T-17-000550' in self.data.get_bsn(msn='44180'))
        self.assertTrue('T-17-000550' in self.data.get_bsn(msn='MSN44180'))

    def test_get_histology(self):
        """
        Test get_patients_and_disease() with various inputs.

        """
        self.assertEqual(self.data.get_histology(psn='11352'),
            {'PSN11352': u'Serous endometrial adenocarcinoma'})
        self.assertEqual(self.data.get_histology(psn='11352,PSN10955,11222,PSN11070'),
            {
                'PSN11352': u'Serous endometrial adenocarcinoma', 
                'PSN11070': u'Salivary gland cancer', 
                'PSN11222': u'Ovarian epithelial cancer', 
                'PSN10955': u'Squamous cell carcinoma of the anus'
            }
        )
        self.assertEqual(self.data.get_histology(psn='PSN11352'),
            {'PSN11352': u'Serous endometrial adenocarcinoma'}
        )
        self.assertEqual(self.data.get_histology(psn=11352),
            {'PSN11352': u'Serous endometrial adenocarcinoma'}
        )

        self.assertEqual(self.data.get_histology(msn=3060),{'MSN3060' : None})

        self.assertEqual(self.data.get_histology(msn=3160),
            {'MSN3160': u'Ovarian epithelial cancer'}
        )
        self.assertEqual(self.data.get_histology(bsn='T-17-000550'),
            {'T-17-000550': u'Carcinosarcoma of the uterus'}
        )

        self.assertEqual(self.data.get_histology(bsn='T-16-987,T-15-1,T-16-000811'),
            {'T-15-1': None, 'T-16-000811': u'Salivary gland cancer', 'T-16-987': None}
        )

        self.assertRaises(SystemExit,self.data.get_histology,psn='11352',msn=3060)

