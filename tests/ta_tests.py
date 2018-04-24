#!/usr/bin/env python3
import sys
import os
import unittest

from matchbox_api_utils import TreatmentArms
from matchbox_api_utils import utils


class TreatmentArmTests(unittest.TestCase):
    # Stick with live queries; they're not too bad.
    ta_data = TreatmentArms(matchbox='adult-matchbox')

    def test_amoi_mapping(self):
        variant1 = {
            'type' : 'snvs_indels',
            'gene'         : 'BRAF',
            'identifier'        : 'COSM476',
            'oncominevariantclass' : 'Hotspot',
            'exon'         : '15',
            'function'     : 'missense'
        }

        variant2 = {
            'type' : 'snvs_indels',
            'gene'         : 'PTEN',
            'identifier'        : '.',
            'oncominevariantclass' : 'Deleterious',
            'exon'         : '4',
            'function'     : 'nonsense'
        }

        variant3 = {
            'type' : 'cnvs',
            'gene'         : 'ERBB2',
            'identifier'        : '.',
            'oncominevariantclass' : '.',
            'exon'         : '.',
            'function'     : '.'
        }

        variant4 = {
            'type' : 'fusions',
            'gene'         : 'ALK',
            'identifier'        : 'ALK-PTPN3.A11P3',
            'oncominevariantclass' : 'fusion',
            'exon'         : '.',
            'function'     : '.'
        }

        variant5 = {
            'type' : 'snvs_indels',
            'gene'         : 'EGFR',
            'identifier'        : '.',
            'oncominevariantclass' : '.',
            'exon'         : '19',
            'function'     : 'nonframeshiftDeletion'
        }

        variant6 = {
            'type' : 'snvs_indels',
            'gene'         : 'ERBB2',
            'identifier'        : '.',
            'oncominevariantclass' : '.',
            'exon'         : '20',
            'function'     : 'nonframeshiftInsertion'
        }

        variant7 = {
            'type' : 'snvs_indels',
            'gene'         : 'TP53',
            'identifier'        : 'COSM10660',
            'oncominevariantclass' : 'Hotspot',
            'exon'         : '8',
            'function'     : 'missense'
        }

        test_cases = {
            'case1' : (
                variant1, 
                ['EAY131-Y(e)','EAY131-P(e)', 'EAY131-N(e)', 'EAY131-H(i)']
            ),
            'case2' : (
                variant2, 
                ['EAY131-N(i)', 'EAY131-I(e)', 'EAY131-IX1(e)']
            ),
            'case3' : (
                variant3, 
                ['EAY131-Q(i)', 'EAY131-J(i)', 'EAY131-QX1(i)']
            ),
            'case4' : (variant4, ['EAY131-F(i)'] ),
            'case5' : (variant5, ['EAY131-A(i)'] ),
            'case6' : (variant6, ['EAY131-B(i)', 'EAY131-BX1(i)']),
            'case7' : (variant7, None),
        }

        for case in test_cases:
            result = self.ta_data.map_amoi(test_cases[case][0])
            if result is not None:
                result = sorted(result)
            answer = test_cases[case][1]
            if answer is not None:
                answer = sorted(answer)
            self.assertEqual(result, answer)

    def test_map_drug_arm(self):
        res = self.ta_data.map_drug_arm(armid='EAY131-Z1A')
        self.assertEqual(res, ('EAY131-Z1A', 'Binimetinib', '788187'))

        res = self.ta_data.map_drug_arm(drugname='Afatinib')
        self.assertEqual(
            res, 
            [
                ('EAY131-A', 'Afatinib', '750691'),
                ('EAY131-B', 'Afatinib', '750691'),
                ('EAY131-BX1', 'Afatinib', '750691')
            ]
        )

        res = self.ta_data.map_drug_arm(drugcode='750691')
        self.assertEqual(
            res, 
            [
                ('EAY131-A', 'Afatinib', '750691'),
                ('EAY131-B', 'Afatinib', '750691'),
                ('EAY131-BX1', 'Afatinib', '750691')
            ]
        )

        self.assertIsNone(self.ta_data.map_drug_arm(drugname='Tylenol'))

    def test_get_exlusion_disease(self):
        self.assertListEqual(
            self.ta_data.get_exclusion_disease('EAY131-Z1A'),
            ['Melanoma']
        )

        self.assertIsNone(self.ta_data.get_exclusion_disease('EAY131-Y'))

        self.assertListEqual(
            self.ta_data.get_exclusion_disease('EAY131-A'),
            [
                'Bronchioloalveolar carcinoma', 
                'Lung adenocar. w/ bronch. feat.',
                'Lung adenocarcinoma', 
                'Non-small cell lung cancer, NOS',
                'Small Cell Lung Cancer', 
                'Squamous cell lung carcinoma'
            ]
        )
