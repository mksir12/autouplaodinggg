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

import sys
import logging
import requests

from rich import box
from imdb import Cinemagoer
from rich.table import Table
from rich.prompt import Prompt
from rich.console import Console
import modules.env as Environment

console = Console()


def _do_tmdb_search(url):
    return requests.get(url)


def __is_auto_reuploader():
    return Environment.get_tmdb_result_auto_select_threshold() is not None


def _return_for_reuploader_and_exit_for_assistant(selected_tmdb_results_data=None):
    # `auto_select_tmdb_result` => This property is present in upload assistant.
    #   For upload assistant if we don't get any results from TMDB, we stop the program.
    #
    # `tmdb_result_auto_select_threshold` => This property is present in auto reuploader.
    # For auto reuploader
    #           1. `auto_select_tmdb_result` will not be present and
    #           2. `tmdb_result_auto_select_threshold` will be present
    #   we return every id as `0` and the auto_reupload will flag the torrent as TMDB_IDENTIFICATION_FAILED
    if __is_auto_reuploader():
        return {
            "tmdb": "0",
            "imdb": "0",
            "tvmaze": "0",
            "tvdb": "0",
            "possible_matches": selected_tmdb_results_data
        }
    else:
        # TODO handle this in upload assistant. Prompt used to manually enter an id ????
        sys.exit("No results found on TMDB, try running this script again but manually supply the TMDB or IMDB ID")


