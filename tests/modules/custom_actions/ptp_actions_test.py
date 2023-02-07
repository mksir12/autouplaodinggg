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
import pickle
import pytest

from pathlib import Path
from pytest_mock import mocker

import modules.custom_actions.ptp_actions as ptp_actions

working_folder = Path(__file__).resolve().parent.parent.parent.parent
crsf_token_path = "/tests/resources/crsf_token/"


class APIResponse:
    ok = None
    data = None
    url = None

    def __init__(self, data, text=None, url=None):
        self.ok = "True"
        self.data = data
        self.text = text
        self.url = url

    def json(self):
        return self.data


tracker_config = {
    "torrents_search": "https://randomsite.com/page1.php",
    "upload_form": "https://randomsite.com/page2.php",
    "dupes": {
        "technical_jargons": {
            "authentication_mode": "HEADER",
            "headers": [
                {"key": "ApiUser", "value": "API_USER"},
                {"key": "ApiKey", "value": "API_KEY"},
            ],
            "payload_type": "MULTI-PART",
            "request_method": "GET",
        },
        "url_format": "{search_url}?imdb={imdb}",
        "strip_text": False,
        "parse_json": {
            "is_needed": True,
            "top_lvl": "Torrents",
            "torrent_name": "ReleaseName",
        },
    },
}


def test_group_already_exists_in_ptp(mocker):
    mocker.patch("os.getenv", return_value="API_KEY")
    mocker.patch(
        "requests.get",
        return_value=APIResponse(
            json.load(
                open(
                    f"{working_folder}/tests/resources/custom_action_responses/ptp_group_exists.json"
                )
            )
        ),
    )

    tracker_settings = {}
    torrent_info = {"imdb": "1630029", "imdb_with_tt": "tt1630029"}
    new_tracker_config = copy.deepcopy(tracker_config)

    ptp_actions.check_for_existing_group(
        torrent_info, tracker_settings, new_tracker_config
    )
    assert (
        new_tracker_config["upload_form"]
        == "https://randomsite.com/page2.php?groupid=276009"
    )
    assert "groupid" in tracker_settings
    assert tracker_settings["groupid"] == "276009"


def test_new_group_custom_action_no_poster(mocker):
    metadata = json.load(
        open(
            f"{working_folder}/tests/resources/custom_action_responses/ptp_new_group_no_poster.json"
        )
    )
    mocker.patch("os.getenv", return_value="API_KEY")
    mocker.patch("requests.get", return_value=APIResponse(metadata))
    metadata = metadata[0]
    # this art will be loaded from tmdb_metadata
    metadata[
        "art"
    ] = "https://m.media-amazon.com/images/M/MV5BMWFmYmRiYzMtMTQ4YS00NjA5LTliYTgtMmM3OTc4OGY3MTFkXkEyXkFqcGdeQXVyODk4OTc3MTY@._V1_.jpg"

    tracker_settings = {}
    torrent_info = {
        "title": None,
        "year": None,
        "imdb": "4947084",
        "imdb_with_tt": "tt4947084",
        "tmdb_metadata": {
            "poster": "https://m.media-amazon.com/images/M/MV5BMWFmYmRiYzMtMTQ4YS00NjA5LTliYTgtMmM3OTc4OGY3MTFkXkEyXkFqcGdeQXVyODk4OTc3MTY@._V1_.jpg"
        },
    }
    new_tracker_config = copy.deepcopy(tracker_config)

    ptp_actions.check_for_existing_group(
        torrent_info, tracker_settings, new_tracker_config
    )
    assert (
        new_tracker_config["upload_form"] == "https://randomsite.com/page2.php"
    )  # there should not be any change to upload url
    assert "groupid" not in tracker_settings
    assert tracker_settings["title"] == metadata["title"]
    assert tracker_settings["year"] == metadata["year"]
    assert tracker_settings["image"] == metadata["art"]
    assert tracker_settings["tags"] == metadata["tags"]
    assert tracker_settings["album_desc"] == metadata["plot"]
    assert tracker_settings["trailer"] == ""


