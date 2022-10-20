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
import requests
import logging

from rich.prompt import Prompt
from rich.console import Console
import modules.env as Environment


console = Console()


def _fill_artist_info(tracker_settings, artist_dict, sub_name_dict, importance):
    if isinstance(sub_name_dict, list):
        sub_name_dict = {} # happens when there are no chinese names available
    if isinstance(artist_dict, list):
        artist_dict = {} # happens when there are particular type of artists

    for artist_id, artist_name in artist_dict.items():
        tracker_settings["artist_ids[]"].append(artist_id)
        tracker_settings["artists[]"].append(artist_name.strip())
        tracker_settings["importance[]"].append(importance)
        # now lets get the chinese name
        tracker_settings["artists_sub[]"].append(sub_name_dict.get(artist_name.strip(), ""))


def _get_tags(imdb_tags, tmdb_tags):
    tags = []
    imdb_tags.extend(tmdb_tags)
    input_tags = set(imdb_tags)
    gpw_tags = [
        "action", "adult", "adventure", "animation", "arthouse", "asian", "biography", "comedy",
        "crime", "cult", "documentary", "drama", "experimental", "exploitation", "family", "fantasy", "film.noir",
        "history", "horror", "martial.arts", "musical", "mystery", "performance", "politics", "romance",
        "sci.fi", "short", "silent", "sport", "thriller", "video.art", "war", "western"
    ]
    for tag in gpw_tags:
        if any(tag.replace('.', '') in x for x in input_tags):
            tags.append(tag)
    return tags