def _metadata_search_tmdb_for_id(query_title, year, content_type, auto_mode):
    # TODO: try to return tvdb id as well from here
    console.line(count=2)
    console.rule("TMDB Search Results", style='red', align='center')
    console.line(count=1)

    # sanitizing query_title
    # query title with '' will allow us to narrow down the search. Although there is a chance for no match
    escaped_query_title = f'\'{query_title}\''

    # translation for TMDB API
    content_type = "tv" if content_type == "episode" else content_type
    query_year = "&year=" + str(year) if len(year) != 0 else ""

    result_num = 0
    result_dict = {}

    # here we do a two phase tmdb search. Initially we do a search with escaped title eg: 'Kung fu Panda 1'.
    # TMDB will try to match the exact title to return results. If we get data here, we proceed with it.
    #
    # if we don't get data for the escaped title request, then we do another request to get data without escaped query.
    logging.info(
        f"[MetadataUtils] GET Request: https://api.themoviedb.org/3/search/{content_type}?api_key=<REDACTED>&query={escaped_query_title}&page=1&include_adult=false{query_year}")
    # doing search with escaped title (strict search)
    search_tmdb_request = _do_tmdb_search(
        f"https://api.themoviedb.org/3/search/{content_type}?api_key={Environment.get_tmdb_api_key()}&query={escaped_query_title}&page=1&include_adult=false{query_year}")

    if search_tmdb_request.ok:
        # print(json.dumps(search_tmdb_request.json(), indent=4, sort_keys=True))
        if len(search_tmdb_request.json()["results"]) == 0:
            logging.critical("[MetadataUtils] No results found on TMDB using the title '{}' and the year '{}'".format(escaped_query_title, year))
            logging.info("[MetadataUtils] Attempting to do a more liberal TMDB Search")
            # doing request without escaped title (search is not strict)
            search_tmdb_request = _do_tmdb_search(
                f"https://api.themoviedb.org/3/search/{content_type}?api_key={Environment.get_tmdb_api_key()}&query={query_title}&page=1&include_adult=false{query_year}")

            if search_tmdb_request.ok:
                if len(search_tmdb_request.json()["results"]) == 0:
                    logging.critical(f"[MetadataUtils] No results found on TMDB using the title '{query_title}' and the year '{year}'")
                    return _return_for_reuploader_and_exit_for_assistant()
            else:
                return _return_for_reuploader_and_exit_for_assistant()

        query_title = escaped_query_title
        logging.info("[MetadataUtils] TMDB search has returned proper responses. Parseing and identifying the proper TMDB Id")
        logging.info(f'[MetadataUtils] TMDB Search parameters. Title :: {query_title}, Year :: \'{year}\'')

        tmdb_search_results = Table(show_header=True, header_style="bold cyan", box=box.HEAVY, border_style="dim")
        tmdb_search_results.add_column("Result #", justify="center")
        tmdb_search_results.add_column("Title", justify="center")
        tmdb_search_results.add_column("TMDB URL", justify="center")
        tmdb_search_results.add_column("Release Date", justify="center")
        tmdb_search_results.add_column("Language", justify="center")
        tmdb_search_results.add_column("Overview", justify="center")

        selected_tmdb_results = 0
        selected_tmdb_results_data = []
        for possible_match in search_tmdb_request.json()["results"]:

            result_num += 1  # This counter is used so that when we prompt a user to select a match, we know which one they are referring to
            # here we just associate the number count ^^ with each results TMDB ID
            result_dict[str(result_num)] = possible_match["id"]

            # ---- Parse the output and process it ---- #
            # Get the movie/tv 'title' from json response
            # TMDB will return either "title" or "name" depending on if the content your searching for is a TV show or movie
            title_match = list(map(possible_match.get, filter(lambda x: x in "title, name", possible_match)))
            title_match_result = "N.A."
            if len(title_match) > 0:
                title_match_result = title_match.pop()
            else:
                logging.error(f"[MetadataUtils] Title not found on TMDB for TMDB ID: {str(possible_match['id'])}")
            logging.info(f'[MetadataUtils] Selected Title: [{title_match_result}]')
            # TODO implement the tmdb title 1:1 comparision here. What the hell is this? what was i thinking when i created this todo???

            # Same situation as with the movie/tv title. The key changes depending on what the content type is
            selected_year = "N.A."
            year_match = list(map(possible_match.get, filter(lambda x: x in "release_date, first_air_date", possible_match)))
            if len(year_match) > 0:
                selected_year = year_match.pop()
            else:
                logging.error(f"[MetadataUtils] Year not found on TMDB for TMDB ID: {str(possible_match['id'])}")
            logging.info(f'[MetadataUtils] Selected Year: [{selected_year}]')

            # attempting to eliminate tmdb results based on year.
            # if the year we have is 2005, then we will only consider releases from year 2004, 2005 and 2006
            # entries from all other years will be eliminated
            if content_type == "tv":
                logging.info("[MetadataUtils] Skipping year matching since this is an episode.")
            elif year != "" and int(year) > 0 and selected_year != "N.A." and len(selected_year) > 0:
                year = int(year)
                selected_year_sub_part = int(selected_year.split("-")[0])
                logging.info(f"[MetadataUtils] Applying year filter. Expected years are [{year - 1}, {year}, or {year + 1}]. Obtained year [{selected_year_sub_part}]")
                if selected_year_sub_part == year or selected_year_sub_part == year - 1 or selected_year_sub_part == year + 1:
                    logging.info("[MetadataUtils] The possible match has passed the year filter")
                else:
                    logging.info("[MetadataUtils] The possible match failed to pass year filter.")
                    del result_dict[str(result_num)]
                    result_num -= 1
                    continue

            if "overview" in possible_match:
                if len(possible_match["overview"]) > 1:
                    overview = possible_match["overview"]
                else:
                    logging.error(f"[MetadataUtils] Overview not found on TMDB for TMDB ID: {str(possible_match['id'])}")
                    overview = "N.A."
            else:
                overview = "N.A."
            # ---- (DONE) Parse the output and process it (DONE) ---- #

            # Now add that json data to a row in the table we show the user
            selected_tmdb_results_data.append({
                "result_num": result_num,
                "title": title_match_result,
                "content_type": content_type,
                "tmdb_id": possible_match['id'],
                "release_date": selected_year,
                "language": possible_match["original_language"],
                "overview": overview
            })
            tmdb_search_results.add_row(
                f"[chartreuse1][bold]{str(result_num)}[/bold][/chartreuse1]", title_match_result, f"themoviedb.org/{content_type}/{str(possible_match['id'])}",
                str(selected_year), possible_match["original_language"], overview, end_section=True
            )
            selected_tmdb_results += 1

        logging.info(f"[MetadataUtils] Total number of results for TMDB search: {str(result_num)}")
        if result_num < 1:
            console.print("Cannot auto select a TMDB id. Marking this upload as [bold red]TMDB_IDENTIFICATION_FAILED[/bold red]")
            logging.info("[MetadataUtils] Cannot auto select a TMDB id. Marking this upload as TMDB_IDENTIFICATION_FAILED")
            _return_for_reuploader_and_exit_for_assistant(selected_tmdb_results_data)

        # once the loop is done we can show the table to the user
        console.print(tmdb_search_results, justify="center")

        # here we convert our integer that was storing the total num of results into a list
        list_of_num = []
        for i in range(result_num):
            i += 1
            # The idea is that we can then show the user all valid options they can select
            list_of_num.append(str(i))


        if __is_auto_reuploader():
            if selected_tmdb_results <= int(Environment.get_tmdb_result_auto_select_threshold(1)) or int(Environment.get_tmdb_result_auto_select_threshold(1)) == 0:
                console.print("Auto selected the #1 result from TMDB...")
                user_input_tmdb_id_num = "1"
                logging.info(f"[MetadataUtils] `tmdb_result_auto_select_threshold` is valid so we are auto selecting #1 from tmdb results (TMDB ID: {str(result_dict[user_input_tmdb_id_num])})")
            else:
                console.print("Cannot auto select a TMDB id. Marking this upload as [bold red]TMDB_IDENTIFICATION_FAILED[/bold red]")
                logging.info("[MetadataUtils] Cannot auto select a TMDB id. Marking this upload as TMDB_IDENTIFICATION_FAILED")
                return {
                    "tmdb": "0",
                    "imdb": "0",
                    "tvmaze": "0",
                    "tvdb": "0",
                    "possible_matches": selected_tmdb_results_data
                }
        else:
            if auto_mode or selected_tmdb_results == 1:
                console.print("Auto selected the #1 result from TMDB...")
                user_input_tmdb_id_num = "1"
                logging.info(f"[MetadataUtils] 'auto_mode' is enabled or 'only 1 result from TMDB', so we are auto selecting #1 from tmdb results (TMDB ID: {str(result_dict[user_input_tmdb_id_num])})")
            else:
                # prompt for user input with 'list_of_num' working as a list of valid choices
                user_input_tmdb_id_num = Prompt.ask("Input the correct Result #", choices=list_of_num, default="1")


        # We take the users (valid) input (or auto selected number) and use it to retrieve the appropriate TMDB ID
        # torrent_info["tmdb"] = str(result_dict[user_input_tmdb_id_num])
        tmdb = str(result_dict[user_input_tmdb_id_num])
        # once we got tmdb id, we can then call tmdb external to get the data for imdb and tvdb
        tmdb_external_ids = _get_external_ids_from_tmdb(content_type, tmdb)
        tmdb_external_ids = { "tmdb": tmdb, "imdb": "0" } if tmdb_external_ids is None else tmdb_external_ids
        tmdb_external_ids["tvmaze"] = "0" # initializing tvmaze id as 0. if user is uploading a tv show we'll try to resolve this.

        # with imdb and tvdb we can attempt to get the tvmaze id.
        if content_type in ["episode", "tv"]:  # getting TVmaze ID
            # Now we can call the function '_get_external_id()' to try and identify the TVmaze ID (insert it into torrent_info dict right away)
            if tmdb_external_ids["imdb"] != "0":
                tmdb_external_ids["tvmaze"] = str(_get_external_id(id_site='imdb', id_value=tmdb_external_ids["imdb"], external_site="tvmaze", content_type=content_type))
                if tmdb_external_ids["tvmaze"] == "0" and tmdb_external_ids["tvdb"] != "0":
                    tmdb_external_ids["tvmaze"] = str(_get_external_id(id_site='tvdb', id_value=tmdb_external_ids["tvdb"], external_site="tvmaze", content_type=content_type))

            if tmdb_external_ids["tvdb"] == "0":
                # if we couldn't get tvdb id from tmdb, we can try to get it from imdb and tvmaze
                if tmdb_external_ids["imdb"] != "0":
                    imdb_external_ids = _get_external_ids_from_imdb(tmdb)
                    tmdb_external_ids["tvdb"] = imdb_external_ids["tvdb"]

                if tmdb_external_ids["tvdb"] == "0" and tmdb_external_ids["tvmaze"] != "0":
                    tvmaze_external_ids = _get_external_ids_from_tvmaze(tmdb)
                    tmdb_external_ids["tvdb"] = tvmaze_external_ids["tvdb"]

        tmdb_external_ids["possible_matches"] = selected_tmdb_results_data
        return tmdb_external_ids
    else:
        _return_for_reuploader_and_exit_for_assistant(selected_tmdb_results_data)


