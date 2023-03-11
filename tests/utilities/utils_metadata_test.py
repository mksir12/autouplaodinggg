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
import pytest

from pathlib import Path
import utilities.utils_metadata as metadata


working_folder = Path(__file__).resolve().parent.parent.parent


class TMDBResponse:
    ok = None
    data = None

    def __init__(self, data):
        self.ok = "True"
        self.data = data

    def json(self):
        return self.data


def test_tmdb_movie_auto_select(mocker, monkeypatch):
    query_title = "Gods of Egypt"
    query_year = "2016"
    content_type = "movie"

    tmdb_response = TMDBResponse(
        json.load(
            open(
                f"{working_folder}/tests/resources/tmdb/results/Gods of Egypt.json"
            )
        )
    )
    tmdb_external_response = TMDBResponse(
        json.load(
            open(
                f"{working_folder}/tests/resources/tmdb/results/Gods of Egypt_external.json"
            )
        )
    )
    tmdb_responses = iter([tmdb_response, tmdb_external_response])
    monkeypatch.setattr("requests.get", lambda url: next(tmdb_responses))

    assert metadata._metadata_search_tmdb_for_id(
        query_title, query_year, content_type, False
    ) == json.load(
        open(
            f"{working_folder}/tests/resources/tmdb/expected/Gods of Egypt.json"
        )
    )


def test_tmdb_movie_loose_search(mocker, monkeypatch):
    query_title = "Kung Fu Panda 1"
    query_year = "2008"
    content_type = "movie"

    tmdb_response_strict = TMDBResponse(
        json.load(
            open(
                f"{working_folder}/tests/resources/tmdb/results/Kung Fu Panda 1_strict.json"
            )
        )
    )
    tmdb_response_loose = TMDBResponse(
        json.load(
            open(
                f"{working_folder}/tests/resources/tmdb/results/Kung Fu Panda 1.json"
            )
        )
    )
    tmdb_responses = iter([tmdb_response_strict, tmdb_response_loose])
    monkeypatch.setattr("requests.get", lambda url: next(tmdb_responses))
    mocker.patch("os.getenv", return_value=1)

    assert metadata._metadata_search_tmdb_for_id(
        query_title, query_year, content_type, False
    ) == json.load(
        open(
            f"{working_folder}/tests/resources/tmdb/expected/Kung Fu Panda 1.json"
        )
    )


def test_tmdb_movie_cannot_auto_select(mocker, monkeypatch):
    query_title = "Uncharted"
    query_year = "2022"
    content_type = "movie"

    tmdb_response = TMDBResponse(
        json.load(
            open(
                f"{working_folder}/tests/resources/tmdb/results/Uncharted.json"
            )
        )
    )
    tmdb_response_external = TMDBResponse(
        json.load(
            open(
                f"{working_folder}/tests/resources/tmdb/results/Uncharted_external.json"
            )
        )
    )
    tmdb_responses = iter([tmdb_response, tmdb_response_external])

    monkeypatch.setattr("requests.get", lambda url: next(tmdb_responses))
    mocker.patch("rich.prompt.Prompt.ask", return_value="1")
    assert metadata._metadata_search_tmdb_for_id(
        query_title, query_year, content_type, False
    ) == json.load(
        open(f"{working_folder}/tests/resources/tmdb/expected/Uncharted.json")
    )


def test_tmdb_tv_auto_select(mocker, monkeypatch):
    query_title = "Bosch Legacy"
    query_year = ""
    content_type = "episode"

    tmdb_response = TMDBResponse(
        json.load(
            open(
                f"{working_folder}/tests/resources/tmdb/results/Bosch Legacy.json"
            )
        )
    )
    tmdb_response_external = TMDBResponse(
        json.load(
            open(
                f"{working_folder}/tests/resources/tmdb/results/Bosch Legacy_external.json"
            )
        )
    )
    tvmaze_search_by_imdb = TMDBResponse(
        json.load(
            open(
                f"{working_folder}/tests/resources/tmdb/results/Bosch Legacy_tvmaze_imdb.json"
            )
        )
    )
    tmdb_responses = iter(
        [tmdb_response, tmdb_response_external, tvmaze_search_by_imdb]
    )
    monkeypatch.setattr("requests.get", lambda url: next(tmdb_responses))

    assert metadata._metadata_search_tmdb_for_id(
        query_title, query_year, content_type, False
    ) == json.load(
        open(
            f"{working_folder}/tests/resources/tmdb/expected/Bosch Legacy.json"
        )
    )