def test_new_group_custom_action(mocker):
    metadata = json.load(
        open(
            f"{working_folder}/tests/resources/custom_action_responses/ptp_new_group.json"
        )
    )
    mocker.patch("os.getenv", return_value="API_KEY")
    mocker.patch("requests.get", return_value=APIResponse(metadata))
    metadata = metadata[0]

    tracker_settings = {}
    torrent_info = {
        "title": None,
        "year": None,
        "imdb": "4947084",
        "imdb_with_tt": "tt4947084",
    }
    new_tracker_config = copy.deepcopy(tracker_config)

    ptp_actions.check_for_existing_group(
        torrent_info, tracker_settings, new_tracker_config
    )
    assert (
        new_tracker_config["upload_form"] == "https://randomsite.com/page2.php"
    )  # there should not be any change to upload url
    assert "groupid" not in tracker_settings
    assert tracker_settings["title"] == metadata["title"]
    assert tracker_settings["year"] == metadata["year"]
    assert tracker_settings["image"] == metadata["art"]
    assert tracker_settings["tags"] == metadata["tags"]
    assert tracker_settings["album_desc"] == metadata["plot"]
    assert tracker_settings["trailer"] == ""


@pytest.mark.parametrize(
    ("torrent_info", "tracker_settings", "expected"),
    [
        pytest.param(
            {"scene": "true"},
            {"scene": "1"},
            {"scene": "on"},
            id="scene_release",
        ),
        pytest.param(
            {"scene": "false"}, {"scene": "0"}, {}, id="not_scene_release"
        ),
        pytest.param(
            {},
            {"scene": "1"},
            {},
            id="no_scene_in_torrent_info_present_in_tracker_settings",
        ),
        pytest.param(
            {}, {}, {}, id="no_scene_in_torrent_info_not_in_tracker_settings"
        ),
    ],
)
def test_mark_scene_release_if_applicable(
    torrent_info, tracker_settings, expected
):
    ptp_actions.mark_scene_release_if_applicable(
        torrent_info, tracker_settings, None
    )
    assert tracker_settings == expected


@pytest.mark.parametrize(
    ("tracker_settings", "expected"),
    [
        pytest.param(
            {"resolution": "1080p"},
            {"resolution": "1080p"},
            id="proper_resolution",
        ),
        pytest.param({"resolution": "Other"}, {}, id="other_resolution"),
    ],
)
def test_fix_other_resolution(tracker_settings, expected):
    ptp_actions.fix_other_resolution(None, tracker_settings, None)
    assert tracker_settings == expected


@pytest.mark.parametrize(
    ("torrent_info", "tracker_settings", "expected"),
    [
        pytest.param(
            {"subtitles": []},
            {},
            {"subtitles[]": [44]},
            id="no_subtitle_present",
        ),
        pytest.param(
            {"subtitles": []},
            {"resolution": "Other"},
            {"resolution": "Other", "subtitles[]": [44]},
            id="no_subtitle_present_retaining_tracker_settings",
        ),
        pytest.param(
            {
                "subtitles": [
                    {"language_code": "swe", "title": "Swedish"},
                    {"language_code": "is"},
                    {"language_code": "cze", "title": "Czech"},
                ]
            },
            {"resolution": "Other"},
            {"resolution": "Other", "subtitles[]": [11, 28, 30]},
            id="some_subs_present",
        ),
    ],
)
def test_add_subtitle_information(torrent_info, tracker_settings, expected):
    ptp_actions.add_subtitle_information(torrent_info, tracker_settings, None)
    assert tracker_settings == expected


def _clean_up(pth):
    pth = Path(pth)
    for child in pth.iterdir():
        if child.is_file():
            child.unlink()
        else:
            _clean_up(child)
    pth.rmdir()


@pytest.fixture(scope="function")
def create_cookie_dirs():
    folder = f"{working_folder}{crsf_token_path}cookies/"

    if Path(folder).is_dir():
        _clean_up(folder)

    Path(folder).mkdir(parents=True, exist_ok=True)
    yield
    _clean_up(folder)


def __ptp_crsf_token_side_effect(key, default=None):
    if key == "PTP_2FA_ENABLED":
        return True
    elif key == "PTP_ANNOUNCE_URL":
        return "http://please.passthepopcorn.me:2710/possiblyavalidtrackerpasskey/announce"
    else:
        return default