def _get_external_id(id_site, id_value, external_site, content_type):
    """
        This method is called when we need to get id for `external_site` using the id `id_value` which we already have for site `id_site`

        imdb id can be obtained from tmdb id
        tmdb id can be obtained from imdb id
        tvmaze id can be obtained from imdb id
    """
    # translation for TMDB API
    content_type = "tv" if content_type == "episode" else content_type

    tmdb_id_from_imdb = f"https://api.themoviedb.org/3/find/{id_value}?api_key={Environment.get_tmdb_api_key()}&language=en-US&external_source=imdb_id"
    tmdb_id_from_imdb_redacted = f"https://api.themoviedb.org/3/find/{id_value}?api_key=<REDACTED>&language=en-US&external_source=imdb_id"
    tmdb_id_from_tvdb = f"https://api.themoviedb.org/3/find/{id_value}?api_key={Environment.get_tmdb_api_key()}&language=en-US&external_source=tvdb_id"
    tmdb_id_from_tvdb_redacted = f"https://api.themoviedb.org/3/find/{id_value}?api_key=<REDACTED>&language=en-US&external_source=tvdb_id"

    tvmaze_id_from_imdb = f"https://api.tvmaze.com/lookup/shows?imdb={id_value}"
    tvmaze_id_from_tvdb = f"https://api.tvmaze.com/lookup/shows?thetvdb={id_value}"

    try:
        if external_site == "tvmaze":  # we need tvmaze id
            # tv maze needs imdb id to search
            if id_site == "imdb": # we have imdb id
                logging.info(f"[MetadataUtils] GET Request For TVMAZE Lookup: {tvmaze_id_from_imdb}")
                tvmaze_id_request = requests.get(tvmaze_id_from_imdb).json()
                logging.debug(f"[MetadataUtils] Returning tvmaze id as `{tvmaze_id_request['id']}`")
                return str(tvmaze_id_request["id"]) if tvmaze_id_request["id"] is not None else "0"
            elif id_site == "tvdb": # we have tvdb id
                logging.info(f"[MetadataUtils] GET Request For TVMAZE Lookup: {tvmaze_id_from_tvdb}")
                tvmaze_id_request = requests.get(tvmaze_id_from_tvdb).json()
                logging.debug(f"[MetadataUtils] Returning tvmaze id as `{tvmaze_id_request['id']}`")
                return str(tvmaze_id_request["id"]) if tvmaze_id_request["id"] is not None else "0"
            else:
                logging.error(f"[MetadataUtils] We cannot get {external_site} from {id_site}. Returning '0' as response")
                return "0"

        elif external_site == "tmdb":  # we need tmdb id
            tmdb_id_request = None
            if id_site == "imdb": # we have imdb id
                logging.info(f"[MetadataUtils] GET Request For TMDB Lookup: {tmdb_id_from_imdb_redacted}")
                tmdb_id_request = requests.get(tmdb_id_from_imdb).json()
            elif id_site == "tvdb": # we have tvdb id
                logging.info(f"[MetadataUtils] GET Request For TMDB Lookup: {tmdb_id_from_tvdb_redacted}")
                tmdb_id_request = requests.get(tmdb_id_from_tvdb).json()
            else:
                logging.error(f"[MetadataUtils] We cannot get {external_site} from {id_site}. Returning '0' as response")
                return "0"

            if tmdb_id_request is not None:
                if content_type == "tv":
                    if len(tmdb_id_request["tv_results"]) == 1:
                        logging.info(f"[MetadataUtils] Returning tmdb id as `{str(tmdb_id_request['tv_results'][0]['id'])}`")
                        return str(tmdb_id_request['tv_results'][0]['id'])
                else:
                    if len(tmdb_id_request["movie_results"]) == 1:
                        logging.info(f"[MetadataUtils] Returning tmdb id as `{str(tmdb_id_request['movie_results'][0]['id'])}`")
                        return str(tmdb_id_request['movie_results'][0]['id'])
    except Exception as e:
        logging.exception(f"[MetadataUtils] Error while fetching {external_site} from {id_site}. Returning `0` as the response", exc_info=e)

    logging.info(f"[MetadataUtils] Returning fall back value of '0' for fetching id for {external_site} from {id_site} ")
    return "0"