def __auto_reuploader(key, default=None):
    if key == "tmdb_result_auto_select_threshold":
        return 1
    return default


def __upload_assistant(key, default=None):
    return default


def __auto_reuploader_loosely_configured(key, default=None):
    if key == "tmdb_result_auto_select_threshold":
        return 10
    return default


def test_tmdb_movie_no_results(mocker, monkeypatch):
    query_title = "Kung Fu Panda 1"
    query_year = "2008"
    content_type = "movie"

    tmdb_response_strict = TMDBResponse(
        json.load(
            open(
                f"{working_folder}/tests/resources/tmdb/results/Kung Fu Panda 1_strict.json"
            )
        )
    )
    tmdb_responses = iter([tmdb_response_strict, tmdb_response_strict])
    monkeypatch.setattr("requests.get", lambda url: next(tmdb_responses))

    mocker.patch("os.getenv", side_effect=__auto_reuploader)

    expected = {
        "tmdb": "0",
        "imdb": "0",
        "tvmaze": "0",
        "tvdb": "0",
        "possible_matches": None,
    }

    assert (
        metadata._metadata_search_tmdb_for_id(
            query_title, query_year, content_type, False
        )
        == expected
    )


def test_tmdb_movie_loosely_configured_reuploader(mocker, monkeypatch):
    query_title = "Kung Fu Panda 1"
    query_year = "2008"
    content_type = "movie"

    tmdb_response_strict = TMDBResponse(
        json.load(
            open(
                f"{working_folder}/tests/resources/tmdb/results/Kung Fu Panda 1_strict.json"
            )
        )
    )
    tmdb_response_loose = TMDBResponse(
        json.load(
            open(
                f"{working_folder}/tests/resources/tmdb/results/Kung Fu Panda 1.json"
            )
        )
    )
    tmdb_response_external = TMDBResponse(
        json.load(
            open(
                f"{working_folder}/tests/resources/tmdb/results/Kung Fu Panda 1_external.json"
            )
        )
    )
    tmdb_responses = iter(
        [tmdb_response_strict, tmdb_response_loose, tmdb_response_external]
    )
    monkeypatch.setattr("requests.get", lambda url: next(tmdb_responses))
    mocker.patch("os.getenv", side_effect=__auto_reuploader_loosely_configured)

    assert metadata._metadata_search_tmdb_for_id(
        query_title, query_year, content_type, False
    ) == json.load(
        open(
            f"{working_folder}/tests/resources/tmdb/expected/Kung Fu Panda 1_loose_reuploader.json"
        )
    )


def test_tmdb_movie_no_results_exit(mocker, monkeypatch):
    query_title = "Kung Fu Panda 1"
    query_year = "2008"
    content_type = "movie"

    tmdb_response_strict = TMDBResponse(
        json.load(
            open(
                f"{working_folder}/tests/resources/tmdb/results/Kung Fu Panda 1_strict.json"
            )
        )
    )
    tmdb_responses = iter([tmdb_response_strict, tmdb_response_strict])
    monkeypatch.setattr("requests.get", lambda url: next(tmdb_responses))

    mocker.patch("os.getenv", side_effect=__upload_assistant)

    with pytest.raises(SystemExit) as pytest_wrapped_e:
        metadata._metadata_search_tmdb_for_id(
            query_title, query_year, content_type, False
        )
    assert pytest_wrapped_e.type == SystemExit
    assert (
        pytest_wrapped_e.value.code
        == "No results found on TMDB, try running this script again but manually supply the TMDB or IMDB ID"
    )