def check_for_existing_group(torrent_info, tracker_settings, tracker_config):
    logging.info("[CustomActions][GPW] Checking whether group exists on tracker")

    base_url = f'{tracker_config["upload_form"].replace("{api_key}", Environment.get_property_or_default("GPW_API_KEY", "")).replace("&action=upload", "")}'
    check_group_params = f"&action=torrent&req=group&imdbID={torrent_info['imdb_with_tt']}"
    metadata_auto_fill_params = f"&action=movie_info&imdbid={torrent_info['imdb_with_tt']}"

    check_group_url = f"{base_url}{check_group_params}"
    try:
        group_response = requests.get(check_group_url).json()
        if group_response["status"] == "failure" and group_response["error"] == "Group not found":
            # group doesn't exist on tracker. we'll need to prepare the extra metadata needed for creating a new group
            # since the group doesn't exist we need to get the movie metadata. Lets get the autofill metadata from tracker
            auto_fill_url = f"{base_url}{metadata_auto_fill_params}"
            metadata_response = requests.get(auto_fill_url).json()
            if metadata_response["status"] == 200:
                auto_fill_metadata = metadata_response["response"]["response"]

                if auto_fill_metadata["Type"] == "Movie":
                    tracker_settings["releasetype"] = "1" # Feature film
                elif auto_fill_metadata["Type"] == "Short":
                    tracker_settings["releasetype"] = "2" # Short film

                tracker_settings["name"] = auto_fill_metadata.get("Title", torrent_info["title"])
                if "SubTitle" in auto_fill_metadata: # chinese name
                    tracker_settings["subname"] = auto_fill_metadata["SubTitle"]

                # ------- Poster -------
                poster = ""
                if "Poster" in auto_fill_metadata: # chinese name
                    poster = auto_fill_metadata["Poster"]
                if poster == "":
                    logging.info("CustomActions][GPW] Could not get poster from GPW. Trying to use the poster from IMDB / TMDB.")
                    # we couldn't get poster information from ptp for some reason. Lets get that metadata from imdb / tmdb
                    if len(torrent_info["tmdb_metadata"]["poster"]) > 0:
                        poster = torrent_info["tmdb_metadata"]["poster"]
                    elif len(torrent_info["imdb_metadata"]["poster"]) > 0:
                        poster = torrent_info["imdb_metadata"]["poster"]
                    else:
                        console.print("[red]We couldn't find any [cyan]poster[/cyan] for this show.[/red]")
                        while poster == "":
                            poster_url = console.input("Please provide a poster url manually. Supported formats => jpg / png\n")
                            if poster_url.endswith(('.jpg', '.png')):
                                poster = poster_url
                            else:
                                console.print("Please enter a valid poster url. Note that this should be a direct link to the poster image")
                tracker_settings["image"] = poster
                # ------- Poster -------

                tracker_settings["year"] = auto_fill_metadata.get("Year", torrent_info["year"])

                # ------- Tags -------
                tags = auto_fill_metadata.get("Genre", "")
                if tags == "":
                    tags = _get_tags(torrent_info["imdb_metadata"]["tags"], torrent_info["tmdb_metadata"]["tags"])
                    logging.info(f"[CustomAction][GPW] Tags identified for this release: {tags}")
                else:
                    logging.info(f"[CustomAction][GPW] Tags obtained from tracker for this release: {tags}")
                tracker_settings["tags"] = tags
                # ------- Tags -------


                tracker_settings["maindesc"] = auto_fill_metadata["MainPlot"] # English description
                tracker_settings["desc"] = auto_fill_metadata["Plot"] if "Plot" in auto_fill_metadata else auto_fill_metadata["MainPlot"] # Chinese description

                # filling the personnel details
                tracker_settings["artist_ids[]"] = []
                tracker_settings["artists[]"] = []
                tracker_settings["artists_sub[]"] = []
                tracker_settings["importance[]"] = []

                _fill_artist_info(tracker_settings, auto_fill_metadata.get("Directors", {}), auto_fill_metadata["SubName"], 1)
                _fill_artist_info(tracker_settings, auto_fill_metadata.get("Writters", {}), auto_fill_metadata["SubName"], 2)
                _fill_artist_info(tracker_settings, auto_fill_metadata.get("Producers", {}), auto_fill_metadata["SubName"], 3)
                _fill_artist_info(tracker_settings, auto_fill_metadata.get("Composers", {}), auto_fill_metadata["SubName"], 4)
                _fill_artist_info(tracker_settings, auto_fill_metadata.get("Cinematographers", {}), auto_fill_metadata["SubName"], 5)
                _fill_artist_info(tracker_settings, auto_fill_metadata.get("Casts", {}), auto_fill_metadata["SubName"], 6)
                _fill_artist_info(tracker_settings, auto_fill_metadata.get("RestCasts", {}), auto_fill_metadata["SubName"], 6)

            else:
                # we couldn't get the metadata from tracker. lets log this and stop the processing for now.
                # TODO: prepare this metadata from the imdb and tmdb metadata that uploader has already collected
                logging.error("[CustomActions][GPW] Error occured while trying to fetch autofill metadata from tracker.")
        else:
            # group already exists on gpw. we just need to add a new format to tracker
            logging.info("CustomActions][GPW] Identified a group for this upload on tracker.")
            group_response = group_response["response"]
            groupID = group_response.get('ID')

            logging.info(f"[CustomActions][GPW] Matched IMDb id {torrent_info['imdb_with_tt']} to group with id {groupID}")
            console.print(f"[bold cyan] * Matched IMDb: [yellow]{torrent_info['imdb_with_tt']}[/yellow] to Group ID: [yellow]{groupID}[/yellow] [/bold cyan]")
            console.print(f"[bold cyan] * Title: [yellow]{group_response.get('Name')}[/yellow] ([yellow]{group_response.get('Year')}[/bold cyan])")
            tracker_settings["groupid"] = groupID

    except Exception as ex:
        logging.exception("[CustomActions][GPW] Error occured while trying to check for existing group on tracker", exc_info=ex)