def search_for_mal_id(content_type, tmdb_id, torrent_info):
    # if 'content_type == tv' then we need to get the TVDB ID since we're going to need it to try and get the MAL ID
    # the below mapping is needed for the Flask app hosted by the original dev.
    # TODO convert this api call to use the metadata locally
    temp_map = {
        "tvdb": 0,
        "mal": 0,
        "tmdb": tmdb_id
    }
    if content_type == 'tv':
        get_tvdb_id = f"https://api.themoviedb.org/3/tv/{tmdb_id}/external_ids?api_key={Environment.get_tmdb_api_key()}&language=en-US"
        logging.info(f"[MetadataUtils] GET Request For TVDB Lookup: https://api.themoviedb.org/3/tv/{tmdb_id}/external_ids?api_key=<REDACTED>&language=en-US")
        get_tvdb_id_response = requests.get(get_tvdb_id).json()
        # Look for the tvdb_id key
        if 'tvdb_id' in get_tvdb_id_response and get_tvdb_id_response['tvdb_id'] is not None:
            temp_map["tvdb"] = str(get_tvdb_id_response['tvdb_id'])

    # We use this small dict to auto fill the right values into the url request below
    content_type_to_value_dict = {'movie': 'tmdb', 'tv': 'tvdb'}

    # Now we we get the MAL ID

    # Before you get too concerned, this address is a flask app I quickly set up to convert TMDB/IMDB IDs to mal using this project/collection https://github.com/Fribb/anime-lists
    # You can test it out yourself with the url: http://195.201.146.92:5000/api/?tmdb=10515 to see what it returns (it literally just returns the number "513" which is the corresponding MAL ID)
    # I might just start include the "tmdb --> mal .json" map with this bot instead of selfhosting it as an api, but for now it works so I'll revisit the subject later
    tmdb_tvdb_id_to_mal = f"http://195.201.146.92:5000/api/?{content_type_to_value_dict[content_type]}={temp_map[content_type_to_value_dict[content_type]]}"
    logging.info(f"[MetadataUtils] GET Request For MAL Lookup: {tmdb_tvdb_id_to_mal}")
    mal_id_response = requests.get(tmdb_tvdb_id_to_mal)

    # If the response returns http code 200 that means that a number has been returned, it'll either be the real mal ID or it will just be 0, either way we can use it
    if mal_id_response.status_code == 200:
        temp_map["mal"] = str(mal_id_response.json())
    return temp_map["tvdb"], temp_map["mal"]


def _fill_tmdb_metadata_to_torrent_info(torrent_info, tmdb_response):
    # --------------------- _fill_tmdb_metadata_to_torrent_info ---------------------
    # TV shows on TMDB have different keys then movies so we need to set that here
    content_title = "name" if torrent_info["type"] == "episode" else "title"

    tmdb_metadata = dict()
    # saving the original language. This will be used to detect dual / multi and dubbed releases
    tmdb_metadata["runtime_minutes"] = tmdb_response["runtime"] if "runtime" in tmdb_response else ""
    tmdb_metadata["overview"] = tmdb_response["overview"] if "overview" in tmdb_response else ""
    tmdb_metadata["title"] = tmdb_response[content_title] if content_title in tmdb_response else ""
    tmdb_metadata["original_title"] = tmdb_response["original_title"] if "original_title" in tmdb_response else ""
    tmdb_metadata["original_language"] = tmdb_response["original_language"] if "original_language" in tmdb_response else ""
    tmdb_metadata["genres"] = list(map(lambda genre: genre["name"], tmdb_response["genres"])) if "genres" in tmdb_response else []
    tmdb_metadata["release_date"] = tmdb_response["release_date"] if "release_date" in tmdb_response and len(tmdb_response["release_date"]) > 0 else ""
    tmdb_metadata["poster"] = f"https://image.tmdb.org/t/p/original{tmdb_response['poster_path']}" if "poster_path" in tmdb_response and len(tmdb_response["poster_path"]) > 0 else ""
    tmdb_metadata["tags"] = list(map(lambda genre: genre.lower().replace(" ", "").replace("-", ""), tmdb_metadata["genres"]))
    torrent_info["tmdb_metadata"] = tmdb_metadata
    # --------------------- _fill_tmdb_metadata_to_torrent_info ---------------------


def _fill_imdb_metadata_to_torrent_info(torrent_info, imdb_response, datasource):
    # --------------------- _fill_imdb_metadata_to_torrent_info ---------------------
    if datasource not in ["API", "CINEMAGOER"]:
        # torrent_info["imdb_metadata"] will have None by default. Keeping that same behaviour in this case as well
        logging.error(f"[MetadataUtils] IMDb metadata from invalid source {datasource} provided. Skipping filling IMDb metadata.")
        return

    imdb_metadata = dict()
    imdb_metadata["title"] = imdb_response.get("title", '')
    imdb_metadata["original_title"] = imdb_response.get("original title", '')
    imdb_metadata["overview"] = imdb_response.get("plot", [''])[0]
    imdb_metadata["poster"] = imdb_response.get("full-size cover url", "").replace(".jpg", "._V1_FMjpg_UX750_.jpg")
    imdb_metadata["year"] = str(imdb_response.get("year"))
    imdb_metadata["kind"] = imdb_response.get("kind")
    imdb_metadata["genres"] = imdb_response.get("genres", "")
    imdb_metadata["tags"] = list(map(lambda genre: genre.lower().replace(" ", "").replace("-", ""), imdb_metadata["genres"]))
    # TODO: youtube trailer
    torrent_info["imdb_metadata"] = imdb_metadata
    # --------------------- _fill_imdb_metadata_to_torrent_info ---------------------


def _fill_keywords_in_tmdb_metadata(content_type, torrent_info):
    get_keywords_url = f"https://api.themoviedb.org/3/{content_type}/{torrent_info['tmdb']}/keywords?api_key={Environment.get_tmdb_api_key()}"
    try:
        logging.info(f"[MetadataUtils] GET Request: https://api.themoviedb.org/3/{content_type}/{torrent_info['tmdb']}/keywords?api_key=<REDACTED>")
        keywords_info = requests.get(get_keywords_url).json()

        if keywords_info is not None and "status_message" not in keywords_info:
            # now that we got a proper response from tmdb, we need to store the keywords in torrent_info
            # for movies, the keywords will be present in `keywords` and for tv shows it'll be in `results`
            keywords_attribute = "results" if content_type == "tv" else "keywords"
            torrent_info["tmdb_metadata"]["keywords"] = list(map(lambda keyword: keyword["name"].lower(), keywords_info[keywords_attribute]))
            logging.info(f"[MetadataUtils] Obtained the following keywords from TMDb :: {torrent_info['tmdb_metadata']['keywords']}")
        else:
            logging.error("[MetadataUtils] Could not obtain keywords for the release from TMDb")
    except Exception as e:
        logging.exception("[MetadataUtils] Error occured while trying to fetch keywords for the relese.", exc_info=e)