@pytest.mark.parametrize(
    (
        "id_site",
        "id_value",
        "external_site",
        "content_type",
        "mock_response_file",
        "expected",
    ),
    [
        # IMDB Available
        pytest.param(
            "imdb",  # id_site
            "123456",  # id_value
            "tmdb",  # external_site
            "movie",  # content_type
            "imdb_available_need_tmdb_for_movie",  # mock_response_file
            "557",  # expected
            id="imdb_available_need_tmdb_for_movie",
        ),
        pytest.param(
            "imdb",  # id_site
            "123456",  # id_value
            "tmdb",  # external_site
            "episode",  # content_type
            "imdb_available_need_tmdb_for_episode",  # mock_response_file
            "1418",  # expected
            id="imdb_available_need_tmdb_for_episode",
        ),
        pytest.param(
            "imdb",  # id_site
            "123456",  # id_value
            "tvmaze",  # external_site
            "episode",  # content_type
            "imdb_available_need_tvmaze_for_episode",  # mock_response_file
            "66",  # expected
            id="imdb_available_need_tvmaze_for_episode",
        ),
        pytest.param(
            "imdb",  # id_site
            "123456",  # id_value
            "tvmaze",  # external_site
            "movie",  # content_type
            "imdb_available_need_tvmaze_for_movie",  # mock_response_file
            "0",  # expected
            id="imdb_available_need_tvmaze_for_movie",  # will be called only if content_type is episode
        ),
        # TMDB Available
        pytest.param(
            "tmdb",  # id_site
            "123456",  # id_value
            "tvmaze",  # external_site
            "movie",  # content_type
            "tmdb_available_need_tvmaze_for_movie",  # mock_response_file
            "0",  # expected
            id="tmdb_available_need_tvmaze_for_movie",  # tvmaze can be obtained only using imdb id
        ),
        pytest.param(
            "tmdb",  # id_site
            "123456",  # id_value
            "tvmaze",  # external_site
            "episode",  # content_type
            "tmdb_available_need_tvmaze_for_episode",  # mock_response_file
            "0",  # expected
            id="tmdb_available_need_tvmaze_for_episode",  # tvmaze can be obtained only using imdb id
        ),
    ],
)
def test_metadata_get_external_id(
    id_site,
    id_value,
    external_site,
    content_type,
    mock_response_file,
    expected,
    mocker,
):
    mock_response_file_data = TMDBResponse(
        json.load(
            open(
                f"{working_folder}/tests/resources/tmdb/results/external_id_search/{mock_response_file}.json"
            )
        )
    )
    mocker.patch("requests.get", return_value=mock_response_file_data)

    assert (
        metadata._get_external_id(
            id_site, id_value, external_site, content_type
        )
        == expected
    )


def __api_return_values(url, **kwargs):
    print(url.url)

    if (
        url.url
        == "https://api.themoviedb.org/3/search/tv?api_key=DUMMY_API_KEY&query='Peaky%20Blinders'&page=1&include_adult=false&year=2022"
    ):
        # TMDB SEARCH
        # episode_all_ids_missing
        return TMDBResponse(
            json.load(
                open(
                    f"{working_folder}/tests/resources/tmdb/results/full_id_search/episode_all_ids_missing/tmdb_search.json"
                )
            )
        )
    if (
        url.url
        == "https://api.themoviedb.org/3/tv/60574/external_ids?api_key=DUMMY_API_KEY&language=en-US"
    ):
        # TMDB => IMDB
        # episode_all_ids_missing
        # episode_tmdb_is_present
        return TMDBResponse(
            json.load(
                open(
                    f"{working_folder}/tests/resources/tmdb/results/full_id_search/episode_all_ids_missing/tmdb_to_imdb.json"
                )
            )
        )
    if url.url == "https://api.tvmaze.com/lookup/shows?imdb=tt2442560":
        # IMDB => TVMAZE
        # episode_imdb_is_present
        # episode_all_ids_missing
        # episode_tmdb_is_present
        return TMDBResponse(
            json.load(
                open(
                    f"{working_folder}/tests/resources/tmdb/results/full_id_search/episode_all_ids_missing/imdb_to_tvmaze.json"
                )
            )
        )

    if (
        url.url
        == "https://api.themoviedb.org/3/find/tt2442560?api_key=DUMMY_API_KEY&language=en-US&external_source=imdb_id"
    ):
        # IMDB => TMDB
        # episode_imdb_is_present
        # episode_tvmaze_is_present
        return TMDBResponse(
            json.load(
                open(
                    f"{working_folder}/tests/resources/tmdb/results/full_id_search/episode_imdb_is_present/imdb_to_tmdb.json"
                )
            )
        )

    if url.url == "https://api.tvmaze.com/shows/269":
        # TVMAZE => IMDB
        # episode_tvmaze_is_present
        return TMDBResponse(
            json.load(
                open(
                    f"{working_folder}/tests/resources/tmdb/results/full_id_search/episode_tvmaze_is_present/tvmaze_to_imdb.json"
                )
            )
        )

    return TMDBResponse(
        json.load(
            open(
                f"{working_folder}/tests/resources/tmdb/results/full_id_search/XXXXXX/imdb_available_need_tmdb_for_episode.json"
            )
        )
    )


