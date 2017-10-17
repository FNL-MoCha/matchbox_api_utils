#!/usr/bin/env python
import sys
import os
import unittest
from matchbox_api_utils import TreatmentArms


class TreatmentArmTests(unittest.TestCase):
    raw_data = os.path.join(os.path.dirname(__file__),'../raw_ta_dump_072717.json')
    arms = TreatmentArms(load_raw=raw_data)

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
        'case1' : (variant1, ['EAY131-Y(e)','EAY131-P(e)', 'EAY131-N(e)', 'EAY131-H(i)'] ),
        'case2' : (variant2, ['EAY131-N(i)', 'EAY131-I(e)', 'EAY131-IX1(e)'] ),
        'case3' : (variant3, ['EAY131-Q(i)', 'EAY131-J(i)', 'EAY131-QX1(i)'] ),
        'case4' : (variant4, ['EAY131-F(i)'] ),
        'case5' : (variant5, ['EAY131-A(i)'] ),
        'case6' : (variant6, ['EAY131-B(i)', 'EAY131-BX1(i)']),
        'case7' : (variant7, None),
    }

    def test_amoi_mapping(self):
        for case in self.test_cases:
            result = self.arms.map_amoi(self.test_cases[case][0])
            if result is not None:
                result = sorted(result)
            answer = self.test_cases[case][1]
            if answer is not None:
                answer = sorted(answer)
            # self.assertEqual(self.arms.map_amoi(self.test_cases[case][0]), self.test_cases[case][1])
            self.assertEqual(result, answer)
