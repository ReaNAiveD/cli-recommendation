import unittest

from common.util import parse_command_info


class TestUtil(unittest.TestCase):
    def test_parse_command_info(self):
        self.assertEqual(parse_command_info('az acr build <SOURCE_LOCATION> --registry $acrName --image $imageName --file $dockerfilePath'),
                         ('az acr build', ['<SOURCE_LOCATION>', '--registry', '--image', '--file']))