def _fill_trailers_in_tmdb_metadata(content_type, torrent_info):
    get_trailers_url = f"https://api.themoviedb.org/3/{content_type}/{torrent_info['tmdb']}/videos?api_key={Environment.get_tmdb_api_key()}"
    try:
        logging.info(f"[MetadataUtils] GET Request: https://api.themoviedb.org/3/{content_type}/{torrent_info['tmdb']}/videos?api_key=<REDACTED>")
        trailers_info = requests.get(get_trailers_url).json()

        if trailers_info is not None and "status_message" not in trailers_info:
            # now that we got a proper response from tmdb, we need to store the trailers in torrent_info
            torrent_info["tmdb_metadata"]["trailer"] = list(
                map(
                    lambda trailer: f"https://youtube.com/watch?v={trailer['key']}",
                    filter(lambda entry: entry["type"] == "Trailer" and entry["site"] == "YouTube", trailers_info["results"])
                )
            )
            logging.info(f"[MetadataUtils] Obtained the following trailers from TMDb :: {torrent_info['tmdb_metadata']['trailer']}")
        else:
            logging.error("[MetadataUtils] Could not obtain trailers for the release from TMDb")
    except Exception as e:
        logging.exception("[MetadataUtils] Error occured while trying to fetch trailers for the relese.", exc_info=e)


def metadata_compare_tmdb_data_local(torrent_info):
    # We need to use TMDB to make sure we set the correct title & year as well as correct punctuation so we don't get held up in torrent moderation queues
    # I've outlined some scenarios below that can trigger issues if we just try to copy and paste the file name as the title

    # 1. For content that is 'non-english' we typically have a foreign title that we can (should) include in the torrent title using 'AKA' (K so both TMDB & OMDB API do not include this info, so we arent doing this)
    # 2. Some content has special characters (e.g.  The Hobbit: An Unexpected Journey   or   Welcome, or No Trespassing  ) we need to include these in the torrent title
    # 3. For TV Shows, Scene groups typically don't include the episode title in the filename, but we get this info from TMDB and include it in the title
    # 4. Occasionally movies that have a release date near the start of a new year will be using the incorrect year (e.g. the movie '300 (2006)' is occasionally mislabeled as '300 (2007)'

    # This will run regardless is auto_mode is set to true or false since I consider it pretty important to comply with all site rules and avoid creating extra work for tracker staff

    # default values
    title = torrent_info["title"]
    year = torrent_info["year"] if "year" in torrent_info else None
    tvdb = "0"
    mal = "0"
    torrent_info["tmdb_metadata"] = None
    torrent_info["imdb_metadata"] = None

    content_type = "tv" if torrent_info["type"] == "episode" else torrent_info["type"]  # translation for TMDB API
    # Getting the movie / tv show details from TMDb
    get_media_info_url = f"https://api.themoviedb.org/3/{content_type}/{torrent_info['tmdb']}?api_key={Environment.get_tmdb_api_key()}"

    try:
        logging.info(f"[MetadataUtils] GET Request: https://api.themoviedb.org/3/{content_type}/{torrent_info['tmdb']}?api_key=<REDACTED>")
        get_media_info = requests.get(get_media_info_url).json()
        _fill_tmdb_metadata_to_torrent_info(torrent_info, get_media_info)
    except Exception:
        logging.exception('[MetadataUtils] Failed to get TVDB and MAL id from TMDB. Possibly wrong TMDB id.')
        return title, year, tvdb, mal

    # Check the genres for 'Animation', if we get a hit we should check for a MAL ID just in case
    for genre in torrent_info["tmdb_metadata"]["genres"]:
        if genre == 'Animation':
            tvdb, mal = search_for_mal_id(content_type=content_type, tmdb_id=torrent_info["tmdb"], torrent_info=torrent_info)

    # Acquire and set the title we get from TMDB here
    if len(torrent_info["tmdb_metadata"]["title"]) > 0:
        title = torrent_info["tmdb_metadata"]["title"]
        logging.info(f"[MetadataUtils] Using the title we got from TMDB: {title}")

    # Set the year (if exists)
    if len(torrent_info["tmdb_metadata"]["release_date"]) > 0:
        year = torrent_info["tmdb_metadata"]["release_date"][:4]
        logging.info(f"[MetadataUtils] Using the year we got from TMDB: {year}")

    # now we'll also fetch and save the keywords from TMDB.
    _fill_keywords_in_tmdb_metadata(content_type, torrent_info)

    # now we can check whether there are any youtube trailers that we can find for this release
    _fill_trailers_in_tmdb_metadata(content_type, torrent_info)
    # if we couldn't get any trailer from tmdb, then we can try to get the same from imdb
    # TODO: in most cases if tmdb does't have the trailer information, them imdb also won't have it.
    # The trailer shown in imdb website would probably be a self hosted one. Which is of no use to us.

    # now that we've added TMDb metadata and TMDb keywords, we need to add the IMDb metadata to torrent info as well.
    # We'll add the data from IMDB API and Cinemagoer
    try:
        # at this point in processing we don't have imdb without tt. Hence we create that.
        imdb_details = Cinemagoer().get_movie(torrent_info["imdb"].replace("tt", ""))
        _fill_imdb_metadata_to_torrent_info(torrent_info, imdb_details, "CINEMAGOER")
    except Exception as ex:
        logging.exception("[MetadataUtils] Exception occured while trying to get IMDb data from cinemagoer", exc_info=ex)
        # TODO: if cinemagoer fails then attempt to get this metadata from imdb api

    return title, year, tvdb, mal


