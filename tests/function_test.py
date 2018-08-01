#!/usr/bin/env python
import sys,os
import unittest
from matchbox_api_utils import MatchData
from matchbox_api_utils import utils

class FunctionTests(unittest.TestCase):
    # proc_mb_file = 'mb_obj_' + utils.get_today('short') + '.json'
    sys_default_json = os.path.join(
        os.path.dirname(__file__),
        'mb_obj_042018.json'
    )
    # sys_default_json = os.path.join(os.path.dirname(__file__), proc_mb_file)
    data = MatchData(matchbox='adult', json_db=sys_default_json)

    def test_get_biopsy_summary(self):
        self.assertNotEqual(
            self.data.get_biopsy_summary(category='failed_biopsy'), 
            0
        )

        # As of this test, we had 19 progression cases, so the number can't be
        # less than that.
        progression_cases = self.data.get_biopsy_summary(category='progression')
        self.assertTrue(progression_cases['progression'] >= 19)

        some_progression_cases = ('T-17-000787', 'T-17-002680', 'T-18-000123')
        query = self.data.get_biopsy_summary(category='progression', 
            ret_type='ids')
        self.assertTrue(
            all(x in query['progression'] for x in some_progression_cases)
        )


        # Total num PSNs must equal to sum(passed_biopsy, failed_biopsy,
        # no_biopsy, outside)
        # TODO: Fix this once we can figure it out.
        # biopsy_data = self.data.get_biopsy_summary()
        # terms = ('initial', 'outside', 'outside_confirmation')
        # total = sum([biopsy_data[i] for i in terms])
        # self.assertEqual(total, biopsy_data['pass'])

    def test_get_psn(self):
        self.assertEqual(self.data.get_psn(msn='MSN44180'),'PSN14420')
        self.assertEqual(self.data.get_psn(msn=19349),'PSN11352')
        self.assertIsNone(self.data.get_psn(msn='6'),None)
        self.assertEqual(self.data.get_psn(bsn='T-17-000550'),'PSN14420')
        self.assertIsNone(self.data.get_psn(bsn='no_biopsy'),None)

    def test_get_msn(self):
        self.assertTrue('MSN44180' in self.data.get_msn(psn='14420'))
        self.assertTrue('MSN19349' in self.data.get_msn(psn=11352))
        self.assertTrue('MSN44180' in self.data.get_msn(bsn='T-17-000550'))
        self.assertEqual(self.data.get_msn(psn='11583'),['MSN18184','MSN41897'])

    def test_get_bsn(self):
        self.assertTrue('T-17-000550' in self.data.get_bsn(psn='14420'))
        self.assertTrue('T-17-000550' in self.data.get_bsn(msn='44180'))
        self.assertTrue('T-17-000550' in self.data.get_bsn(msn='MSN44180'))
        self.assertEqual(
            self.data.get_bsn(psn=11583), 
            ['T-16-000811', 'T-17-000333']
        )

    def test_get_disease_summary(self):
        self.assertIsNone(
            self.data.get_disease_summary(query_disease='Not a real disease')
        )

        # Difficult to get a real count, so just try to get greater than 0
        ret_data = self.data.get_disease_summary(query_disease=['Liposarcoma'])
        self.assertGreater(list(ret_data.values())[0][1], 0)

        dis_dict = {
            '10006190' : 'Invasive breast carcinoma',
            '10014735' : 'Endometrioid endometrial adenocarcinoma',
            '10024193' : 'Leiomyosarcoma (excluding uterine leiomyosarcoma)',
        }

        ret_data = self.data.get_disease_summary(query_medra=list(dis_dict))
        self.assertEqual(
            list(dis_dict.values()),
            [ret_data[x][0] for x in ret_data]
        )

    def test_get_histology(self):
        self.assertEqual(
            self.data.get_histology(psn='11352'),
            {'PSN11352': u'Serous endometrial adenocarcinoma'}
        )

        self.assertDictEqual(
            self.data.get_histology(psn='11352,PSN10955,11222,PSN11070'),
            {
                'PSN11352': u'Serous endometrial adenocarcinoma', 
                'PSN11070': u'Salivary gland cancer', 
                'PSN11222': u'Ovarian epithelial cancer', 
                'PSN10955': u'Squamous cell carcinoma of the anus'
            }
        )


        self.assertEqual(
            self.data.get_histology(psn='PSN11352'),
            {'PSN11352': u'Serous endometrial adenocarcinoma'}
        )

        self.assertEqual(
            self.data.get_histology(psn=11352),
            {'PSN11352': u'Serous endometrial adenocarcinoma'}
        )

        self.assertEqual(
            self.data.get_histology(msn=3060),
            {'MSN3060' : None}
        )

        self.assertEqual(
            self.data.get_histology(msn=3160),
            {'MSN3160': u'Ovarian epithelial cancer'}
        )

        self.assertEqual(
            self.data.get_histology(bsn='T-17-000550'),
            {'T-17-000550': u'Carcinosarcoma of the uterus'}
        )

        self.assertDictEqual(
            self.data.get_histology(bsn='T-16-987,T-15-1,T-16-000811'),
            {
                'T-15-1': None, 
                'T-16-000811': u'Salivary gland cancer', 
                'T-16-987': None
            }
        )

        self.assertEqual(
            self.data.get_histology(psn='11352',msn=3060),
            None
        )

    def test_find_variant_frequency(self):
        query = {'snvs' : ['EGFR'], 'indels' : ['EGFR']}
        
        wanted_result = {'15232': {'bsns': ['T-17-001423'],
           'disease': 'Lung adenocarcinoma',
           'mois': [{'alleleFrequency': 0.191596,
                     'alternative': 'T',
                     'amoi': ['EAY131-A(e)', 'EAY131-E(i)'],
                     'chromosome': 'chr7',
                     'confirmed': True,
                     'exon': '20',
                     'function': 'missense',
                     'gene': 'EGFR',
                     'hgvs': 'c.2369C>T',
                     'identifier': 'COSM6240',
                     'oncominevariantclass': 'Hotspot',
                     'position': '55249071',
                     'protein': 'p.Thr790Met',
                     'reference': 'C',
                     'transcript': 'NM_005228.3',
                     'type': 'snvs_indels'},
                    {'alleleFrequency': 0.748107,
                     'alternative': '-',
                     'amoi': ['EAY131-A(i)'],
                     'chromosome': 'chr7',
                     'confirmed': True,
                     'exon': '19',
                     'function': 'nonframeshiftDeletion',
                     'gene': 'EGFR',
                     'hgvs': 'c.2240_2257delTAAGAGAAGCAACATCTC',
                     'identifier': 'COSM12370',
                     'oncominevariantclass': 'Hotspot',
                     'position': '55242470',
                     'protein': 'p.Leu747_Pro753delinsSer',
                     'reference': 'TAAGAGAAGCAACATCTC',
                     'transcript': 'NM_005228.3',
                     'type': 'snvs_indels'}],
           'msns': ['MSN52258'],
           'psn': '15232'}}

        self.assertDictEqual(
            self.data.find_variant_frequency(query, [15232])[0],
            wanted_result
        )

    def test_get_variant_report(self):
        result1 = {'MSN3111': {'unifiedGeneFusions': [{'amoi': None,
                                 'annotation': 'COSF1232',
                                 'confirmed': True,
                                 'driverGene': 'RET',
                                 'driverReadCount': 7121,
                                 'gene': 'RET',
                                 'identifier': 'KIF5B-RET.K15R12.COSF1232',
                                 'partnerGene': 'KIF5B',
                                 'type': 'fusions'}]}}

        result2 = {
            'MSN35733': {
                'singleNucleotideVariants': [
                    {
                        'alleleFrequency': 0.570856,
                        'alternative': 'T',
                        'alternativeAlleleObservationCount': 3190,
                        'amoi': ['EAY131-Z1I(i)'],
                        'chromosome': 'chr13',
                        'confirmed': True,
                        'exon': '25',
                        'flowAlternativeAlleleObservationCount': '1140',
                        'flowReferenceAlleleObservations': '177',
                        'function': 'nonsense',
                        'gene': 'BRCA2',
                        'hgvs': 'c.9382C>T',
                        'identifier': '.',
                        'oncominevariantclass': 'Deleterious',
                        'position': '32968951',
                        'protein': 'p.Arg3128Ter',
                        'readDepth': 5551,
                        'reference': 'C',
                        'referenceAlleleObservations': 456,
                        'transcript': 'NM_000059.3',
                        'type': 'snvs_indels'
                    }
                ]
            }
        }

        self.assertEqual(
            self.data.get_variant_report(psn=10005),
            result1
        )

        self.assertEqual(
            self.data.get_variant_report(msn=35733),
            result2
        )


    def test_get_patient_ta_status(self):
        self.assertEqual(
            self.data.get_patient_ta_status(psn=10837),
            {'EAY131-Z1A' : 'FORMERLY_ON_ARM_OFF_TRIAL'},
        )

        self.assertEqual(
            self.data.get_patient_ta_status(psn=11889),
            {
                'EAY131-IX1' : 'FORMERLY_ON_ARM_OFF_TRIAL', 
                'EAY131-I' : 'COMPASSIONATE_CARE'
            }
        )

        self.assertEqual(self.data.get_patient_ta_status(psn=10003), {})
    
    def test_get_ihc_results(self):
        r1 = {'MSN30791': {'MLH1': u'POSITIVE',
                      'MSH2': u'POSITIVE',
                      'PTEN': u'POSITIVE',
                      'RB': u'ND'}}

        
        r2 = {u'MSN30791': {'PTEN': u'POSITIVE'}}

        r3 = {'MSN12104': {'MLH1': 'POSITIVE',
                      'MSH2': 'POSITIVE',
                      'PTEN': 'POSITIVE',
                      'RB': 'ND'},
         'MSN51268': {'MLH1': 'POSITIVE',
                      'MSH2': 'POSITIVE',
                      'PTEN': 'POSITIVE',
                      'RB': 'ND'}}

        self.assertEqual(
            self.data.get_ihc_results(msn='MSN30791'),
            r1
        )
        self.assertEqual(
            self.data.get_ihc_results(bsn='T-16-002222', assays=['PTEN']),
            r2
        )

        self.assertEqual(
            self.data.get_ihc_results(psn=10818),
            r3
        )
