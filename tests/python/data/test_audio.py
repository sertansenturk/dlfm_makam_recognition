from unittest import mock

import pytest

import mlflow
import pandas as pd

from compmusic import dunya
from mre.data import Audio


@pytest.fixture
def mock_tmp_dir(scope="session") -> mock.MagicMock:
    tmp_dir = mock.MagicMock()
    tmp_dir.name = "/tmp/dir_path"

    return tmp_dir


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

    @mock.patch("mre.data.audio.get_run_by_name", return_value=None)
    def test_from_mlflow_no_run(self, mock_run):
        # GIVEN
        audio = Audio()

        # WHEN; THEN
        with pytest.raises(ValueError):
            audio.from_mlflow()
        mock_run.assert_called_once()

    def test_from_mlflow(self):
        # GIVEN
        audio = Audio()
        mock_run = pd.Series({"run_id": "rid1"})
        artifact_names = ["audio1.mp3",
                          "audio2.mp3"]

        # WHEN; THEN
        mock_list = []
        mock_calls = []
        for an in artifact_names:
            tmp_call = mock.MagicMock()
            tmp_call.path = an
            mock_list.append(tmp_call)
            mock_calls.append(mock.call(mock_run.run_id, an))

        with mock.patch("mre.data.audio.get_run_by_name",
                        return_value=mock_run):
            with mock.patch('mlflow.tracking.MlflowClient.__init__',
                            autospec=True,
                            return_value=None):
                with mock.patch.object(mlflow.tracking.MlflowClient,
                                       "list_artifacts",
                                       autospec=True,
                                       return_value=mock_list):
                    with mock.patch.object(mlflow.tracking.MlflowClient,
                                           "download_artifacts"
                                           ) as mock_download_artifacts:
                        _ = audio.from_mlflow()
                        mock_download_artifacts.assert_has_calls(mock_calls)

    @pytest.mark.parametrize("annotation_df", [
        pd.DataFrame([{"mbid": "mbid1", "dunya_uid": "dunya_uid1"}]),
        pd.DataFrame([{"mbid": "mbid1", "dunya_uid": "dunya_uid1"},
                      {"mbid": "mbid2", "dunya_uid": "dunya_uid2"}])])
    def test_from_dunya(self, annotation_df, mock_tmp_dir):
        # GIVEN
        audio = Audio()

        # WHEN
        with mock.patch("mre.data.audio.config",
                        autospec=True):
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
        expected_num_writes = len(annotation_df)

        mock_get_mp3.assert_has_calls(expected_get_mp3_calls)
        mock_open().write.assert_has_calls(expected_write_call)
        assert mock_open().write.call_count == expected_num_writes

    def test_from_dunya_exception_404(self, mock_tmp_dir):
        # GIVEN
        audio = Audio()
        annotation_df = pd.DataFrame(
            [{"mbid": "mbid1", "dunya_uid": "dunya_uid1"}])

        # WHEN
        with mock.patch("mre.data.audio.config",
                        autospec=True):
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
        with mock.patch("mre.data.audio.config",
                        autospec=True):
            with mock.patch("tempfile.TemporaryDirectory",
                            autospec=True,
                            return_value=mock_tmp_dir):
                with mock.patch("compmusic.dunya.docserver.get_mp3"
                                ) as mock_get_mp3:
                    mock_get_mp3.side_effect = dunya.conn.HTTPError(
                        mock.Mock(status=401), 'Unauthorized')
                    with pytest.raises(dunya.conn.HTTPError):
                        _ = audio.from_dunya(annotation_df)

    def test_log(self,
                 mock_tmp_dir):
        # GIVEN
        audio = Audio()

        # WHEN; THEN
        with mock.patch("mre.data.audio.log"
                        ) as mock_log:
            with mock.patch.object(audio,
                                   "tmp_dir",
                                   mock_tmp_dir):
                with mock.patch.object(audio,
                                       "_cleanup"
                                       ) as mock_cleanup:
                    audio.log()

                    mock_log.assert_called_once_with(
                        experiment_name=audio.EXPERIMENT_NAME,
                        run_name=audio.RUN_NAME,
                        artifact_dir=audio._tmp_dir_path(),
                        tags=audio._mlflow_tags()
                    )
                    mock_cleanup.assert_called_once_with()

    def test_mlflow_tags(self):
        # GIVEN
        audio = Audio()

        # WHEN
        result = audio._mlflow_tags()

        # THEN
        expected = {"audio_source": audio.AUDIO_SOURCE}

        assert result == expected
