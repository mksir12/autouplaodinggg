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

import json
import copy
import pytest

from pathlib import Path
from pytest_mock import mocker

import modules.custom_actions.ptp_actions as ptp_actions


working_folder = Path(__file__).resolve().parent.parent.parent.parent


class APIResponse:
    ok = None
    data = None

    def __init__(self, data):
        self.ok = "True"
        self.data = data

    def json(self):
        return self.data


tracker_config = {
    "torrents_search": "https://randomsite.com/page1.php",
    "upload_form": "https://randomsite.com/page2.php",
    "dupes": {
        "technical_jargons": {
            "authentication_mode": "HEADER",
            "headers" : [ { "key": "ApiUser", "value": "API_USER" }, { "key": "ApiKey", "value": "API_KEY" } ],
            "payload_type": "MULTI-PART",
            "request_method": "GET"
        },
        "url_format": "{search_url}?imdb={imdb}",
        "strip_text": False,
        "parse_json": {
            "is_needed": True,
            "top_lvl": "Torrents",
            "torrent_name": "ReleaseName"
        }
    },
}


def test_group_already_exists_in_ptp(mocker):
    mocker.patch("os.getenv", return_value="API_KEY")
    mocker.patch("requests.get", return_value=APIResponse(json.load(open(f"{working_folder}/tests/resources/custom_action_responses/ptp_group_exists.json"))))

    tracker_settings = {}
    torrent_info = { "imdb" : "4947084", "imdb_with_tt" : "tt4947084"}
    new_tracker_config = copy.deepcopy(tracker_config)

    ptp_actions.check_for_existing_group(torrent_info, tracker_settings, new_tracker_config)
    assert new_tracker_config["upload_form"] == "https://randomsite.com/page2.php?groupid=138295"


def test_new_group_custom_action(mocker):
    mocker.patch("os.getenv", return_value="API_KEY")
    mocker.patch("requests.get", return_value=APIResponse(json.load(open(f"{working_folder}/tests/resources/custom_action_responses/ptp_new_group.json"))))

    tracker_settings = {}
    torrent_info = { "imdb" : "4947084", "imdb_with_tt" : "tt4947084"}
    new_tracker_config = copy.deepcopy(tracker_config)

    ptp_actions.check_for_existing_group(torrent_info, tracker_settings, new_tracker_config)
    assert new_tracker_config["upload_form"] == "https://randomsite.com/page2.php" # there should not be any change to upload url