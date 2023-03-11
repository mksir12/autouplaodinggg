# GG Bot Upload Assistant
# Copyright (C) 2022  Noob Master669
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import datetime
import json
import logging
import uuid
from pprint import pformat
from typing import Dict, Tuple, Union, Any

from modules.cache import Cache
from modules.config import ReUploaderConfig
from modules.torrent_client import TorrentClient
from utilities.utils import get_and_validate_configured_trackers

TORRENT_DB_KEY_PREFIX = "ReUpload::Torrent"
JOB_REPO_DB_KEY_PREFIX = "ReUpload::JobRepository"
TMDB_DB_KEY_PREFIX = "MetaData::TMDB"
UPLOAD_RETRY_LIMIT = 3


class TrackerUploadStatus:
    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    DUPE = "DUPE"
    BANNED_GROUP = "BANNED_GROUP"
    PAYLOAD_ERROR = "PAYLOAD_ERROR"


class TorrentStatus:
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    PARTIALLY_SUCCESSFUL = "PARTIALLY_SUCCESSFUL"
    TMDB_IDENTIFICATION_FAILED = "TMDB_IDENTIFICATION_FAILED"
    PENDING = "PENDING"
    DUPE_CHECK_FAILED = "DUPE_CHECK_FAILED"
    READY_FOR_PROCESSING = "READY_FOR_PROCESSING"
    KNOWN_FAILURE = "KNOWN_FAILURE"
    # unrecoverable error. Needs to check the log or console to resolve them. Not automatic fix available
    UNKNOWN_FAILURE = "UNKNOWN_FAILURE"


class TorrentFailureStatus:
    RAR_EXTRACTION_FAILED = "RAR_EXTRACTION_FAILED"
    TMDB_IDENTIFICATION_FAILED = "TMDB_IDENTIFICATION_FAILED"
    DUPE_CHECK_FAILED = "DUPE_CHECK_FAILED"
    TYPE_AND_BASIC_INFO_ERROR = "TYPE_AND_BASIC_INFO_ERROR"
    UNKNOWN_FAILURE = "UNKNOWN_FAILURE"


torrent_failure_messages = {
    TorrentFailureStatus.RAR_EXTRACTION_FAILED: "Failed to extract rared contents",
    TorrentFailureStatus.TMDB_IDENTIFICATION_FAILED: "Failed to identify proper TMDb ID",
    TorrentFailureStatus.TYPE_AND_BASIC_INFO_ERROR: "Type and basic info of the torrent could not be identified.",
    TorrentFailureStatus.DUPE_CHECK_FAILED: "A dupe of this torrent already exists in tracker",
    TorrentFailureStatus.UNKNOWN_FAILURE: "Unknown Failure. Please get in touch with dev :(",
}

client_labels_for_failure = {
    TorrentFailureStatus.RAR_EXTRACTION_FAILED: "GGBOT_ERROR_RAR_EXTRACTION",
    TorrentFailureStatus.TMDB_IDENTIFICATION_FAILED: "TMDB_IDENTIFICATION_FAILED",
    TorrentFailureStatus.TYPE_AND_BASIC_INFO_ERROR: "GGBOT_ERROR_TYPE_AND_BASIC",
    TorrentFailureStatus.DUPE_CHECK_FAILED: "DUPE_CHECK_FAILED",
    TorrentFailureStatus.UNKNOWN_FAILURE: "GGBOT_ERROR_UNKNOWN_FAILURE",
}


