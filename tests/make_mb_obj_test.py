from unittest import TestCase
from matchbox_api_utils.Matchbox import MatchboxData

class MatchboxConnectTest(TestCase):
    def setUp(self):
        self.matchbox = MatchboxData(...)

    def tearDown(self):
        self.matchbox.dispose()
        self.matchbox = None
