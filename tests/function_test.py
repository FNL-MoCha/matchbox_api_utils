import sys,os
from unittest import TestCase
from matchbox_api_utils import MatchboxData

class FunctionTests(TestCase):
    data = MatchboxData(dumped_data = os.path.join(os.path.dirname(__file__),'mb_obj.json'))

    def test_get_biopsy_summary(self):
        self.assertNotEqual(self.data.get_biopsy_summary(category='failed'),0)

        # Total num PSNs must equal to sum(passed_biopsy,failed_biopsy,no_biopsy,outside)
        biopsy_data = self.data.get_biopsy_summary()
        print(biopsy_data)
        self.assertEqual(
            sum([biopsy_data['passed_biopsy'],biopsy_data['failed_biopsy'],biopsy_data['no_biopsy'],
                biopsy_data['outside']]
            ),
            biopsy_data['psn']
        )

    def test_get_disease_summary(self):
        self.assertIsNone(self.data.get_disease_summary(disease='Not a real disease'))
        # Difficult to get a real count, so just try to get greater than 0
        self.assertGreater(self.data.get_disease_summary(disease='Liposarcoma')['Liposarcoma'],0)

    def test_get_psn_from_msn(self):
        self.assertEqual(self.data.get_psn(msn='MSN44180'),'PSN14420')
        self.assertEqual(self.data.get_psn(msn=19349),'PSN11352')
        self.assertIsNone(self.data.get_psn(msn='6'),None)

    def test_get_psn_from_bsn(self):
        self.assertEqual(self.data.get_psn(bsn='T-17-000550'),'PSN14420')
        self.assertIsNone(self.data.get_psn(bsn='no_biopsy'),None)

    def test_get_msn_from_psn(self):
        self.assertEqual(self.data.get_msn(psn='14420'),'MSN44180')
        self.assertEqual(self.data.get_msn(psn=11352),'MSN19349')

    def test_get_msn_from_bsn(self):
        self.assertEqual(self.data.get_msn(bsn='T-17-000550'),'MSN44180')

    def test_get_msn_from_psn_multiple(self):
        self.assertEqual(self.data.get_msn(psn='11926'),'MSN19992,MSN21717')

    def test_get_bsn_from_psn(self):
        self.assertEqual(self.data.get_bsn(psn='14420'),'T-17-000550')

    def test_get_bsn_from_msn(self):
        self.assertEqual(self.data.get_bsn(msn='44180'),'T-17-000550')
        self.assertEqual(self.data.get_bsn(msn='MSN44180'),'T-17-000550')

    def test_get_patients_and_disease(self):
        self.assertEqual(self.data.get_patients_and_disease(psn='11352'),
            {'11352': u'Serous endometrial adenocarcinoma'})
        self.assertEqual(self.data.get_patients_and_disease(psn='11352,PSN10955,11222,PSN11070'),
            {
                '11352': u'Serous endometrial adenocarcinoma', 
                '11070': u'Salivary gland cancer', 
                '11222': u'Ovarian epithelial cancer', 
                '10955': u'Squamous cell carcinoma of the anus'
            }
        )
        self.assertEqual(self.data.get_patients_and_disease(psn='PSN11352'),
            {'11352': u'Serous endometrial adenocarcinoma'}
        )
        self.assertEqual(self.data.get_patients_and_disease(psn=11352),
            {'11352': u'Serous endometrial adenocarcinoma'}
        )
        self.assertEqual(self.data.get_patients_and_disease(msn=3060),{'MSN3060' : None})
        self.assertEqual(self.data.get_patients_and_disease(msn=3160),
            {'MSN3160': u'Ovarian epithelial cancer'}
        )
        self.assertEqual(self.data.get_patients_and_disease(bsn='T-17-000550'),
            {'T-17-000550': u'Carcinosarcoma of the uterus'}
        )
        self.assertRaises(SystemExit,self.data.get_patients_and_disease,psn='11352',msn=3060)