def add_subtitle_information(torrent_info, tracker_settings, tracker_config):
    subtitle_mapping = {
        (
            "English", "eng", "en", "English - Forced", "English (Forced)", "en (Forced)", "English (CC)",
            "English - SDH", "English Intertitles", "English (Intertitles)", "English - Intertitles", "en (Intertitles)"
        ) : "english",
        ("Spanish", "spa", "es") : "spanish",
        ("French", "fre", "fr") : "french",
        ("German", "ger", "de") : "german",
        ("Russian", "rus", "ru") : "russian",
        ("Japanese", "jpn", "ja") : "japanesev",
        ("Dutch", "dut", "nl") : "dutch",
        ("Danish", "dan", "da") : "danish",
        ("Swedish", "swe", "sv") : "swedish",
        ("Norwegian", "nor", "no") : "norwegian",
        ("Romanian", "rum", "ro") : "romanian",
        ("Chinese", "chi", "zh", "Chinese (Traditional)") : "chinese_traditional",
        ("Chinese", "chi", "zh", "Chinese (Simplified)") : "chinese_simplified",
        ("Finnish", "fin", "fi") : "finnish",
        ("Italian", "ita", "it") : "italian",
        ("Polish", "pol", "pl") : "polish",
        ("Turkish", "tur", "tr") : "turkish",
        ("Korean", "kor", "ko") : "korean",
        ("Thai", "tha", "th") : "thai",
        ("Portuguese", "por", "pt") : "portuguese",
        ("Arabic", "ara", "ar") : "arabic",
        ("Croatian", "hrv", "hr", "scr") : "croatian",
        ("Hungarian", "hun", "hu") : "hungarian",
        ("Vietnamese", "vie", "vi") : "vietnamese",
        ("Greek", "gre", "el") : "greek",
        ("Icelandic", "ice", "is") : "icelandic",
        ("Bulgarian", "bul", "bg") : "bulgarian",
        ("Czech", "cze", "cz", "cs") : "czech",
        ("Serbian", "srp", "sr", "scc") : "serbian",
        ("Ukrainian", "ukr", "uk") : "ukrainian",
        ("Latvian", "lav", "lv") : "latvian",
        ("Estonian", "est", "et") : "estonian",
        ("Lithuanian", "lit", "lt") : "lithuanian",
        ("Hebrew", "heb", "he") :"hebrew",
        ("Hindi" "hin", "hi") : "hindi",
        ("Slovak", "slo", "sk") : "slovak",
        ("Slovenian", "slv", "sl") : "slovenian",
        ("Indonesian", "ind", "id") : "indonesian",
        ("Brazilian Portuguese", "Brazilian", "Portuguese-BR", 'pt-br') : "brazilian_port",
        ("Persian", "fa", "far") : "persian",
    }

    logging.info("[CustomActions][GPW] Adding subtitles information to tracker payload")
    available_subtitles = []
    tracker_settings["subtitle_type"] = 1 # softcoded subtitle
    # TODO: how to detect and tag a hardcoded subtitle
    # tracker_settings["subtitle_type"] = 2 # hardcoded subtitle

    for subtitle in torrent_info["subtitles"]:
        for lang, subtitleId in subtitle_mapping.items():
            if subtitle["language_code"] in lang or ( "title" in subtitle and subtitle["title"] in lang ) and subtitleId not in available_subtitles:
                available_subtitles.append(subtitleId)

    if len(torrent_info["subtitles"]) < 1:
        logging.info("[CustomActions][GPW] There are not subtitles available from mediainfo summary")
        tracker_settings["subtitle_type"] = 3 # no subs

    if len(available_subtitles) < 1:
        logging.info("[CustomActions][GPW] Couldn't identify any subtitles using the provided mapping.")
        tracker_settings["subtitle_type"] = 3 # no subs

    logging.info(f"[CustomActions][GPW] Adding the following subtitle ids to tracker payload : {available_subtitles}")
    tracker_settings["subtitles[]"] = available_subtitles


def check_successful_upload(response):
    # GPW tracker returns a json response but it is slightly different, hence using a custom action to parse it
    response = response.json()
    if response["status"] == 200 and response["response"]["message"] == "Succesfully uploaded torrent":
        return True, "Successfully uploaded torrent to GPW"
    else:
        return False, response["response"]["error"] if "error" in response["response"] else "Upload to GPW failed due to an unknown error."


def _rehost_to_gpw(tracker_config, image_url_list):
    image_upload_url = f'{tracker_config["upload_form"].replace("{api_key}", Environment.get_property_or_default("GPW_API_KEY", "")).replace("&action=upload", "&action=imgupload")}'
    data = {
        "urls[]" : image_url_list
    }
    image_upload_response = requests.post(image_upload_url, data=data).json()
    if image_upload_response["status"] == 200 and "error" not in image_upload_response["response"]:
        image_upload_response = list(map(lambda element: element["name"], image_upload_response["response"]["files"]))
        return image_upload_response

    raise Exception(f'Image Rehosting to GPW failed. Error: {image_upload_response["response"]["error"]}')


