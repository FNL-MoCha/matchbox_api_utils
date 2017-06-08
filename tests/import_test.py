from unittest import TestCase
from matchbox_api_utils.Matchbox import Matchbox, MatchboxData

class TestImport(TestCase):
    def test_can_import(self):
        self.func = MatchboxData()