def __env_auto_uploader(param, default=None):
    if param == "TMDB_API_KEY":
        return "DUMMY_API_KEY"
    if param == "tmdb_result_auto_select_threshold":
        return 5
    return None


@pytest.mark.parametrize(
    (
        "torrent_info",
        "tmdb_id",
        "imdb_id",
        "tvmaze_id",
        "auto_mode",
        "expected",
    ),
    [
        pytest.param(
            {"type": "episode"},
            "123123",
            "tt7654323",
            "12342",
            False,
            {
                "imdb": "tt7654323",
                "tmdb": "123123",
                "tvmaze": "12342",
                "possible_match": None,
            },
            id="episode_all_ids_available",
        ),
        pytest.param(
            {"type": "episode"},
            ["123123"],
            ["tt7654323"],
            ["12342"],
            False,
            {
                "imdb": "tt7654323",
                "tmdb": "123123",
                "tvmaze": "12342",
                "possible_match": None,
            },
            id="episode_all_ids_available",
        ),
        pytest.param(
            {"type": "episode"},
            "123123",
            "7654323",
            "12342",
            False,
            {
                "imdb": "tt7654323",
                "tmdb": "123123",
                "tvmaze": "12342",
                "possible_match": None,
            },
            id="episode_all_ids_available_adding_tt",
        ),
        pytest.param(
            {"type": "episode", "title": "Peaky Blinders", "year": "2022"},
            "",
            "",
            "",
            False,
            {
                "imdb": "tt2442560",
                "tmdb": "60574",
                "tvmaze": "269",
                "possible_match": f"{working_folder}/tests/resources/tmdb/results/full_id_search/episode_all_ids_missing/possible_match.json",
            },
            id="episode_all_ids_missing",
        ),
        pytest.param(
            {"type": "episode", "title": "Peaky Blinders", "year": "2022"},
            "",
            "tt2442560",
            "",
            False,
            {
                "imdb": "tt2442560",
                "tmdb": "60574",
                "tvmaze": "269",
                "possible_match": None,
            },
            id="episode_imdb_is_present",
        ),
        pytest.param(
            {"type": "episode", "title": "Peaky Blinders", "year": "2022"},
            "60574",
            "",
            "",
            False,
            {
                "imdb": "tt2442560",
                "tmdb": "60574",
                "tvmaze": "269",
                "possible_match": None,
            },
            id="episode_tmdb_is_present",
        ),
        pytest.param(
            {"type": "episode", "title": "Peaky Blinders", "year": "2022"},
            "",
            "",
            "269",
            False,
            {
                "imdb": "tt2442560",
                "tmdb": "60574",
                "tvmaze": "269",
                "possible_match": None,
            },
            id="episode_tvmaze_is_present",
        ),
    ],
)
def test_fill_database_ids(
    torrent_info, tmdb_id, imdb_id, tvmaze_id, auto_mode, expected, mocker
):
    # this mocker is so that, we can run out whole code, and we intercept http call from inside requests package.
    mocker.patch(
        "requests.sessions.Session.send", side_effect=__api_return_values
    )
    mocker.patch("os.getenv", side_effect=__env_auto_uploader)

    possible_match = metadata.fill_database_ids(
        torrent_info, tmdb_id, imdb_id, tvmaze_id, auto_mode
    )
    print(torrent_info)
    print(expected)
    print(possible_match)
    assert torrent_info["imdb"] == expected["imdb"]
    assert torrent_info["tmdb"] == expected["tmdb"]
    assert torrent_info["tvmaze"] == expected["tvmaze"]
    if expected["possible_match"] is None:
        assert possible_match == expected["possible_match"]
    else:
        assert possible_match == json.load(open(expected["possible_match"]))