def _sanitize_metadata_from_arguments(tmdb_id, imdb_id, tvmaze_id, tvdb_id):
    if not isinstance(tmdb_id, list):
        tmdb_id = [tmdb_id]
    if not isinstance(imdb_id, list):
        imdb_id = [imdb_id]
    if not isinstance(tvmaze_id, list):
        tvmaze_id = [tvmaze_id]
    if not isinstance(tvdb_id, list):
        tvdb_id = [tvdb_id]
    return tmdb_id, imdb_id, tvmaze_id, tvdb_id


def _get_external_ids_from_imdb(imdb):
    imdb_api_key = Environment.get_imdb_api_key()
    if imdb_api_key is None:
        logging.info("[MetadataUtils] IMDB Api is not enabled. Skipping metadata fetch from imdb.")
        return None

    logging.info("[MetadataUtils] Fetching external ids from IMDB")
    imdb_external_id_url = f"https://imdb-api.com/API/ExternalSites/{imdb_api_key}/{imdb}"
    imdb_external_id_url_redacted = f"https://imdb-api.com/API/ExternalSites/<REDACTED>/{imdb}"
    logging.info(f"[MetadataUtils] IMDB request url: {imdb_external_id_url_redacted}")

    try:
        imdb_response = requests.get(imdb_external_id_url).json()
        if len(imdb_response["errorMessage"]) > 0:
            logging.error(f"[MetadataUtils] Error obtained from imdb api. Error '{imdb_response['errorMessage']}' ")
            # we couldn't get any data from imdb api. Possibly invalid imdb id
            return None

        tvdb_data = imdb_response["theTVDB"]["id"] if imdb_response["theTVDB"] is not None else "0"
        tmdb_data = imdb_response["theMovieDb"]["id"] if imdb_response["theMovieDb"] is not None else "0"
        if "movies/" in tvdb_data:
            tvdb_data = "0" # for movies we ignore tvdb id
        elif tvdb_data != "0":
            tvdb_data = tvdb_data.split("&id=")[1]

        if tmdb_data !="0" and "/" in tmdb_data:
            tmdb_data = tmdb_data.split("/")[1]
        return {
            "imdb": imdb_response["imDb"]["id"],
            "tmdb": tmdb_data,
            "tvdb": tvdb_data
        }
    except Exception as e:
        logging.exception("[MetadataUtils] Fatal error occured while fetching external ids from imdb api.", exc_info=e)
        return None


def _get_external_ids_from_tmdb(content_type, tmdb):
    content_type = "tv" if content_type == "episode" else content_type

    logging.info("[MetadataUtils] Fetching external ids from TMDB")
    tmdb_external_id_url = f"https://api.themoviedb.org/3/{content_type}/{tmdb}/external_ids?api_key={Environment.get_tmdb_api_key()}&language=en-US"
    tmdb_external_id_url_redacted = f"https://api.themoviedb.org/3/{content_type}/{tmdb}/external_ids?api_key=<REDACTED>&language=en-US"
    logging.info(f"[MetadataUtils] TMDB external ids request url: {tmdb_external_id_url_redacted}")

    try:
        tmdb_response = requests.get(tmdb_external_id_url).json()
        if "status_message" in tmdb_response:
            logging.error(f"[MetadataUtils] Error obtained from tmdb api. Error '{tmdb_response['status_message']}' ")
            # we couldn't get any data from tmdb api. Possibly invalid tmdb id
            return None
        else:
            return {
                "imdb": str(tmdb_response["imdb_id"]) if "imdb_id" in tmdb_response and tmdb_response["imdb_id"] is not None else "0",
                "tmdb": str(tmdb_response["id"]),
                "tvdb": str(tmdb_response["tvdb_id"]) if "tvdb_id" in tmdb_response and tmdb_response["tvdb_id"] is not None else "0"
            }
    except Exception as e:
        logging.exception("[MetadataUtils] Fatal error occured while fetching external ids from TMDB api.", exc_info=e)
        return None


def _get_external_ids_from_tvmaze(tvmaze):
    logging.info("[MetadataUtils] Fetching external ids from TVMAZE")
    tvmaze_external_ids_url = f"https://api.tvmaze.com/shows/{tvmaze}"
    logging.info(f"[MetadataUtils] TVMAZE request url: {tvmaze_external_ids_url}")

    try:
        tvmaze_response = requests.get(tvmaze_external_ids_url).json()
        if "message" in tvmaze_response:
            logging.error(f"[MetadataUtils] Error obtained from tvmaze api. Error '{tvmaze_response['name']}' ")
            # we couldn't get any data from tvmaze api. Possibly invalid tvmaze id
            return None
        else:
            return {
                "tvmaze": str(tvmaze_response["id"]),
                "tvdb": str(tvmaze_response["externals"]["thetvdb"]) if "thetvdb" in tvmaze_response["externals"] and tvmaze_response["externals"]["thetvdb"] is not None else "0",
                "imdb": tvmaze_response["externals"]["imdb"] if "thetvdb" in tvmaze_response["externals"] and tvmaze_response["externals"]["imdb"] is not None  else "0"
            }
    except Exception as e:
        logging.exception("[MetadataUtils] Fatal error occured while fetching external ids from TVMAZE api.", exc_info=e)
        return None


def _fill_torrent_info_with_defaults(torrent_info):
    torrent_info["imdb"] = "0"
    torrent_info["tmdb"] = "0"
    torrent_info["tvdb"] = "0"
    torrent_info["mal"] = "0"
    torrent_info["tvmaze"] = "0"

