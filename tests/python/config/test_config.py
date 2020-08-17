import os
from unittest import mock

from mre.config import config


class TestRead:
    @mock.patch.object(config.configparser.ConfigParser, 'read')
    def test_read(self, mock_read):
        # WHEN
        config.read()

        # THEN
        mock_read.assert_called_once_with(config._get_config_filepath())

    @mock.patch.object(config.configparser.ConfigParser, 'read')
    def test_read_secrets(self, mock_read):
        # WHEN
        config.read_secrets()

        # THEN
        mock_read.assert_called_once_with(config._get_secrets_filepath())


def test_get_config_filepath():
    # WHEN
    path = config._get_config_filepath()

    # THEN
    assert os.path.exists(path)