@pytest.mark.parametrize(
    ("imdbId", "expected"),
    [
        pytest.param(
            "tt0110413",
            {"imdb": "tt0110413", "tmdb": "101", "tvdb": "0"},
            id="imdbId_external_for_movie",
        ),
        pytest.param(
            "tt0168366",
            {"imdb": "tt0168366", "tmdb": "60572", "tvdb": "76703"},
            id="imdbId_external_for_tv",
        ),
        pytest.param(
            "tt12851524",
            {"imdb": "tt12851524", "tmdb": "0", "tvdb": "399959"},
            id="imdbId_external_for_tv_no_tmdb",
        ),
        pytest.param(
            "tt10857160",
            {"imdb": "tt10857160", "tmdb": "92783", "tvdb": "0"},
            id="imdbId_external_for_tv_no_tvdb",
        ),
        pytest.param("tt128515242", None, id="imdbId_external_invalid_imdb_id"),
    ],
)
def test_get_external_ids_from_imdb(imdbId, expected, mocker):
    mocker.patch("os.getenv", return_value=imdbId)
    mock_response_file_data = TMDBResponse(
        json.load(
            open(
                f"{working_folder}/tests/resources/imdb_external_ids/{imdbId}.json"
            )
        )
    )
    mocker.patch("requests.get", return_value=mock_response_file_data)

    assert expected == metadata._get_external_ids_from_imdb(imdbId)


def test_get_external_ids_from_imdb_no_api_key():
    assert None == metadata._get_external_ids_from_imdb("imdbId")


@pytest.mark.parametrize(
    ("content_type", "tmdb_id", "expected"),
    [
        pytest.param(
            "movie",
            "634649",
            {"imdb": "tt10872600", "tmdb": "634649", "tvdb": "0"},
            id="tmdb_external_for_movie",
        ),
        pytest.param(
            "episode",
            "76479",
            {"imdb": "tt1190634", "tmdb": "76479", "tvdb": "355567"},
            id="tmdb_external_for_tv",
        ),
        pytest.param(
            "episode",
            "60625",
            {"imdb": "0", "tmdb": "60625", "tvdb": "275274"},
            id="tmdb_external_for_tv_no_imdb",
        ),
        pytest.param(
            "movie",
            "453395",
            {"imdb": "tt9419884", "tmdb": "453395", "tvdb": "0"},
            id="tmdb_external_for_tv_no_tvdb",
        ),
        pytest.param(
            "episode",
            "invalid",
            None,
            id="tmdb_external_for_tv_invalid_tmdb_id",
        ),
    ],
)
def test_get_external_ids_from_tmdb(content_type, tmdb_id, expected, mocker):
    mocker.patch("os.getenv", return_value=tmdb_id)
    mock_response_file_data = TMDBResponse(
        json.load(
            open(
                f"{working_folder}/tests/resources/tmdb_external_ids/{content_type}/{tmdb_id}.json"
            )
        )
    )
    mocker.patch("requests.get", return_value=mock_response_file_data)

    assert expected == metadata._get_external_ids_from_tmdb(
        content_type, tmdb_id
    )


@pytest.mark.parametrize(
    ("tvmaze", "expected"),
    [
        pytest.param(
            "34650",
            {"imdb": "tt7772602", "tvdb": "347645", "tvmaze": "34650"},
            id="tvmaze_external_for_tv",
        ),
        pytest.param(
            "100",
            {"imdb": "tt1595859", "tvdb": "0", "tvmaze": "100"},
            id="tvmaze_external_for_tv_no_tvdb",
        ),
        pytest.param(
            "101",
            {"imdb": "0", "tvdb": "95451", "tvmaze": "101"},
            id="tvmaze_external_for_tv_no_imdb",
        ),
    ],
)
def test_get_external_ids_from_tvmaze(tvmaze, expected, mocker):
    mock_response_file_data = TMDBResponse(
        json.load(
            open(
                f"{working_folder}/tests/resources/tvmaze_external_ids/{tvmaze}.json"
            )
        )
    )
    mocker.patch("requests.get", return_value=mock_response_file_data)

    assert expected == metadata._get_external_ids_from_tvmaze(tvmaze)