@pytest.mark.usefixtures("create_cookie_dirs")
def test_get_crsf_token_successful_login(mocker):
    tracker_settings = {}
    torrent_info = {"cookies_dump": f"{working_folder}{crsf_token_path}"}

    mocker.patch("os.getenv", side_effect=__ptp_crsf_token_side_effect)
    mocker.patch(
        "requests.Session.post",
        return_value=APIResponse(
            json.load(
                open(
                    f"{working_folder}/tests/resources/custom_action_responses/ptp_login_success.json"
                )
            )
        ),
    )

    ptp_actions.get_crsf_token(torrent_info, tracker_settings, {})
    assert tracker_settings["AntiCsrfToken"] == "ObviouslyTheRealCsrfToken"


@pytest.mark.usefixtures("create_cookie_dirs")
def test_get_crsf_token_failed_login(mocker):
    torrent_info = {"cookies_dump": f"{working_folder}{crsf_token_path}"}

    mocker.patch("os.getenv", side_effect=__ptp_crsf_token_side_effect)
    mocker.patch(
        "requests.Session.post",
        return_value=APIResponse(
            json.load(
                open(
                    f"{working_folder}/tests/resources/custom_action_responses/ptp_login_failed.json"
                )
            )
        ),
    )
    with pytest.raises(Exception) as ex:
        ptp_actions.get_crsf_token(torrent_info, {}, {})
        assert (
            ex.message
            == "Failed to login to PTP. Bad 'username' / 'password' / '2fa_key' provided."
        )


@pytest.mark.usefixtures("create_cookie_dirs")
def test_get_crsf_token_cached_cookie(mocker):
    tracker_settings = {}
    torrent_info = {"cookies_dump": f"{working_folder}{crsf_token_path}"}
    tracker_config = {"upload_form": "https://passthepopcorn.me/upload.php"}
    cookiefile = f"{torrent_info['cookies_dump']}cookies/cookie.dat"

    # creating a dummy pickle file
    pickle.dump(torrent_info, open(cookiefile, "wb"))

    mocker.patch("os.getenv", side_effect=__ptp_crsf_token_side_effect)
    mocker.patch(
        "requests.Session.get",
        return_value=APIResponse(
            None, text='data-AntiCsrfToken="ObviouslyTheRealCsrfToken"'
        ),
    )

    ptp_actions.get_crsf_token(torrent_info, tracker_settings, tracker_config)
    assert tracker_settings["AntiCsrfToken"] == "ObviouslyTheRealCsrfToken"


@pytest.mark.usefixtures("create_cookie_dirs")
def test_get_crsf_token_cached_cookie_failure(mocker):
    tracker_settings = {}
    torrent_info = {"cookies_dump": f"{working_folder}{crsf_token_path}"}
    tracker_config = {"upload_form": "https://passthepopcorn.me/upload.php"}
    cookiefile = f"{torrent_info['cookies_dump']}cookies/cookie.dat"

    # creating a dummy pickle file
    pickle.dump(torrent_info, open(cookiefile, "wb"))

    mocker.patch("os.getenv", side_effect=__ptp_crsf_token_side_effect)
    mocker.patch(
        "requests.Session.get",
        return_value=APIResponse(
            None,
            text="Dear, Hacker! Do you really have nothing better do than this?",
        ),
    )
    mocker.patch(
        "requests.Session.post",
        return_value=APIResponse(
            json.load(
                open(
                    f"{working_folder}/tests/resources/custom_action_responses/ptp_login_success.json"
                )
            )
        ),
    )

    ptp_actions.get_crsf_token(torrent_info, tracker_settings, tracker_config)
    assert tracker_settings["AntiCsrfToken"] == "ObviouslyTheRealCsrfToken"


@pytest.mark.parametrize(
    ("imdb_tags", "tmdb_tags", "expected"),
    [
        pytest.param(
            ["action", "comedy", "drama"],
            ["comedy", "action"],
            ["action", "comedy", "drama"],
            id="ptp_tags",
        ),
        pytest.param(
            ["action", "drama"],
            ["comedy"],
            ["action", "comedy", "drama"],
            id="ptp_tags",
        ),
        pytest.param(
            ["scifi", "drama"], [], ["drama", "sci.fi"], id="ptp_tags"
        ),
        pytest.param(
            [], ["scifi", "drama"], ["drama", "sci.fi"], id="ptp_tags"
        ),
        pytest.param([], [], [], id="ptp_tags"),
    ],
)
def test_get_tags(imdb_tags, tmdb_tags, expected):
    assert ptp_actions._get_tags(imdb_tags, tmdb_tags) == expected