def rehost_screens(torrent_info, tracker_settings, tracker_config):
    if "screenshots_data" not in torrent_info:
        logging.info("[CustomActions][GPW] No screenshots available for rehosting")
        return

    # checking whether the "screenshots_data" have `ptp_rehosted`. If present, then we wiil
    # use it and proceed. Else we'll reupload the urls and save to screenshots_data
    console.print("[bold magenta] Rehosting non ptpimg/imgbox screenshots to gpw[/bold magenta]")
    logging.info("[CustomActions][GPW] Reuploading non-ptpimg/imgbox screenshots to gpw")
    screenshots_data = json.load(open(torrent_info["screenshots_data"]))

    if "gpw_rehosted" in screenshots_data and screenshots_data["gpw_rehosted"] is not None and len(screenshots_data["gpw_rehosted"]) > 0:
        logging.info("[CustomActions][GPW] Obtained rehosted url from screenshot_data. Proceeding with this value")
        logging.info(f"[CustomActions][GPW] Rehosted url from screenshot_data: {screenshots_data['gpw_rehosted']}")
        tracker_settings["gpw_rehosted"] = screenshots_data["gpw_rehosted"]
        return

    supported_hosts = list(filter(lambda url: len(url) > 0, map(lambda url: url.replace("\n", ""), filter(lambda url: "ptpimg.me" in url or "imgbox.com" in url, torrent_info["url_images"].split("\n")))))
    reupload_img_urls = list(filter(lambda url: len(url) > 0, map(lambda url: url.replace("\n", ""),
        filter(lambda url: "ptpimg.me" not in url and "imgbox.me" not in url, torrent_info["url_images"].split("\n")))))

    logging.info(f"[CustomActions][GPW] Supported urls: {supported_hosts}")
    logging.info(f"[CustomActions][GPW] Reupload urls: {reupload_img_urls}")

    if len(reupload_img_urls) > 0:
        gpw_img_upload = _rehost_to_gpw(tracker_config, reupload_img_urls)
        logging.info(f"[CustomActions][GPW] Reuploaded screenshots reponse: {gpw_img_upload}")
        gpw_img_upload.extend(supported_hosts)
        logging.info(f"[CustomActions][GPW] Reuploaded screenshots ptpimg url: {gpw_img_upload}")
        tracker_settings["gpw_rehosted"] = gpw_img_upload
    else:
        tracker_settings["gpw_rehosted"] = supported_hosts
    screenshots_data["gpw_rehosted"] = tracker_settings["gpw_rehosted"]

    with open(torrent_info["screenshots_data"], "w") as screenshots_file:
        screenshots_file.write(json.dumps(screenshots_data))
    logging.info("[CustomActions][GPW] Finished reuploading unsupported host screenshots to gpw")


def rewrite_description(torrent_info, tracker_settings, tracker_config):
    logging.info("[CustomActions][GPW] Preparing description in template needed for GPW")
    gpw_description_file = torrent_info["description"].replace("description.txt", "gpw_description.txt")

    # writing custom_descriptions
    if "custom_user_inputs" in torrent_info and torrent_info["custom_user_inputs"] is not None:
        write_cutsom_user_inputs_to_description(
            torrent_info=torrent_info,
            description_file_path=gpw_description_file,
            config=tracker_config,
            tracker="GPW",
            bbcode_line_break=tracker_config['bbcode_line_break'],
            debug=True
        )

    with open(gpw_description_file, "a") as gpw_description:
        # writing screenshots to description
        gpw_description.write("[align=center]..:: Screenshots ::..\n")
        for screenshot in tracker_settings["gpw_rehosted"]:
            gpw_description.write(f"[img]{screenshot}[/img]\n")
        gpw_description.write("\nUploaded with [color=#ff0000]❤[/color] using GG-BOT Upload Assistant[/align]")

    tracker_settings["release_desc"] = gpw_description_file
    logging.info("[CustomActions][GPW] Finished creating descrption for PTP")