def test_get_external_ids_from_tvmaze_invalid(mocker):
    mock_response_file_data = TMDBResponse(
        json.load(
            open(
                f"{working_folder}/tests/resources/tvmaze_external_ids/invalid.json"
            )
        )
    )
    mocker.patch("requests.get", return_value=mock_response_file_data)

    assert None == metadata._get_external_ids_from_tvmaze("invalid")


def test_user_gave_imdb_for_movie(mocker, monkeypatch):
    auto_mode = False
    torrent_info = {"type": "movie"}
    tmdb_id = None
    imdb_id = "tt10648342"
    tvmaze_id = None
    tvdb_id = None
    expected_ids = {
        "imdb": "tt10648342",
        "tmdb": "616037",
        "tvmaze": "0",
        "tvdb": "0",
    }

    mocker.patch("os.getenv", return_value="IMDB_API_KEY")

    imdb_external_response = TMDBResponse(
        json.load(
            open(
                f"{working_folder}/tests/resources/user_provided_metadata_arguments/{torrent_info['type']}/user_provided_imdb/imdb_external.json"
            )
        )
    )
    tmdb_external_response = TMDBResponse(
        json.load(
            open(
                f"{working_folder}/tests/resources/user_provided_metadata_arguments/{torrent_info['type']}/user_provided_imdb/tmdb_external.json"
            )
        )
    )
    api_responses = iter([imdb_external_response, tmdb_external_response])

    monkeypatch.setattr("requests.get", lambda url: next(api_responses))

    possible_matches = metadata.fill_database_ids(
        torrent_info, tmdb_id, imdb_id, tvmaze_id, auto_mode, tvdb_id
    )
    assert possible_matches is None
    assert torrent_info["imdb"] == expected_ids["imdb"]
    assert torrent_info["tmdb"] == expected_ids["tmdb"]
    assert torrent_info["tvmaze"] == expected_ids["tvmaze"]
    assert torrent_info["tvdb"] == expected_ids["tvdb"]


def test_user_gave_tmdb_for_movie(mocker, monkeypatch):
    auto_mode = False
    torrent_info = {"type": "movie"}
    tmdb_id = "616037"
    imdb_id = None
    tvmaze_id = None
    tvdb_id = None
    expected_ids = {
        "imdb": "tt10648342",
        "tmdb": "616037",
        "tvmaze": "0",
        "tvdb": "0",
    }

    mocker.patch("os.getenv", return_value="IMDB_API_KEY")

    tmdb_external_response = TMDBResponse(
        json.load(
            open(
                f"{working_folder}/tests/resources/user_provided_metadata_arguments/{torrent_info['type']}/user_provided_tmdb/tmdb_external.json"
            )
        )
    )
    api_responses = iter([tmdb_external_response])

    monkeypatch.setattr("requests.get", lambda url: next(api_responses))

    possible_matches = metadata.fill_database_ids(
        torrent_info, tmdb_id, imdb_id, tvmaze_id, auto_mode, tvdb_id
    )
    assert possible_matches is None
    assert torrent_info["imdb"] == expected_ids["imdb"]
    assert torrent_info["tmdb"] == expected_ids["tmdb"]
    assert torrent_info["tvmaze"] == expected_ids["tvmaze"]
    assert torrent_info["tvdb"] == expected_ids["tvdb"]