class JobStatus:
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class AutoReUploaderManager:
    def __init__(self, *, cache: Cache, client: TorrentClient):
        self.cache = cache
        self.client = client
        reuploader_config = ReUploaderConfig()
        self.dynamic_tracker_selection_enabled: bool = (
            reuploader_config.DYNAMIC_TRACKER_SELECTION
        )
        self.perform_path_translation: bool = reuploader_config.TRANSLATE_PATH
        self.torrent_client_accessible_path: bool = (
            reuploader_config.TORRENT_CLIENT_PATH
        )
        self.uploader_accessible_path: bool = reuploader_config.UPLOADER_PATH

    @staticmethod
    def get_unique_id():
        return str(uuid.uuid4())

    def get_torrent_status(self, info_hash):
        data = self.cache.get(f"{TORRENT_DB_KEY_PREFIX}::{info_hash}")
        return data[0]["status"] if data is not None and len(data) > 0 else None

    def is_un_processable_data_present_in_cache(self, info_hash):
        """
        cached_data = cache.get(f'{TORRENT_DB_KEY_PREFIX}::{info_hash}', "status")
        return cached_data is not None and cached_data not in [TorrentStatus.READY_FOR_PROCESSING, TorrentStatus.PENDING]

        """
        # torrents in pending or ready for processing can be uploaded again.
        # torrents that are in other statuses needs no more processing
        torrent_status = self.get_torrent_status(info_hash)
        # status that are not mentioned below cannot be processed again by the uploader automatically
        return torrent_status is not None and torrent_status not in [
            TorrentStatus.READY_FOR_PROCESSING,
            TorrentStatus.PENDING,
        ]

    def initialize_torrent(self, torrent: Dict) -> Dict:
        logging.debug(
            f'[AutoReUploaderManager::initialize_torrent_data] Initializing torrent data in cache for {torrent["name"]}'
        )
        init_data = {
            "id": self.get_unique_id(),
            "hash": torrent["hash"],
            "name": torrent["name"],
            "status": TorrentStatus.PENDING,
            "torrent": json.dumps(torrent),
            "upload_attempt": 1,
            "movie_db": "None",
            "date_created": datetime.datetime.now().isoformat(),
            "possible_matches": "None",
        }
        # when this attempt becomes greater than 3, the torrent will be marked as UNKNOWN_FAILURE
        self.cache.save(
            f'{TORRENT_DB_KEY_PREFIX}::{torrent["hash"]}', init_data
        )
        logging.debug(
            f'[AutoReUploaderManager::initialize_torrent_data] Successfully initialized torrent data in cache for {torrent["name"]} '
        )
        return init_data  # adding return for testing

    def skip_reupload(self, torrent: Dict) -> bool:
        logging.info(
            f'[ReUploadUtils] Updating upload attempt for torrent {torrent["name"]}'
        )
        torrent["upload_attempt"] = torrent["upload_attempt"] + 1
        if torrent["upload_attempt"] > UPLOAD_RETRY_LIMIT:
            torrent["status"] = TorrentStatus.UNKNOWN_FAILURE
        self.cache.save(f'{TORRENT_DB_KEY_PREFIX}::{torrent["hash"]}', torrent)
        return torrent["upload_attempt"] > UPLOAD_RETRY_LIMIT

    def get_cached_data(self, info_hash: str) -> Dict:
        data = self.cache.get(f"{TORRENT_DB_KEY_PREFIX}::{info_hash}")
        return data[0] if data is not None and len(data) > 0 else None

    def update_torrent_status(self, info_hash, status):
        # data will always be present
        existing_data = self.cache.get(f"{TORRENT_DB_KEY_PREFIX}::{info_hash}")[
            0
        ]
        logging.debug(
            f'[ReUploadUtils] Updating status of `{info_hash}` from `{existing_data["status"]}` to `{status}`'
        )
        existing_data["status"] = status
        self.cache.save(f"{TORRENT_DB_KEY_PREFIX}::{info_hash}", existing_data)
        return existing_data  # returning data for testing

    def update_torrent_field(self, info_hash, field, data, is_json):
        # data will always be present
        existing_data = self.cache.get(f"{TORRENT_DB_KEY_PREFIX}::{info_hash}")[
            0
        ]
        if is_json and data is not None:
            data = json.dumps(data)
        logging.debug(
            f"[ReUploadUtils] Updating `{field}` of `{info_hash}` from `{existing_data[field]}` to `{data}`"
        )
        existing_data[field] = data
        self.cache.save(f"{TORRENT_DB_KEY_PREFIX}::{info_hash}", existing_data)
        return existing_data  # returning data for testing

    def insert_into_job_repo(self, job_repo_entry):
        logging.debug(
            f'[ReUploadUtils] Saving job entry in cache for {job_repo_entry["hash"]}'
        )
        self.cache.save(
            f'{JOB_REPO_DB_KEY_PREFIX}::{job_repo_entry["hash"]}::{job_repo_entry["tracker"]}',
            job_repo_entry,
        )
        logging.debug(
            f'[ReUploadUtils] Successfully saved job entry in cache for {job_repo_entry["hash"]}'
        )
        return job_repo_entry  # returning data for testing

    def _cache_tmdb_selection(self, movie_db):
        self.cache.save(
            f'{TMDB_DB_KEY_PREFIX}::{movie_db["title"]}@{movie_db["year"]}',
            movie_db,
        )

    def _check_for_tmdb_cached_data(self, title, year, content_type):
        data = self.cache.get(
            f"{TMDB_DB_KEY_PREFIX}",
            {
                "$or": [
                    {
                        "$and": [
                            {"type": content_type},
                            {"$and": [{"title": title}, {"year": year}]},
                        ]
                    },
                    {"$and": [{"type": content_type}, {"title": title}]},
                ]
            },
        )
        return data[0] if data is not None and len(data) > 0 else None

    def cached_moviedb_details(self, cached_data, title, year, upload_type):
        movie_db = self._check_for_tmdb_cached_data(title, year, upload_type)
        logging.debug(
            f"[ReUploadUtils] MovieDB data obtained from cache: {pformat(movie_db)}"
        )

        # if we don't have any movie_db data cached in tmdb repo, repo then we'll initialize the movie_db
        # dictionary.cache similarly if there is a user provided tmdb id (from gg-bot-visor) then we'll give higher
        # priority to users choice and clear the cached movie_db
        if movie_db is None or (
            cached_data is not None and "tmdb_user_choice" in cached_data
        ):
            return {}
        return movie_db

    def cache_moviedb_data(
        self,
        movie_db,
        torrent_info,
        torrent_hash,
        original_title,
        original_year,
    ):
        # checking whether we got any data or whether it was an empty dict
        cache_tmdb_metadata = "tmdb" not in movie_db

        movie_db["tmdb"] = (
            torrent_info["tmdb"] if "tmdb" in torrent_info else "0"
        )
        movie_db["imdb"] = (
            torrent_info["imdb"] if "imdb" in torrent_info else "0"
        )
        movie_db["tvmaze"] = (
            torrent_info["tvmaze"] if "tvmaze" in torrent_info else "0"
        )
        movie_db["tvdb"] = (
            torrent_info["tvdb"] if "tvdb" in torrent_info else "0"
        )
        movie_db["mal"] = torrent_info["mal"] if "mal" in torrent_info else "0"
        movie_db["title"] = original_title
        movie_db["year"] = original_year
        movie_db["type"] = torrent_info["type"]
        backup_id = None

        if "_id" in movie_db:
            backup_id = movie_db["_id"]
            del movie_db["_id"]

        self.update_torrent_field(torrent_hash, "movie_db", movie_db, True)

        if cache_tmdb_metadata:
            if backup_id is not None:
                movie_db["_id"] = backup_id
            self._cache_tmdb_selection(movie_db)

        return movie_db

    @staticmethod
    def get_external_moviedb_id(
        movie_db, torrent_info, cached_data, required_id
    ):
        # in case of tmdb id, we need to give the highest priority to the golden data obtained from the user via
        # GG-BOT Visor If bot wants tmdb id, and we have data in cached data (for currently uploading torrent) then
        # we return it. Otherwise, we go for the cached movieDB data (from another torrent) and finally we get the
        # data from media_info_summary
        if required_id == "tmdb":
            if cached_data is not None and "tmdb_user_choice" in cached_data:
                # this is value provided by the user. This will never be None and is considered as ~~ GOLDEN ~~
                # TMDB id from GG-BOT Visor
                return str(cached_data["tmdb_user_choice"])

        external_db_id = ""
        if (
            required_id in movie_db
        ):  # TODO need to figure out why None is saved in metadata db
            external_db_id = (
                str(movie_db[required_id])
                if movie_db[required_id] is not None
                else ""
            )
        elif required_id in torrent_info:
            external_db_id = (
                str(torrent_info[required_id])
                if torrent_info[required_id] is not None
                else ""
            )
        return external_db_id

    def get_processable_torrents(self):
        logging.info(
            "[ReUploadUtils] Listing latest torrents status from client"
        )
        # listing all the torrents that needs to be re-uploaded
        torrents = self.client.list_torrents()

        # Attributes present in the torrent list
        # "category", "completed", "content_path", "hash", "name", "save_path", "size", "tracker"
        logging.info(
            f"[ReUploadUtils] Total number of torrents that needs to be reuploaded are {len(torrents)}"
        )

        # listing out only the completed torrents and eliminating unprocessable torrents based on cached data
        logging.debug(
            f"[ReUploadUtils] Torrent data from client: {pformat(torrents)}"
        )
        torrents = list(
            filter(
                lambda torrent: not self.is_un_processable_data_present_in_cache(
                    torrent["hash"]
                ),
                filter(
                    lambda torrent: torrent["completed"] == torrent["size"],
                    torrents,
                ),
            )
        )
        logging.info(
            f"[ReUploadUtils] Total number of completed torrents that needs to be reuploaded are {len(torrents)}"
        )
        return torrents

    def translate_torrent_path(self, torrent_path: str) -> str:
        if not self.perform_path_translation:
            logging.info("[ReUploadUtils] No path translations needed.")
            return torrent_path

        logging.info(
            '[ReUploadUtils] Translating paths... ("translation_needed" flag set to True in reupload.config.env) '
        )

        # Just in case the user didn't end the path with a forward slash...
        host_path = f"{self.uploader_accessible_path}/".replace("//", "/")
        remote_path = f"{self.torrent_client_accessible_path}/".replace(
            "//", "/"
        )
        logging.info(f"[ReUploadUtils] Host path of the torrent: {host_path}")
        logging.info(
            f"[ReUploadUtils] Remote path of the torrent: {remote_path}"
        )

        translated_path = str(torrent_path).replace(remote_path, host_path)
        # And finally log the changes
        logging.info(
            f"[ReUploadUtils] Remote path (torrent_path) of the torrent: {torrent_path}"
        )
        logging.info(
            f"[ReUploadUtils] Translated path of the torrent: {translated_path}"
        )
        return translated_path

    def get_trackers_dynamically(
        self,
        torrent,
        original_upload_to_trackers,
        api_keys_dict,
        all_trackers_list,
    ):
        if not self.dynamic_tracker_selection_enabled:
            # well, no need to select trackers dynamically or no valid dynamic trackers (exception case)
            return original_upload_to_trackers

        # try to dynamically select the trackers to upload to from the torrent label.
        logging.info(
            "[ReUploadUtils] Uploader running in dynamic tracker section mode. Attempting to resolve any dynamic "
            "trackers"
        )
        dynamic_trackers = None
        try:
            dynamic_trackers = self.client.get_dynamic_trackers(torrent)
            logging.info(
                f"[ReUploadUtils] Dynamic trackers obtained from the torrent {torrent['name']} are {dynamic_trackers}"
            )
            return get_and_validate_configured_trackers(
                trackers=dynamic_trackers,
                all_trackers=False,
                api_keys_dict=api_keys_dict,
                all_trackers_list=all_trackers_list,
            )
        except AssertionError:
            logging.error(
                f"[ReUploadUtils] None of the trackers dynamic trackers {dynamic_trackers} have a valid "
                f"configuration. Proceeding with fall back trackers {original_upload_to_trackers}"
            )
        # well, no need to select trackers dynamically or no valid dynamic trackers (exception case)
        return original_upload_to_trackers

    def mark_successful_upload(self, torrent, tracker, upload_response):
        # getting the overall status of the torrent from cache
        torrent_status = self.get_torrent_status(torrent["hash"])

        # this is the first tracker for this torrent
        self._save_job_repo_entry(
            torrent["hash"], tracker, JobStatus.SUCCESS, upload_response
        )

        if (
            torrent_status == TorrentStatus.PENDING
            or torrent_status == TorrentStatus.READY_FOR_PROCESSING
        ):
            # updating the overall status of the torrent
            self.update_torrent_field(
                torrent["hash"], "status", TorrentStatus.SUCCESS, False
            )
            return TorrentStatus.SUCCESS
        elif torrent_status == TorrentStatus.FAILED:
            # updating the overall status of the torrent
            self.update_torrent_field(
                torrent["hash"],
                "status",
                TorrentStatus.PARTIALLY_SUCCESSFUL,
                False,
            )
            return TorrentStatus.PARTIALLY_SUCCESSFUL
        # here the status could be SUCCESS or PARTIALLY_SUCCESSFUL, We don't need to make any changes to this status
        # for testing purpose we just return the status from cache
        return torrent_status

    def _save_job_repo_entry(self, info_hash, tracker, status, upload_response):
        job_repo_entry = {
            "job_id": self.get_unique_id(),
            "hash": info_hash,
            "tracker": tracker,
            "status": status,
            "tracker_response": json.dumps(upload_response),
        }
        self.insert_into_job_repo(job_repo_entry)

    def mark_failed_upload(self, torrent, tracker, upload_response):
        # getting the overall status of the torrent from cache
        torrent_status = self.get_torrent_status(torrent["hash"])

        # this is the first tracker for this torrent
        self._save_job_repo_entry(
            torrent["hash"], tracker, JobStatus.FAILED, upload_response
        )

        # inserting the torrent->tracker data to job_repository
        if (
            torrent_status == TorrentStatus.PENDING
            or torrent_status == TorrentStatus.READY_FOR_PROCESSING
        ):
            # updating the overall status of the torrent
            self.update_torrent_field(
                torrent["hash"], "status", TorrentStatus.FAILED, False
            )
            return TorrentStatus.FAILED
        elif torrent_status == TorrentStatus.SUCCESS:
            # updating the overall status of the torrent
            self.update_torrent_field(
                torrent["hash"],
                "status",
                TorrentStatus.PARTIALLY_SUCCESSFUL,
                False,
            )
            return TorrentStatus.PARTIALLY_SUCCESSFUL
        # here status could be FAILED or PARTIALLY_SUCCESSFUL, we don't need to change this status
        # for testing purpose we just return the status obtained from cache
        return torrent_status

    def mark_torrent_failure(
        self, info_hash: str, status: TorrentFailureStatus
    ):
        self.update_torrent_field(info_hash, "status", status, False)
        self.update_torrent_field(
            info_hash,
            "failure_message",
            torrent_failure_messages[status],
            False,
        )
        self.client.update_torrent_category(
            info_hash=info_hash, category_name=client_labels_for_failure[status]
        )

    def update_jobs_and_torrent_status(
        self,
        info_hash: str,
        tracker_status_map: Dict[
            str, Tuple[TrackerUploadStatus, Union[Dict, Any]]
        ],
    ) -> None:
        # saving tracker status to job repo
        for trkr, response in tracker_status_map.items():
            self._save_job_repo_entry(
                info_hash, trkr, JobStatus.FAILED, response[1]
            )

        torrent_status = self.get_client_label_for_torrent(tracker_status_map)
        if torrent_status is None:
            torrent_status = TorrentStatus.SUCCESS
        self.update_torrent_field(info_hash, "status", torrent_status, False)

    @staticmethod
    def get_client_label_for_torrent(
        tracker_status_map: Dict[
            str, Tuple[TrackerUploadStatus, Union[Dict, Any]]
        ]
    ) -> Union[str, None]:
        if all(
            status[0] == TrackerUploadStatus.SUCCESS
            for trkr, status in tracker_status_map.items()
        ):
            # upload successful to all trackers
            return None  # None tells client to set source label as category

        if any(
            status[0] != TrackerUploadStatus.SUCCESS
            for trkr, status in tracker_status_map.items()
        ):
            # all uploads have failed
            return TorrentStatus.FAILED
        return TorrentStatus.PARTIALLY_SUCCESSFUL