@pytest.mark.parametrize(
    ("response", "expected"),
    [
        pytest.param(
            APIResponse(
                None,
                text=None,
                url="https://passthepopcorn.me/torrents.php?id=1234567&torrentid=7654321",
            ),
            (True, "Successfully Uploaded to PTP"),
            id="ptp_successful_upload",
        ),
        pytest.param(
            APIResponse(
                None,
                text='ANNOUNCE_URL<div class="alert-bar"><a class="alert-bar__link" href="user.php?action=sessions">This is the error message displayed to the user</a></div>',
                url=None,
            ),
            (False, "This is the error message displayed to the user"),
            id="ptp_failed_upload",
        ),
        pytest.param(
            APIResponse(
                None,
                text='ANNOUNCE_URL<div class="alert alert--error alert--centered-content"><div>This is another type of error</div></div>',
                url=None,
            ),
            (False, "This is another type of error"),
            id="ptp_failed_upload_2",
        ),
    ],
)
def test_check_successful_upload(response, expected, mocker):
    mocker.patch("os.getenv", return_value="ANNOUNCE_URL")
    assert ptp_actions.check_successful_upload(response) == expected


@pytest.mark.parametrize(
    ("torrent_info", "expected"),
    [
        pytest.param(
            {
                "tmdb_metadata": {"keywords": ["concert"]},
                "content_type": "movie",
                "duration": "4200000",  # 70min * 60000
                "imdb": "",
            },
            "Concert",
            id="long_duration_concert",
        ),
        pytest.param(
            {
                "tmdb_metadata": {"keywords": ["comedy", "stand-up-comedy"]},
                "content_type": "movie",
                "duration": "4200000",  # 70min * 60000
                "imdb": "",
            },
            "Stand-up Comedy",
            id="standup_comedy",
        ),
        pytest.param(
            {
                "tmdb_metadata": {"keywords": ["short"]},
                "content_type": "movie",
                "duration": "4200000",  # 70min * 60000
                "imdb": "",
            },
            "Short Film",
            id="short_film",
        ),
        pytest.param(
            {
                "tmdb_metadata": {
                    "keywords": ["short", "miniseries", "short-film"]
                },
                "content_type": "movie",
                "duration": "4200000",  # 70min * 60000
                "imdb": "",
            },
            "Short Film",
            id="mini_series_short_film",
        ),
        pytest.param(
            {
                "tmdb_metadata": {"keywords": ["miniseries"]},
                "content_type": "movie",
                "duration": "4200000",  # 70min * 60000
                "imdb": "",
            },
            "Miniseries",
            id="mini_series",
        ),
        pytest.param(
            {
                "tmdb_metadata": {"keywords": []},
                "content_type": "movie",
                "duration": "4200000",  # 70min * 60000
                "imdb": "",
            },
            "Feature Film",
            id="feature_film",
        ),
        pytest.param(
            {
                "tmdb_metadata": {"keywords": []},
                "content_type": "movie",
                "duration": "1200000",  # 20min * 60000
                "imdb": "",
            },
            "Short Film",
            id="short_film_by_duration",
        ),
        pytest.param(
            {
                "tmdb_metadata": {"keywords": []},
                "content_type": "movie",
                "duration": "1200000",  # 20min * 60000
                "imdb": "0020530",
            },
            "Short Film",
            id="short_film_by_imdb",
        ),
        pytest.param(
            {
                "tmdb_metadata": {"keywords": []},
                "content_type": "movie",
                "duration": "4200000",  # 20min * 60000
                "imdb": "0499549",
            },
            "Feature Film",
            id="feature_film_by_imdb",
        ),
    ],
)
def test_get_ptp_type_for_movie(torrent_info, expected):
    tracker_settings = {}
    ptp_actions.get_ptp_type(torrent_info, tracker_settings, {})
    assert "type" in tracker_settings
    assert tracker_settings["type"] == expected


def test_get_ptp_type_from_user(mocker):
    tracker_settings = {}
    torrent_info = {
        "tmdb_metadata": {"keywords": []},
        "content_type": "tv",
        "duration": "1200000",  # 20min * 60000
        "imdb": "",
    }
    mocker.patch("rich.prompt.Prompt.ask", return_value="Miniseries")
    ptp_actions.get_ptp_type(torrent_info, tracker_settings, {})
    assert "type" in tracker_settings
    assert tracker_settings["type"] == "Miniseries"