def test_user_gave_tvmaze_for_movie(mocker, monkeypatch):
    auto_mode = False
    torrent_info = {"type": "movie", "title": "Gods of Egypt", "year": "2016"}
    tmdb_id = None
    imdb_id = None
    tvmaze_id = "12345"
    tvdb_id = None
    # this will auto select the first result since tmdb response contain only 1 result
    expected_ids = {
        "imdb": "tt2404233",
        "tmdb": "205584",
        "tvmaze": "0",
        "tvdb": "0",
    }

    tmdb_search_response = TMDBResponse(
        json.load(
            open(
                f"{working_folder}/tests/resources/user_provided_metadata_arguments/{torrent_info['type']}/user_provided_tvmaze/tmdb_search.json"
            )
        )
    )
    tmdb_external_response = TMDBResponse(
        json.load(
            open(
                f"{working_folder}/tests/resources/user_provided_metadata_arguments/{torrent_info['type']}/user_provided_tvmaze/tmdb_external.json"
            )
        )
    )
    api_responses = iter([tmdb_search_response, tmdb_external_response])

    monkeypatch.setattr("requests.get", lambda url: next(api_responses))

    possible_matches_expected = TMDBResponse(
        json.load(
            open(
                f"{working_folder}/tests/resources/user_provided_metadata_arguments/{torrent_info['type']}/user_provided_tvmaze/possible_matches.json"
            )
        )
    )

    possible_matches = metadata.fill_database_ids(
        torrent_info, tmdb_id, imdb_id, tvmaze_id, auto_mode, tvdb_id
    )
    assert possible_matches == possible_matches_expected.json()
    assert torrent_info["imdb"] == expected_ids["imdb"]
    assert torrent_info["tmdb"] == expected_ids["tmdb"]
    assert torrent_info["tvmaze"] == expected_ids["tvmaze"]
    assert torrent_info["tvdb"] == expected_ids["tvdb"]


def test_user_gave_imdb_for_tv(mocker, monkeypatch):
    auto_mode = False
    torrent_info = {"type": "episode"}
    tmdb_id = None
    imdb_id = "tt10857160"
    tvmaze_id = None
    tvdb_id = None
    expected_ids = {
        "imdb": "tt10857160",
        "tmdb": "92783",
        "tvmaze": "43517",
        "tvdb": "368613",
    }

    mocker.patch("os.getenv", return_value="IMDB_API_KEY")

    imdb_external_response = TMDBResponse(
        json.load(
            open(
                f"{working_folder}/tests/resources/user_provided_metadata_arguments/{torrent_info['type']}/user_provided_imdb/imdb_external.json"
            )
        )
    )
    tmdb_external_response = TMDBResponse(
        json.load(
            open(
                f"{working_folder}/tests/resources/user_provided_metadata_arguments/{torrent_info['type']}/user_provided_imdb/tmdb_external.json"
            )
        )
    )
    tvmaze_from_imdb = TMDBResponse(
        json.load(
            open(
                f"{working_folder}/tests/resources/user_provided_metadata_arguments/{torrent_info['type']}/user_provided_imdb/tvmaze_from_imdb.json"
            )
        )
    )
    api_responses = iter(
        [imdb_external_response, tmdb_external_response, tvmaze_from_imdb]
    )
    monkeypatch.setattr("requests.get", lambda url: next(api_responses))

    possible_matches = metadata.fill_database_ids(
        torrent_info, tmdb_id, imdb_id, tvmaze_id, auto_mode, tvdb_id
    )
    assert possible_matches is None
    assert torrent_info["imdb"] == expected_ids["imdb"]
    assert torrent_info["tmdb"] == expected_ids["tmdb"]
    assert torrent_info["tvmaze"] == expected_ids["tvmaze"]
    assert torrent_info["tvdb"] == expected_ids["tvdb"]


def test_user_gave_tmdb_for_tv(mocker, monkeypatch):
    auto_mode = False
    torrent_info = {"type": "episode"}
    tmdb_id = "92783"
    imdb_id = None
    tvmaze_id = None
    tvdb_id = None
    expected_ids = {
        "imdb": "tt10857160",
        "tmdb": "92783",
        "tvmaze": "43517",
        "tvdb": "368613",
    }

    mocker.patch("os.getenv", return_value="IMDB_API_KEY")

    tmdb_external_response = TMDBResponse(
        json.load(
            open(
                f"{working_folder}/tests/resources/user_provided_metadata_arguments/{torrent_info['type']}/user_provided_tmdb/tmdb_external.json"
            )
        )
    )
    tvmaze_from_imdb = TMDBResponse(
        json.load(
            open(
                f"{working_folder}/tests/resources/user_provided_metadata_arguments/{torrent_info['type']}/user_provided_tmdb/tvmaze_from_imdb.json"
            )
        )
    )
    api_responses = iter([tmdb_external_response, tvmaze_from_imdb])
    monkeypatch.setattr("requests.get", lambda url: next(api_responses))

    possible_matches = metadata.fill_database_ids(
        torrent_info, tmdb_id, imdb_id, tvmaze_id, auto_mode, tvdb_id
    )
    assert possible_matches is None
    assert torrent_info["imdb"] == expected_ids["imdb"]
    assert torrent_info["tmdb"] == expected_ids["tmdb"]
    assert torrent_info["tvmaze"] == expected_ids["tvmaze"]
    assert torrent_info["tvdb"] == expected_ids["tvdb"]