# ---------------------------------------------------------------------- #
#           !!! WARN !!! This Method has side effects. !!! WARN !!!
# ---------------------------------------------------------------------- #
# The method rewrites the following fields in torrent_info
# imdb, tmdb, tvmaze, tvdb
# The method returns the data obtained from tmdb after filtering
def fill_database_ids(torrent_info, tmdb_id, imdb_id, tvmaze_id, auto_mode, tvdb_id=None):
    possible_matches = None
    metadata_providers = ['imdb', 'tmdb', 'tvmaze', 'tvdb']
    # small sanity check
    # TODO: Should the mal id collected in arguments be used ??
    tmdb_id, imdb_id, tvmaze_id, tvdb_id = _sanitize_metadata_from_arguments(tmdb_id, imdb_id, tvmaze_id, tvdb_id)
    # initializing all keys to 0 so that we can refer them without any errors down the road
    _fill_torrent_info_with_defaults(torrent_info)

    # -------- Get TMDB, IMDB & TVMAZE ID --------
    # If the TMDB/IMDB/TVMAZE was not supplied then we need to search TMDB for it using the title & year
    # If user has provided any ids as arguments then we'll add them to `torrent_info`
    # here we add imdb, tvmaze and tmdb ids to the torrent_info.
    # later down the filling process we'll detect and add tvdb id and mal id
    for media_id_key, media_id_val in {"tmdb": tmdb_id, "imdb": imdb_id, "tvmaze": tvmaze_id, "tvdb": tvdb_id}.items():
        # we include ' > 1 ' to prevent blank ID's and issues later
        if media_id_val[0] is not None and len(media_id_val[0]) > 1:
            # We have one more check here to verify that the "tt" is included for the IMDB ID (TMDB won't accept it if it doesnt)
            if media_id_key == 'imdb' and not str(media_id_val[0]).lower().startswith('tt'):
                torrent_info[media_id_key] = f'tt{media_id_val[0]}'
            else:
                torrent_info[media_id_key] = media_id_val[0]

    if all(x in torrent_info and torrent_info[x] != "0" for x in metadata_providers):
        # This means both the TVMAZE, TMDB & IMDB ID are already in the torrent_info dict
        logging.info("[MetadataUtils] TMDB, TVmaze, TVDB & IMDB ID have been identified from media_info, so no need to make any TMDB API request")

    elif any(x in torrent_info and torrent_info[x] != "0" for x in ['imdb', 'tmdb', 'tvmaze', 'tvdb']):
        # This means we can skip the search via title/year and instead use whichever ID to get the other (tmdb -> imdb and vice versa)
        ids_present = list(filter(lambda id: id in torrent_info and torrent_info[id] != "0", metadata_providers))
        ids_missing = [id for id in metadata_providers if id not in ids_present]

        logging.info(f"[MetadataUtils] We have {ids_present} with us currently.")
        logging.info(f"[MetadataUtils] We are missing {ids_missing} starting External Database API requests now")
        # ----------------------------------------
        # Priority Order
        # 1 => Ids from Mediainfo
        # 2 => Ids provided by user
        # 3 => Ids that is resolved by uploader
        # ----------------------------------------
        # First if any of the ids are available to us either from media info or user provided details, we use them to resolve the other ids.
        # After this resolution we will try to get the missing ids
        # ----------------------------------------
        # External Ids calls
        # IMDB > TMDB > TVMAZE
        # ----------------------------------------
        # To get imdb id:   we need tmdb id or tvmaze
        # to get tmdb id:   we need imdb id or tvdb id
        # to get tvmaze id: we need imdb id or tvdb id
        # to get tvdb id:   we need imdb id or tmdb id or tvmazeid

        # with imdb id      we can get tmdb id and tvmaze id and tvdb id
        # with tmdb id      we can get imdb id and tvdb id
        # with tvmaze id    we can get imdb id and tvdb id
        # with tvdb id      we can get tmdb id

        # we need to do this operation twice. Since suppose user provided a tvmaze id, which will give us tvdb.
        # using this tvdb id we might be able to resolve imdb and tvdb ids. But without attempting for a second time we won't be
        # able to get these data.
        for _ in range(0, 2):
            # Filling all the database ids from the external id requests
            if "imdb" in ids_present and any(x in ids_missing and torrent_info[x] == "0" for x in ['tmdb', 'tvdb']):
                # if imdb is available and imdb api is enabled, then we make a request to imdb api and gets the list of external ids
                _fill_ids_from_external_response(_get_external_ids_from_imdb(torrent_info["imdb"]), torrent_info, ids_missing, ids_present)

            if "tmdb" in ids_present and any(x in ids_missing and torrent_info[x] == "0" for x in ['imdb', 'tvdb']):
                # calling the get external ids api of themoviedb and filling it metadata
                _fill_ids_from_external_response(_get_external_ids_from_tmdb(torrent_info["type"], torrent_info["tmdb"]), torrent_info, ids_missing, ids_present)

            if torrent_info["type"] == "episode":

                if "tvmaze" in ids_present and any(x in ids_missing and torrent_info[x] == "0" for x in ['imdb', 'tvdb']):
                    _fill_ids_from_external_response(_get_external_ids_from_tvmaze(torrent_info["tvmaze"]), torrent_info, ids_missing, ids_present)

                if "tvdb" in ids_present:
                    # we don't use tvdb api. hence we need to handle this case manually.
                    if "tmdb" in ids_missing:
                        torrent_info["tmdb"] = _get_external_id(id_site="tvdb", id_value=torrent_info["tvdb"], external_site="tmdb", content_type=torrent_info["type"])
                        if torrent_info["tmdb"] != "0":
                            ids_missing.remove("tmdb")
                            ids_present.append("tmdb")

                    if "tvmaze" in ids_missing:
                        torrent_info["tvmaze"] = _get_external_id(id_site="tvdb", id_value=torrent_info["tvdb"], external_site="tvmaze", content_type=torrent_info["type"])
                        if torrent_info["tvmaze"] != "0":
                            ids_missing.remove("tvmaze")
                            ids_present.append("tvmaze")

                    if "imdb" in ids_missing:
                        if torrent_info["tmdb"] != "0":
                             _fill_ids_from_external_response(_get_external_ids_from_tmdb(torrent_info["type"], torrent_info["tmdb"]), torrent_info, ids_missing, ids_present)

                        if torrent_info["tvmaze"] != "0" and "imdb" in ids_missing:
                            _fill_ids_from_external_response(_get_external_ids_from_tvmaze(torrent_info["tvmaze"]), torrent_info, ids_missing, ids_present)
            # end of torrent_info["type"] == "episode"

        logging.info("[MetadataUtils] Finished fetching external ids from the provided ids. Information collected so far...")
        logging.info(f'[MetadataUtils] IMDB ID: {torrent_info["imdb"]}')
        logging.info(f'[MetadataUtils] TMDB ID: {torrent_info["tmdb"]}')
        logging.info(f'[MetadataUtils] TVMAZE ID: {torrent_info["tvmaze"]}')
        logging.info(f'[MetadataUtils] TVDB ID: {torrent_info["tvdb"]}')
        logging.info("[MetadataUtils] Attempting to resolve any ids that are still missing.")

        if "imdb" in ids_missing:
            # we couldn't get imdb id. and we cannot get it
            logging.fatal("[MetadataUtils] Could not resolve IMDB id. If IMDB Id is mandatory, then it needs to be provided via runtime argument '--imdb'")

        if "tvdb" in ids_missing and torrent_info["type"] == "episode":
            # we couldn't get tvdb id, and we cannot get it
            logging.fatal("[MetadataUtils] Could not resolve TVDB id. If TVDB Id is mandatory, then it needs to be provided via runtime argument '--tvdb'")

        if "tmdb" in ids_missing:
            # we couldn't get tmdb id. we can still get it by searching tmdb with imdb and tvdb ids
            if torrent_info["imdb"] != "0":
                torrent_info["tmdb"] = _get_external_id(id_site="imdb", id_value=torrent_info["imdb"], external_site="tmdb", content_type=torrent_info["type"])
                if torrent_info["tmdb"] != "0":
                    ids_missing.remove("tmdb")
            elif torrent_info["tvdb"] != "0":
                torrent_info["tmdb"] = _get_external_id(id_site="tvdb", id_value=torrent_info["tvdb"], external_site="tmdb", content_type=torrent_info["type"])
                if torrent_info["tmdb"] != "0":
                    ids_missing.remove("tmdb")

        if "tvmaze" in ids_missing and torrent_info["type"] == "episode":
            # we couldn't get tvmaze id. We can still attempt to get it by searching with imdb and tvdb ids
            if torrent_info["imdb"] != "0":
                torrent_info["tvmaze"] = _get_external_id(id_site="imdb", id_value=torrent_info["imdb"], external_site="tvmaze", content_type=torrent_info["type"])
                if torrent_info["tvmaze"] != "0":
                    ids_missing.remove("tvmaze")
            elif torrent_info["tvdb"] != "0":
                torrent_info["tvmaze"] = _get_external_id(id_site="tvdb", id_value=torrent_info["tvdb"], external_site="tvmaze", content_type=torrent_info["type"])
                if torrent_info["tvmaze"] != "0":
                    ids_missing.remove("tvmaze")

        logging.info("[MetadataUtils] Metadata Information collected after individual searches...")
        logging.info(f'[MetadataUtils] IMDB ID: {torrent_info["imdb"]}')
        logging.info(f'[MetadataUtils] TMDB ID: {torrent_info["tmdb"]}')
        logging.info(f'[MetadataUtils] TVMAZE ID: {torrent_info["tvmaze"]}')
        logging.info(f'[MetadataUtils] TVDB ID: {torrent_info["tvdb"]}')

        # once we try to resolve everything and still we couldn't get tmdb, then we need to fall back to search
        if torrent_info["tmdb"] == "0":
            logging.error("[MetadataUtils] Could not get TMDB id from the user provided ids. Fallbacking to TMDB search by title & year")
            possible_matches = _search_and_get_possible_matches(torrent_info, auto_mode)

    else:
        logging.error("[MetadataUtils] No ids provided by user / mediainfo. Fallbacking to TMDB search by title & year")
        possible_matches = _search_and_get_possible_matches(torrent_info, auto_mode)

    return possible_matches


