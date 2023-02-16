# GG Bot Upload Assistant
# Copyright (C) 2022  Noob Master669
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import json
from pathlib import Path

import pytest

from modules.torrent_clients.client_qbittorrent import Qbittorrent
from utilities.utils_reupload import TorrentStatus, AutoReUploaderManager

working_folder = Path(__file__).resolve().parent.parent.parent


class TestAutoReUploaderManager:
    @pytest.fixture()
    def mock_cache(self, mocker):
        yield mocker.patch("modules.cache.Cache")

    @pytest.fixture()
    def mock_client(self, mocker):
        yield mocker.patch("modules.torrent_client.TorrentClient")

    @pytest.fixture()
    def mock_qbit_client(self, mocker):
        mocker.patch(
            "qbittorrentapi.auth.AuthAPIMixIn.auth_log_in", return_value=None
        )
        mocker.patch(
            "os.getenv", side_effect=self.__dynamic_trackers_side_effect
        )
        yield Qbittorrent()

    @pytest.fixture()
    def reupload_manager(self, mock_cache, mock_client):
        yield AutoReUploaderManager(cache=mock_cache, client=mock_client)

    @pytest.fixture()
    def qbit_reupload_manager(self, mock_cache, mock_qbit_client):
        yield AutoReUploaderManager(cache=mock_cache, client=mock_qbit_client)

    def test_initialize_torrent_data(self, reupload_manager):
        input_data = {"hash": "TORRENT_HASH", "name": "TORRENT_NAME"}
        expected = {
            "hash": "TORRENT_HASH",
            "name": "TORRENT_NAME",
            "torrent": json.dumps(input_data),
            "status": TorrentStatus.PENDING,
        }

        init_data = reupload_manager.initialize_torrent_data(input_data)

        assert init_data["id"] is not None
        assert init_data["hash"] == expected["hash"]
        assert init_data["name"] == expected["name"]
        assert init_data["status"] == expected["status"]
        assert init_data["torrent"] == expected["torrent"]
        assert init_data["upload_attempt"] == 1
        assert init_data["movie_db"] == "None"
        assert init_data["possible_matches"] == "None"
        assert init_data["date_created"] is not None

    @pytest.mark.parametrize(
        ("return_data", "expected"),
        [
            pytest.param(None, None, id="status_not_in_cache"),
            pytest.param(
                [{"status": "TORRENT_STATUS"}],
                "TORRENT_STATUS",
                id="status_in_cache",
            ),
            pytest.param([], None, id="status_empty_in_cache"),
        ],
    )
    def test_get_torrent_status(
        self, return_data, expected, reupload_manager, mocker
    ):
        mocker.patch("modules.cache.Cache.get", return_value=return_data)
        assert reupload_manager.get_torrent_status("INFO_HASH") == expected

    @pytest.mark.parametrize(
        ("return_data", "expected"),
        [
            pytest.param(None, False, id="nothing_in_cache"),
            pytest.param(
                [{"status": "READY_FOR_PROCESSING"}],
                False,
                id="status_is_ready_for_processing",
            ),
            pytest.param(
                [{"status": "PENDING"}], False, id="status_is_ready_for_pending"
            ),
            pytest.param(
                [{"status": "SUCCESS"}], True, id="status_is_ready_for_success"
            ),
            pytest.param(
                [{"status": "FAILED"}], True, id="status_is_ready_for_failed"
            ),
            pytest.param(
                [{"status": "PARTIALLY_SUCCESSFUL"}],
                True,
                id="status_is_ready_for_partial_success",
            ),
            pytest.param(
                [{"status": "TMDB_IDENTIFICATION_FAILED"}],
                True,
                id="status_is_ready_for_tmdb_failed",
            ),
            pytest.param(
                [{"status": "DUPE_CHECK_FAILED"}],
                True,
                id="status_is_ready_for_dupe_check_failed",
            ),
            pytest.param(
                [{"status": "UNKNOWN_FAILURE"}],
                True,
                id="status_is_ready_for_unknown_failure",
            ),
            pytest.param([], False, id="empty_status_in_cache"),
        ],
    )
    def test_is_unprocessable_data_present_in_cache(
        self, return_data, expected, reupload_manager, mocker
    ):
        mocker.patch("modules.cache.Cache.get", return_value=return_data)
        assert (
            reupload_manager.is_un_processable_data_present_in_cache(
                "INFO_HASH"
            )
            == expected
        )
        # TODO: renamed method to start with _

    @pytest.mark.parametrize(
        ("torrent", "expected"),
        [
            pytest.param(
                {
                    "upload_attempt": 1,
                    "status": "READY_FOR_PROCESSING",
                    "name": "",
                    "hash": "",
                },
                False,
                id="upload_cannot_be_skipped",
            ),
            pytest.param(
                {
                    "upload_attempt": 2,
                    "status": "UNKNOWN_FAILURE",
                    "name": "",
                    "hash": "",
                },
                False,
                id="upload_cannot_be_skipped",
            ),
            pytest.param(
                {
                    "upload_attempt": 3,
                    "status": "UNKNOWN_FAILURE",
                    "name": "",
                    "hash": "",
                },
                True,
                id="upload_cannot_be_skipped",
            ),
        ],
    )
    def test_should_upload_be_skipped(
        self, torrent, expected, reupload_manager, mocker
    ):
        mocker.patch("modules.cache.Cache.save", return_value=None)
        assert reupload_manager.should_upload_be_skipped(torrent) == expected

    @pytest.mark.parametrize(
        ("return_data", "expected"),
        [
            pytest.param(None, None, id="no_data_in_cache"),
            pytest.param([], None, id="empty_data_in_cache"),
            pytest.param(
                [{"status": "value"}], {"status": "value"}, id="data_in_cache"
            ),
            pytest.param(
                [{"status": "value"}, {"status1": "value1"}],
                {"status": "value"},
                id="multiple_data_in_cache",
            ),
        ],
    )
    def test_get_cached_data(
        self, return_data, expected, reupload_manager, mocker
    ):
        mocker.patch("modules.cache.Cache.get", return_value=return_data)
        assert reupload_manager.get_cached_data("info_hash") == expected

    @pytest.mark.parametrize(
        ("return_data", "new_status", "expected"),
        [
            pytest.param(
                [{"status": "value"}],
                "NEW_STATUS",
                "NEW_STATUS",
                id="updating_status",
            ),
        ],
    )
    def test_update_torrent_status(
        self, return_data, new_status, expected, reupload_manager, mocker
    ):
        mocker.patch("modules.cache.Cache.get", return_value=return_data)
        mocker.patch("modules.cache.Cache.save", return_value=None)
        assert (
            reupload_manager.update_torrent_status("info_hash", new_status)[
                "status"
            ]
            == expected
        )

    @pytest.mark.parametrize(
        ("new_data", "is_json", "return_data", "expected"),
        [
            pytest.param(
                "NEW_DATA",
                False,
                [{"field": "b"}],
                "NEW_DATA",
                id="updating_normal_field",
            ),
            pytest.param(
                {"a": "b", "b": "c"},
                True,
                [{"field": "b"}],
                json.dumps({"a": "b", "b": "c"}),
                id="updating_json_data",
            ),
            pytest.param(
                None, True, [{"field": "b"}], None, id="updating_json_none_data"
            ),
        ],
    )
    def test_update_field(
        self, new_data, is_json, return_data, expected, reupload_manager, mocker
    ):
        mocker.patch("modules.cache.Cache.get", return_value=return_data)
        mocker.patch("modules.cache.Cache.save", return_value=None)
        assert (
            reupload_manager.update_field(
                "info_hash", "field", new_data, is_json
            )["field"]
            == expected
        )

    def test_insert_into_job_repo(self, reupload_manager, mocker):
        data = {"hash": "hash", "tracker": "tracker"}
        mocker.patch("modules.cache.Cache.save", return_value=None)
        assert reupload_manager.insert_into_job_repo(data) == data

    @pytest.mark.parametrize(
        ("cached_data", "movie_db", "expected"),
        [
            pytest.param(None, None, {}, id="no_movie_db_data"),
            pytest.param(None, [], {}, id="empty_movie_db_data"),
            pytest.param(
                None,
                [{"status": "value"}],
                {"status": "value"},
                id="movie_db_in_cache_no_cached_data",
            ),
            pytest.param(
                {},
                [{"status": "value"}],
                {"status": "value"},
                id="movie_db_in_cache_cached_data_without_user_choice",
            ),
            pytest.param(
                {"tmdb_user_choice": ""},
                [{"status": "value"}],
                {},
                id="movie_db_in_cache_cached_data_wit_user_choice",
            ),
        ],
    )
    def test_reupload_get_movie_db_from_cache(
        self, cached_data, movie_db, expected, reupload_manager, mocker
    ):
        mocker.patch("modules.cache.Cache.get", return_value=movie_db)
        assert (
            reupload_manager.reupload_get_movie_db_from_cache(
                cached_data, "", "", ""
            )
            == expected
        )

    @pytest.mark.parametrize(
        ("existing_data", "movie_db", "torrent_info", "expected"),
        [
            pytest.param(
                [{"movie_db": ""}],  # the existing torrent data from cache
                {},
                # this is the moviedb data obtained from `utilities.utils_reupload.reupload_get_movie_db_from_cache`
                {  # this is the metadata in torrent_info
                    "tmdb": "tmdb",
                    "imdb": "imdb",
                    "tvmaze": "tvmaze",
                    "tvdb": "tvdb",
                    "mal": "mal",
                    "type": "type",
                },
                {  # this is the moviedb being saved to cache
                    "tmdb": "tmdb",
                    "imdb": "imdb",
                    "tvmaze": "tvmaze",
                    "tvdb": "tvdb",
                    "mal": "mal",
                    "type": "type",
                    "title": "original_title",
                    "year": "original_year",
                },
                id="no_movie_db_data",
            ),
            pytest.param(
                [{"movie_db": ""}],  # the existing torrent data from cache
                # this is the moviedb data obtained from `utilities.utils_reupload.reupload_get_movie_db_from_cache`
                {"_id": "adsasdasd"},
                {  # this is the metadata in torrent_info
                    "tmdb": "tmdb",
                    "imdb": "imdb",
                    "tvmaze": "tvmaze",
                    "tvdb": "tvdb",
                    "mal": "mal",
                    "type": "type",
                },
                {  # this is the moviedb being saved to cache
                    "tmdb": "tmdb",
                    "_id": "adsasdasd",
                    "imdb": "imdb",
                    "tvmaze": "tvmaze",
                    "tvdb": "tvdb",
                    "mal": "mal",
                    "type": "type",
                    "title": "original_title",
                    "year": "original_year",
                },
                id="_id_in_movie_db",
            ),
            pytest.param(
                [{"movie_db": ""}],  # the existing torrent data from cache
                # this is the moviedb data obtained from `utilities.utils_reupload.reupload_get_movie_db_from_cache`
                {"_id": "adsasdasd", "tmdb": ""},
                {  # this is the metadata in torrent_info
                    "tmdb": "tmdb",
                    "imdb": "imdb",
                    "tvmaze": "tvmaze",
                    "tvdb": "tvdb",
                    "mal": "mal",
                    "type": "type",
                },
                {  # this is the moviedb being saved to cache
                    "tmdb": "tmdb",
                    "imdb": "imdb",
                    "tvmaze": "tvmaze",
                    "tvdb": "tvdb",
                    "mal": "mal",
                    "type": "type",
                    "title": "original_title",
                    "year": "original_year",
                },
                id="tmdb_in_movie_db",
            ),
            pytest.param(
                [{"movie_db": ""}],  # the existing torrent data from cache
                # this is the moviedb data obtained from `utilities.utils_reupload.reupload_get_movie_db_from_cache`
                {"_id": "adsasdasd", "tmdb": ""},
                {  # this is the metadata in torrent_info
                    "tmdb": "tmdb",
                    "tvmaze": "tvmaze",
                    "mal": "mal",
                    "type": "type",
                },
                {  # this is the moviedb being saved to cache
                    "tmdb": "tmdb",
                    "imdb": "0",
                    "tvmaze": "tvmaze",
                    "tvdb": "0",
                    "mal": "mal",
                    "type": "type",
                    "title": "original_title",
                    "year": "original_year",
                },
                id="certain_ids_missing",
            ),
        ],
    )
    def test_reupload_persist_updated_moviedb_to_cache(
        self,
        existing_data,
        movie_db,
        torrent_info,
        expected,
        reupload_manager,
        mocker,
    ):
        mocker.patch("modules.cache.Cache.get", return_value=existing_data)
        mocker.patch("modules.cache.Cache.save", return_value=None)
        assert (
            reupload_manager.reupload_persist_updated_moviedb_to_cache(
                movie_db,
                torrent_info,
                "torrent_hash",
                "original_title",
                "original_year",
            )
            == expected
        )

    @pytest.mark.parametrize(
        ("movie_db", "torrent_info", "cached_data", "required_id", "expected"),
        [
            pytest.param(
                None,
                None,
                {"tmdb_user_choice": "tmdb_user_choice"},
                "tmdb",
                "tmdb_user_choice",
                id="tmdb_user_choice",
            ),
            pytest.param(
                {"tmdb": "tmdb_movie_db"},
                None,
                None,
                "tmdb",
                "tmdb_movie_db",
                id="data_from_movie_db",
            ),
            pytest.param(
                {"tmdb": None}, None, None, "tmdb", "", id="none_in_movie_db"
            ),
            pytest.param(
                {"imdb": "imdb_movie_db"},
                None,
                None,
                "imdb",
                "imdb_movie_db",
                id="imdb_external_id",
            ),
            pytest.param(
                {},
                {"tvmaze": "tvmaze_torrent_info"},
                None,
                "tvmaze",
                "tvmaze_torrent_info",
                id="data_from_torrent_info",
            ),
            pytest.param(
                {},
                {"tvmaze": None},
                "tvmaze",
                None,
                "",
                id="none_in_torrent_info",
            ),
        ],
    )
    def test_reupload_get_external_id_based_on_priority(
        self,
        movie_db,
        torrent_info,
        cached_data,
        required_id,
        expected,
        reupload_manager,
    ):
        assert (
            reupload_manager.reupload_get_external_id_based_on_priority(
                movie_db, torrent_info, cached_data, required_id
            )
            == expected
        )

    @pytest.mark.parametrize(
        ("cache_get_data", "list_torrents_data", "expected"),
        [
            pytest.param(
                [{"status": "PENDING"}],
                [
                    {"completed": "100", "size": "200", "hash": "hash1"},
                    {"completed": "200", "size": "200", "hash": "hash2"},
                ],
                [{"completed": "200", "size": "200", "hash": "hash2"}],
                id="processable_torrents_present",
            ),
            pytest.param(
                [{"status": "FAILED"}],
                [
                    {"completed": "100", "size": "200", "hash": "hash1"},
                    {"completed": "200", "size": "200", "hash": "hash2"},
                ],
                [],
                id="processable_torrents_not_present",
            ),
        ],
    )
    def test_reupload_get_processable_torrents(
        self,
        cache_get_data,
        list_torrents_data,
        expected,
        reupload_manager,
        mocker,
    ):
        mocker.patch("modules.cache.Cache.get", return_value=cache_get_data)

        mocker.patch(
            "modules.torrent_client.TorrentClient.list_torrents",
            return_value=list_torrents_data,
        )

        assert reupload_manager.get_processable_torrents() == expected

    @staticmethod
    def __torrent_path_not_translation_side_effect(param, default=None):
        if param == "translation_needed":
            return False
        else:
            return default

    @staticmethod
    def __torrent_path_translation_side_effect(param, default=None):
        if param == "translation_needed":
            return True
        elif param == "uploader_accessible_path":
            return "/uploader/path/"
        elif param == "client_accessible_path":
            return "/client/location/"
        else:
            return default

    @pytest.mark.parametrize(
        ("torrent_path", "expected_path"),
        [
            pytest.param(
                "/client/location/to/media/file.mkv",
                "/uploader/path/to/media/file.mkv",
                id="torrent_path_translation_needed",
            )
        ],
    )
    def test_reupload_get_translated_torrent_path(
        self, torrent_path, expected_path, reupload_manager, mocker
    ):
        mocker.patch(
            "os.getenv", side_effect=self.__torrent_path_translation_side_effect
        )
        assert (
            reupload_manager.reupload_get_translated_torrent_path(torrent_path)
            == expected_path
        )

    @pytest.mark.parametrize(
        ("torrent_path", "expected_path"),
        [
            pytest.param(
                "/client/location/to/media/file.mkv",
                "/client/location/to/media/file.mkv",
                id="torrent_path_translation_not_needed",
            )
        ],
    )
    def test_reupload_get_no_translated_torrent_path(
        self, torrent_path, expected_path, reupload_manager, mocker
    ):
        mocker.patch(
            "os.getenv",
            side_effect=self.__torrent_path_not_translation_side_effect,
        )
        assert (
            reupload_manager.reupload_get_translated_torrent_path(torrent_path)
            == expected_path
        )

    @staticmethod
    def __dynamic_trackers_side_effect(param, default=None):
        if param == "dynamic_tracker_selection":
            return True
        return default

    @pytest.mark.parametrize(
        ("torrent", "upload_to_trackers", "api_keys_dict", "expected"),
        [
            pytest.param(
                {"category": "GGBOT::TSP::ATH", "name": "Torrent.Name"},
                ["BHD, BLU"],
                {
                    "tsp_api_key": "YES",
                    "ath_api_key": "YES",
                    "bhd_api_key": "YES",
                    "blu_api_key": "YES",
                },
                ["TSP", "ATH"],
                id="dynamic_trackers_yes",
            ),
            pytest.param(
                {"category": "GGBOT::TSP::ATH", "name": "Torrent.Name"},
                ["BHD, BLU"],
                {
                    "tsp_api_key": "YES",
                    "bhd_api_key": "YES",
                    "blu_api_key": "YES",
                },
                ["TSP"],
                id="dynamic_trackers_yes",
            ),
            pytest.param(
                {
                    "category": "GGBOT::TSP::ATH::BHD::BHDTV",
                    "name": "Torrent.Name",
                },
                ["BHD, BLU"],
                {
                    "tsp_api_key": "YES",
                    "bhd_api_key": "YES",
                    "blu_api_key": "YES",
                },
                ["TSP", "BHD"],
                id="dynamic_trackers_yes",
            ),
            pytest.param(
                {"category": "GGBOT::TSP::ATH", "name": "Torrent.Name"},
                ["BHD, BLU"],
                {
                    "bhd_api_key": "YES",
                    "blu_api_key": "YES",
                },
                ["BHD, BLU"],
                id="dynamic_trackers_validation_failed",
            ),
            pytest.param(
                {"category": "GGBOT::TSP::", "name": "Torrent.Name"},
                ["BHD, BLU"],
                {
                    "bhd_api_key": "YES",
                    "blu_api_key": "YES",
                },
                ["BHD, BLU"],
                id="dynamic_trackers_validation_failed",
            ),
        ],
    )
    def test_get_available_dynamic_trackers_qbittorrnet(
        self,
        torrent,
        upload_to_trackers,
        api_keys_dict,
        expected,
        qbit_reupload_manager,
    ):
        assert (
            qbit_reupload_manager.get_available_dynamic_trackers(
                torrent=torrent,
                original_upload_to_trackers=upload_to_trackers,
                api_keys_dict=api_keys_dict,
                all_trackers_list=json.load(
                    open(f"{working_folder}/parameters/tracker/acronyms.json")
                ).keys(),
            )
            == expected
        )

    @pytest.mark.parametrize(
        ("torrent", "current_status", "expected"),
        [
            pytest.param(
                {"hash": "info_hash"},
                [{"status": "PENDING"}],
                "SUCCESS",
                id="upload_success_status_pending",
            ),
            pytest.param(
                {"hash": "info_hash"},
                [{"status": "READY_FOR_PROCESSING"}],
                "SUCCESS",
                id="upload_success_status_ready",
            ),
            pytest.param(
                {"hash": "info_hash"},
                [{"status": "FAILED"}],
                "PARTIALLY_SUCCESSFUL",
                id="upload_success_status_failed",
            ),
            pytest.param(
                {"hash": "info_hash"},
                [{"status": "TMDB_IDENTIFICATION_FAILED"}],
                "TMDB_IDENTIFICATION_FAILED",
                id="invalid_status_return_from_cache",
            ),
        ],
    )
    def test_update_success_status_for_torrent_upload(
        self, torrent, current_status, expected, reupload_manager, mocker
    ):
        mocker.patch("modules.cache.Cache.get", return_value=current_status)

        assert (
            reupload_manager.update_success_status_for_torrent_upload(
                torrent, "TRACKER", {}
            )
            == expected
        )

    @pytest.mark.parametrize(
        ("torrent", "current_status", "expected"),
        [
            pytest.param(
                {"hash": "info_hash"},
                [{"status": "PENDING"}],
                "FAILED",
                id="upload_failed_status_pending",
            ),
            pytest.param(
                {"hash": "info_hash"},
                [{"status": "READY_FOR_PROCESSING"}],
                "FAILED",
                id="upload_failed_status_ready",
            ),
            pytest.param(
                {"hash": "info_hash"},
                [{"status": "SUCCESS"}],
                "PARTIALLY_SUCCESSFUL",
                id="upload_failed_status_success",
            ),
            pytest.param(
                {"hash": "info_hash"},
                [{"status": "TMDB_IDENTIFICATION_FAILED"}],
                "TMDB_IDENTIFICATION_FAILED",
                id="invalid_status_return_from_cache",
            ),
        ],
    )
    def test_update_failure_status_for_torrent_upload(
        self, torrent, current_status, expected, reupload_manager, mocker
    ):
        mocker.patch("modules.cache.Cache.get", return_value=current_status)

        assert (
            reupload_manager.update_failure_status_for_torrent_upload(
                torrent, "TRACKER", {}
            )
            == expected
        )