def test_user_gave_tvmaze_for_tv(mocker, monkeypatch):
    auto_mode = False
    torrent_info = {"type": "episode"}
    tmdb_id = None
    imdb_id = None
    tvmaze_id = "43517"
    tvdb_id = None
    expected_ids = {
        "imdb": "tt10857160",
        "tmdb": "92783",
        "tvmaze": "43517",
        "tvdb": "368613",
    }

    mocker.patch("os.getenv", return_value="IMDB_API_KEY")

    tvmaze_details_response = TMDBResponse(
        json.load(
            open(
                f"{working_folder}/tests/resources/user_provided_metadata_arguments/{torrent_info['type']}/user_provided_tvmaze/tvmaze_details.json"
            )
        )
    )
    tmdb_search_by_tvdb = TMDBResponse(
        json.load(
            open(
                f"{working_folder}/tests/resources/user_provided_metadata_arguments/{torrent_info['type']}/user_provided_tvmaze/tmdb_search_by_tvdb.json"
            )
        )
    )
    api_responses = iter([tvmaze_details_response, tmdb_search_by_tvdb])

    monkeypatch.setattr("requests.get", lambda url: next(api_responses))

    possible_matches = metadata.fill_database_ids(
        torrent_info, tmdb_id, imdb_id, tvmaze_id, auto_mode, tvdb_id
    )
    assert possible_matches is None
    assert torrent_info["imdb"] == expected_ids["imdb"]
    assert torrent_info["tmdb"] == expected_ids["tmdb"]
    assert torrent_info["tvmaze"] == expected_ids["tvmaze"]
    assert torrent_info["tvdb"] == expected_ids["tvdb"]


def test_user_gave_tvdb_for_tv(mocker, monkeypatch):
    auto_mode = False
    torrent_info = {"type": "episode"}
    tmdb_id = None
    imdb_id = None
    tvmaze_id = None
    tvdb_id = "368613"
    expected_ids = {
        "imdb": "tt10857160",
        "tmdb": "92783",
        "tvmaze": "43517",
        "tvdb": "368613",
    }

    mocker.patch("os.getenv", return_value="IMDB_API_KEY")

    tmdb_search_by_tvdb = TMDBResponse(
        json.load(
            open(
                f"{working_folder}/tests/resources/user_provided_metadata_arguments/{torrent_info['type']}/user_provided_tvdb/tmdb_search_by_tvdb.json"
            )
        )
    )
    tvmaze_search_by_tvdb = TMDBResponse(
        json.load(
            open(
                f"{working_folder}/tests/resources/user_provided_metadata_arguments/{torrent_info['type']}/user_provided_tvdb/tvmaze_search_by_tvdb.json"
            )
        )
    )
    tmdb_external = TMDBResponse(
        json.load(
            open(
                f"{working_folder}/tests/resources/user_provided_metadata_arguments/{torrent_info['type']}/user_provided_tvdb/tmdb_external.json"
            )
        )
    )

    api_responses = iter(
        [tmdb_search_by_tvdb, tvmaze_search_by_tvdb, tmdb_external]
    )

    monkeypatch.setattr("requests.get", lambda url: next(api_responses))

    possible_matches = metadata.fill_database_ids(
        torrent_info, tmdb_id, imdb_id, tvmaze_id, auto_mode, tvdb_id
    )
    assert possible_matches is None
    assert torrent_info["imdb"] == expected_ids["imdb"]
    assert torrent_info["tmdb"] == expected_ids["tmdb"]
    assert torrent_info["tvmaze"] == expected_ids["tvmaze"]
    assert torrent_info["tvdb"] == expected_ids["tvdb"]