def _search_and_get_possible_matches(torrent_info, auto_mode):
    # here we are missing all three mandatory id. We'll go a TMDB search and based on the result we'll decide on an id
    logging.info("[Main] We are missing the 'TMDB', 'TVMAZE' & 'IMDB' ID, trying to identify it via title & year")
    # this method searchs and gets all three ids ` 'imdb', 'tmdb', 'tvmaze' `
    metadata_result = _metadata_search_tmdb_for_id(
        query_title=torrent_info["title"], year=torrent_info["year"] if "year" in torrent_info else "", content_type=torrent_info["type"], auto_mode=auto_mode
    )
    torrent_info["tmdb"] = metadata_result["tmdb"]
    torrent_info["imdb"] = metadata_result["imdb"]
    torrent_info["tvmaze"] = metadata_result["tvmaze"]
    torrent_info["tvdb"] = metadata_result["tvdb"]
    return metadata_result["possible_matches"]


def _fill_ids_from_external_response(external_ids_resolved, torrent_info, ids_missing, ids_present):
    if external_ids_resolved is not None:
        # here we'll fill the ids that we've got so far and remove them from `ids_missing`
        for key, value in external_ids_resolved.items():
            if value is not None and value != "0" and torrent_info[key] == "0":
                torrent_info[key] = value
                ids_missing.remove(key)
                if key not in ids_present:
                    ids_present.append(key)
