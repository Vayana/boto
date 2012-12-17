#!/usr/bin/env python
from datetime import datetime, timedelta

from tests.unit import unittest
import mock

from boto import provider


class TestProvider(unittest.TestCase):
    def setUp(self):
        self.environ = {}
        self.config = {}

        self.metadata_patch = mock.patch('boto.utils.get_instance_metadata')
        self.config_patch = mock.patch('boto.provider.config.get',
                                       self.get_config)
        self.has_config_patch = mock.patch('boto.provider.config.has_option',
                                           self.has_config)
        self.environ_patch = mock.patch('os.environ', self.environ)

        self.get_instance_metadata = self.metadata_patch.start()
        self.config_patch.start()
        self.has_config_patch.start()
        self.environ_patch.start()


    def tearDown(self):
        self.metadata_patch.stop()
        self.config_patch.stop()
        self.has_config_patch.stop()
        self.environ_patch.stop()

    def has_config(self, section_name, key):
        try:
            self.config[section_name][key]
            return True
        except KeyError:
            return False

    def get_config(self, section_name, key):
        try:
            return self.config[section_name][key]
        except KeyError:
            return None

    def test_passed_in_values_are_used(self):
        p = provider.Provider('aws', 'access_key', 'secret_key', 'security_token')
        self.assertEqual(p.access_key, 'access_key')
        self.assertEqual(p.secret_key, 'secret_key')
        self.assertEqual(p.security_token, 'security_token')

    def test_environment_variables_are_used(self):
        self.environ['AWS_ACCESS_KEY_ID'] = 'env_access_key'
        self.environ['AWS_SECRET_ACCESS_KEY'] = 'env_secret_key'
        p = provider.Provider('aws')
        self.assertEqual(p.access_key, 'env_access_key')
        self.assertEqual(p.secret_key, 'env_secret_key')
        self.assertIsNone(p.security_token)

    def test_config_values_are_used(self):
        self.config = {
            'Credentials': {
                'aws_access_key_id': 'cfg_access_key',
                'aws_secret_access_key': 'cfg_secret_key',
            }
        }
        p = provider.Provider('aws')
        self.assertEqual(p.access_key, 'cfg_access_key')
        self.assertEqual(p.secret_key, 'cfg_secret_key')
        self.assertIsNone(p.security_token)

    def test_env_vars_beat_config_values(self):
        self.environ['AWS_ACCESS_KEY_ID'] = 'env_access_key'
        self.environ['AWS_SECRET_ACCESS_KEY'] = 'env_secret_key'
        self.config = {
            'Credentials': {
                'aws_access_key_id': 'cfg_access_key',
                'aws_secret_access_key': 'cfg_secret_key',
            }
        }
        p = provider.Provider('aws')
        self.assertEqual(p.access_key, 'env_access_key')
        self.assertEqual(p.secret_key, 'env_secret_key')
        self.assertIsNone(p.security_token)

    def test_metadata_server_credentials(self):
        instance_config = {
            'iam': {
                'security-credentials': {
                    'allowall': {'AccessKeyId': 'iam_access_key',
                                 'Code': 'Success',
                                 'Expiration': '2012-09-01T03:57:34Z',
                                 'LastUpdated': '2012-08-31T21:43:40Z',
                                 'SecretAccessKey': 'iam_secret_key',
                                 'Token': 'iam_token',
                                 'Type': 'AWS-HMAC'}
                }
            }
        }
        self.get_instance_metadata.return_value = instance_config
        p = provider.Provider('aws')
        self.assertEqual(p.access_key, 'iam_access_key')
        self.assertEqual(p.secret_key, 'iam_secret_key')
        self.assertEqual(p.security_token, 'iam_token')

    def test_refresh_credentials(self):
        now = datetime.now()
        first_expiration = (now + timedelta(seconds=10)).strftime(
            "%Y-%m-%dT%H:%M:%SZ")
        credentials = {
            'AccessKeyId': 'first_access_key',
            'Code': 'Success',
            'Expiration': first_expiration,
            'LastUpdated': '2012-08-31T21:43:40Z',
            'SecretAccessKey': b'first_secret_key',
            'Token': 'first_token',
            'Type': 'AWS-HMAC'
        }
        instance_config = {
            'iam': {
                'security-credentials': {
                    'allowall': credentials
                }
            }
        }
        self.get_instance_metadata.return_value = instance_config
        p = provider.Provider('aws')
        self.assertEqual(p.access_key, 'first_access_key')
        self.assertEqual(p.secret_key, b'first_secret_key')
        self.assertEqual(p.security_token, 'first_token')
        self.assertIsNotNone(p._credential_expiry_time)

        # Now set the expiration to something in the past.
        expired = now - timedelta(seconds=20)
        p._credential_expiry_time = expired
        credentials['AccessKeyId'] = 'second_access_key'
        credentials['SecretAccessKey'] = b'second_secret_key'
        credentials['Token'] = 'second_token'
        self.get_instance_metadata.return_value = instance_config

        # Now upon attribute access, the credentials should be updated.
        self.assertEqual(p.access_key, 'second_access_key')
        self.assertEqual(p.secret_key, b'second_secret_key')
        self.assertEqual(p.security_token, 'second_token')


if __name__ == '__main__':
    unittest.main()
