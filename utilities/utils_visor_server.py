# GG Bot Upload Assistant
# Copyright (C) 2022  Noob Master669

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

import math
import json
import functools
from typing import Dict

from bson import json_util

TORRENT_DB_KEY_PREFIX = "ReUpload::Torrent"
JOB_REPO_DB_KEY_PREFIX = "ReUpload::JobRepository"


class TorrentStatus:
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    PARTIALLY_SUCCESSFUL = "PARTIALLY_SUCCESSFUL"
    TMDB_IDENTIFICATION_FAILED = "TMDB_IDENTIFICATION_FAILED"
    PENDING = "PENDING"
    UNKNOWN_FAILURE = "UNKNOWN_FAILURE"
    DUPE_CHECK_FAILED = "DUPE_CHECK_FAILED"
    READY_FOR_PROCESSING = "READY_FOR_PROCESSING"


class JobStatus:
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class Query:
    ALL_FAILED = {
        "status": {
            "$in": [
                TorrentStatus.FAILED,
                TorrentStatus.TMDB_IDENTIFICATION_FAILED,
                TorrentStatus.UNKNOWN_FAILURE,
                TorrentStatus.DUPE_CHECK_FAILED,
            ]
        }
    }
    FAILED = {"status": TorrentStatus.FAILED}
    SUCCESS = {"status": TorrentStatus.SUCCESS}
    UNKNOWN_FAILURE = {"status": TorrentStatus.UNKNOWN_FAILURE}
    DUPE_CHECK_FAILED = {"status": TorrentStatus.DUPE_CHECK_FAILED}
    PARTIALLY_SUCCESSFUL = {"status": TorrentStatus.PARTIALLY_SUCCESSFUL}
    TMDB_IDENTIFICATION_FAILED = {
        "status": TorrentStatus.TMDB_IDENTIFICATION_FAILED
    }


def serialize_json(function):
    @functools.wraps(function)
    def decorator(*args, **kwargs):
        # TODO: figure out how to handle the exceptions
        return json.loads(json_util.dumps(function(*args, **kwargs)))

    return decorator


def __count_torrents_collection(cache, filter_criteria):
    return cache.count(TORRENT_DB_KEY_PREFIX, filter_criteria)


def _get_all_data_from_torrents_collection(
    cache, page_number, sort_field, items_per_page, filter_query
):
    return _get_all_data_from_torrents_collection_as_object(
        cache, page_number, sort_field, items_per_page, filter_query
    )


@serialize_json
def _get_all_data_from_torrents_collection_as_object(
    cache, page_number, sort_field, items_per_page, filter_query
):
    return cache.advanced_get(
        TORRENT_DB_KEY_PREFIX,
        items_per_page,
        page_number,
        sort_field,
        filter_query,
    )


def __get_unique_document(cache, info_hash):
    document = cache.get(
        TORRENT_DB_KEY_PREFIX, {"hash": {"$regex": f"^{info_hash}"}}
    )
    return None if len(document) != 1 else document[0]


class VisorServerManager:
    def __init__(self, cache):
        self.cache = cache

    def _count_torrents_collection(self, filter_criteria: Dict) -> int:
        return self.cache.count(TORRENT_DB_KEY_PREFIX, filter_criteria)

    def get_torrent_statistics(self):
        return {
            "all": self._count_torrents_collection({}),
            "successful": self._count_torrents_collection(Query.SUCCESS),
            "failed": self._count_torrents_collection(Query.ALL_FAILED),
            "partial": self._count_torrents_collection(
                Query.PARTIALLY_SUCCESSFUL
            ),
        }

    def failed_torrents_statistics(self):
        return {
            "all": self._count_torrents_collection({}),
            "partial_failure": self._count_torrents_collection(
                Query.PARTIALLY_SUCCESSFUL
            ),
            "tmdb_failure": self._count_torrents_collection(
                Query.TMDB_IDENTIFICATION_FAILED
            ),
            "unknown_failure": self._count_torrents_collection(
                Query.UNKNOWN_FAILURE
            ),
            "dupe_check_failure": self._count_torrents_collection(
                Query.DUPE_CHECK_FAILED
            ),
            "upload_failure": self._count_torrents_collection(Query.FAILED),
        }

    def all_torrents(
        self,
        filter_query: dict = None,
        items_per_page: int = 20,
        page: int = 1,
        sort: str = "id",
    ):
        total_number_of_torrents = self._count_torrents_collection(filter_query)
        total_pages = math.ceil(total_number_of_torrents / items_per_page)

        return {
            "page": {
                "page_number": page,
                "total_pages": total_pages,
                "total_torrents": total_number_of_torrents,
            },
            "torrents": _get_all_data_from_torrents_collection(
                self.cache, page, sort.lower(), items_per_page, filter_query
            ),
        }

    def torrent_details(self, torrent_id):
        return _get_all_data_from_torrents_collection(
            self.cache, 1, "id", 1, {"id": torrent_id}
        )

    def get_torrent_details_object(self, torrent_id):
        return _get_all_data_from_torrents_collection_as_object(
            self.cache, 1, "id", 1, {"id": torrent_id}
        )

    def update_torrent_object(self, torrent):
        self.cache.save(TORRENT_DB_KEY_PREFIX, torrent)
