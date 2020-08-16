from unittest import mock

import pytest

# import mlflow
import pandas as pd

from compmusic import dunya
from mre.data import Audio


@pytest.fixture
def mock_tmp_dir(scope="session") -> mock.MagicMock:
    tmp_dir = mock.MagicMock()
    tmp_dir.name = "/tmp/dir_path"

    return tmp_dir


@pytest.fixture
def mock_experiment(scope="session") -> mock.MagicMock:
    experiment = mock.MagicMock()
    experiment.experiment_id = "mock_id"
    return experiment


class TestAudio:
    def test_cleanup(self):
        # GIVEN
        audio = Audio()

        # WHEN; THEN
        with mock.patch.object(audio, "tmp_dir"):
            with mock.patch.object(audio.tmp_dir,
                                   "cleanup"
                                   ) as mock_cleanup:
                audio._cleanup()
        mock_cleanup.assert_called_once_with()

    @pytest.mark.parametrize("annotation_df", [
        pd.DataFrame([{"mbid": "mbid1", "dunya_uid": "dunya_uid1"}]),
        pd.DataFrame([{"mbid": "mbid1", "dunya_uid": "dunya_uid1"},
                      {"mbid": "mbid2", "dunya_uid": "dunya_uid2"}])])
    def test_from_dunya(self, annotation_df, mock_tmp_dir):
        # GIVEN
        audio = Audio()

        # WHEN
        with mock.patch("tempfile.TemporaryDirectory",
                        autospec=True,
                        return_value=mock_tmp_dir):
            with mock.patch("compmusic.dunya.docserver.get_mp3"
                            ) as mock_get_mp3:
                with mock.patch('builtins.open', mock.mock_open()
                                ) as mock_open:
                    audio.from_dunya(annotation_df)

        # THEN
        expected_get_mp3_calls = [mock.call(val)
                                  for val in annotation_df.dunya_uid]
        expected_write_call = mock_get_mp3()
        num_writes = len(annotation_df)

        mock_get_mp3.assert_has_calls(expected_get_mp3_calls)
        mock_open().write.assert_has_calls(expected_write_call)
        assert mock_open().write.call_count == num_writes

    def test_from_dunya_exception_404(self, mock_tmp_dir):
        # GIVEN
        audio = Audio()
        annotation_df = pd.DataFrame(
            [{"mbid": "mbid1", "dunya_uid": "dunya_uid1"}])

        # WHEN
        with mock.patch("tempfile.TemporaryDirectory",
                        autospec=True,
                        return_value=mock_tmp_dir):
            with mock.patch("compmusic.dunya.docserver.get_mp3"
                            ) as mock_get_mp3:
                mock_get_mp3.side_effect = dunya.conn.HTTPError(
                    mock.Mock(status=404),
                    '404 Client Error: Not Found for url:')

                result = audio.from_dunya(annotation_df)

        # THEN
        result_mbids = list(result.keys())
        expected = ["mbid1"]

        assert result_mbids == expected

    def test_from_dunya_exception_not_404(self, mock_tmp_dir):
        # GIVEN
        audio = Audio()
        annotation_df = pd.DataFrame(
            [{"mbid": "mbid1", "dunya_uid": "dunya_uid1"}])

        # WHEN
        with mock.patch("tempfile.TemporaryDirectory",
                        autospec=True,
                        return_value=mock_tmp_dir):
            with mock.patch("compmusic.dunya.docserver.get_mp3"
                            ) as mock_get_mp3:
                mock_get_mp3.side_effect = dunya.conn.HTTPError(
                    mock.Mock(status=401), 'Unauthorized')
                with pytest.raises(dunya.conn.HTTPError):
                    _ = audio.from_dunya(annotation_df)

    @mock.patch("mlflow.log_artifacts")
    @mock.patch("mlflow.set_tags")
    @mock.patch("mlflow.start_run")
    @mock.patch("mlflow.set_experiment")
    def test_log_no_run(self,
                        mock_mlflow_set_experiment,
                        mock_mlflow_start_run,
                        mock_mlflow_set_tags,
                        mock_mlflow_log_artifacts,
                        mock_tmp_dir,
                        mock_experiment):
        # GIVEN
        audio = Audio()
        mock_run = pd.DataFrame(columns=["run_id"])  # empty

        # WHEN; THEN
        with mock.patch('mlflow.get_experiment_by_name',
                        autospec=True,
                        return_value=mock_experiment):
            with mock.patch('mlflow.search_runs',
                            autospec=True,
                            return_value=mock_run):
                with mock.patch.object(audio,
                                       "tmp_dir",
                                       mock_tmp_dir):
                    with mock.patch.object(audio,
                                           "_cleanup"
                                           ) as mock_cleanup:
                        audio.log()

                        mock_mlflow_set_experiment.assert_called_once()
                        mock_mlflow_start_run.assert_called_once()

                        mock_mlflow_set_tags.assert_called_once()
                        mock_mlflow_log_artifacts.assert_called_once_with(
                            audio._tmp_dir_path())
                        mock_cleanup.assert_called_once_with()
