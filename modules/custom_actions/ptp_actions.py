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

import json
import logging
import pickle
import re
from pathlib import Path

import ptpimg_uploader
import requests
from imdb import Cinemagoer
from rich.console import Console
from rich.prompt import Prompt

from utilities.utils import (
    prepare_headers_for_tracker,
    write_cutsom_user_inputs_to_description,
)
from modules.config import PTPImgConfig, TrackerConfig
from modules.tfa.tfa import get_totp_token

console = Console()


def _get_tags(imdb_tags, tmdb_tags):
    tags = []
    imdb_tags.extend(tmdb_tags)
    input_tags = set(imdb_tags)
    ptp_tags = [
        "action",
        "adventure",
        "animation",
        "arthouse",
        "asian",
        "biography",
        "camp",
        "comedy",
        "crime",
        "cult",
        "documentary",
        "drama",
        "experimental",
        "exploitation",
        "family",
        "fantasy",
        "film.noir",
        "history",
        "horror",
        "martial.arts",
        "musical",
        "mystery",
        "performance",
        "philosophy",
        "politics",
        "romance",
        "sci.fi",
        "short",
        "silent",
        "sport",
        "thriller",
        "video.art",
        "war",
        "western",
    ]
    for tag in ptp_tags:
        if any(tag.replace(".", "") in x for x in input_tags):
            tags.append(tag)
    return tags


def check_for_existing_group(torrent_info, tracker_settings, tracker_config):
    # group_check_url = tracker_config["dupes"]["url_format"].format(search_url=str(tracker_config["torrents_search"]), imdb=torrent_info["imdb"])
    group_check_url = f"https://passthepopcorn.me/ajax.php?imdb={torrent_info['imdb_with_tt']}&action=torrent_info&fast=1"

    headers = prepare_headers_for_tracker(
        tracker_config["dupes"]["technical_jargons"],
        "PTP",
        TrackerConfig("PTP").API_KEY,
    )
    try:
        response = requests.get(url=group_check_url, headers=headers).json()[0]
        if "groupid" in response:
            # group already exists on tracker
            logging.info(
                "CustomActions][PTP] Identified a group for this upload in PTP."
            )
            groupID = response.get("groupid")
            logging.info(
                f"[CustomActions][PTP] Matched IMDb id {torrent_info['imdb_with_tt']} to group with id {groupID}"
            )
            console.print(
                f"[bold cyan] * Matched IMDb: [yellow]{torrent_info['imdb_with_tt']}[/yellow] to Group ID: [yellow]{groupID}[/yellow] [/bold cyan]"
            )
            console.print(
                f"[bold cyan] * Title: [yellow]{response.get('title')}[/yellow] ([yellow]{response.get('year')}[/bold cyan])"
            )
            # to upload a release to an existing group, we need add group information to param
            # updating the `upload_form` url in tracker_config
            tracker_config[
                "upload_form"
            ] = f'{tracker_config["upload_form"]}?groupid={groupID}'
            # along with this we also add the group to tracker settings
            tracker_settings["groupid"] = groupID
        else:
            # if no group is present in ptp then we'll need to send more details to the tracker.
            # these details are fetched here and added to `tracker_settings`
            logging.info(
                f"[CustomActions][PTP] Failed to match IMDb id {torrent_info['imdb_with_tt']} to any groups on PTP"
            )
            logging.info(
                "[CustomActions][PTP] Filling details required for a new group upload."
            )
            # we try to use the data we got from PTP to fill the metadata.
            # for any missing values, we use the data that we have obtained from tmdb and imdb.
            # ------- Poster -------
            poster = response.get("art", "")
            if poster == "":
                logging.info(
                    "CustomActions][PTP] Could not get poster from PTP. Trying to use the poster from IMDB / TMDB."
                )
                # we couldn't get poster information from ptp for some reason. Lets get that metadata from imdb / tmdb
                if len(torrent_info["tmdb_metadata"]["poster"]) > 0:
                    poster = torrent_info["tmdb_metadata"]["poster"]
                elif len(torrent_info["imdb_metadata"]["poster"]) > 0:
                    poster = torrent_info["imdb_metadata"]["poster"]
                else:
                    console.print(
                        "[red]We couldn't find any [cyan]poster[/cyan] for this show.[/red]"
                    )
                    while poster == "":
                        poster_url = console.input(
                            "Please provide a poster url manually. Supported formats => jpg / png\n"
                        )
                        if "ptpimg" in poster_url:
                            poster = poster_url
                        elif poster_url.endswith((".jpg", ".png")):
                            poster = _rehost_to_ptpimg(poster_url)
                        else:
                            console.print(
                                "Please enter a valid poster url. Note that this should be a direct link to the poster image"
                            )
            else:
                # we got a poster from PTP. lets now reupload it to ptpimg and use it
                logging.info(
                    "[CustomActions][PTP] Re hosting poster from PTP to ptpimg."
                )
                try:
                    poster = _rehost_to_ptpimg(poster)
                except Exception as ex:
                    # in case of any failures we'll use the image that ptp has returned
                    logging.exception(
                        "[CustomActions][PTP] Error occurred while trying to reupload poster image to ptpimg",
                        exc_info=ex,
                    )
            # ------- Poster -------

            # ------- Tags -------
            tags = response.get("tags", "")
            if tags == "":
                tags = _get_tags(
                    torrent_info["imdb_metadata"]["tags"],
                    torrent_info["tmdb_metadata"]["tags"],
                )
                logging.info(
                    f"[CustomAction][PTP] Tags identified for this release: {tags}"
                )
            else:
                logging.info(
                    f"[CustomAction][PTP] Tags obtained from PTP for this release: {tags}"
                )
            # ------- Tags -------

            # ------- Overview -------
            overview = response.get("plot", "")
            if overview == "":
                if len(torrent_info["tmdb_metadata"]["overview"]) > 0:
                    overview = torrent_info["tmdb_metadata"]["overview"]
                elif len(torrent_info["imdb_metadata"]["overview"]) > 0:
                    overview = torrent_info["imdb_metadata"]["overview"]
                else:
                    console.print(
                        "[red]We couldn't find any [cyan]Plot / Overview[/cyan] for this show.[/red]"
                    )
                    while overview == "":
                        user_overview = console.input(
                            f"Please provide the plot / overview of {torrent_info['title']}\n"
                        )
                        overview = (
                            user_overview
                            if len(user_overview) > 0
                            else overview
                        )
            else:
                logging.info(
                    f"[CustomAction][PTP] Overview obtained from PTP for this release: {overview}"
                )
            # ------- Overview -------

            # ------- Trailer -------
            trailer = ""
            if (
                "tmdb_metadata" in torrent_info
                and "trailer" in torrent_info["tmdb_metadata"]
                and len(torrent_info["tmdb_metadata"]["trailer"]) > 0
            ):
                trailer = torrent_info["tmdb_metadata"]["trailer"][0]
            # ------- Trailer -------

            metadata = {
                "title": response.get("title", torrent_info["title"]),
                "year": response.get("year", torrent_info["year"]),
                "image": poster,
                "tags": tags,
                "album_desc": overview,
                "trailer": trailer,
            }
            tracker_settings.update(metadata)
    except Exception as ex:
        logging.exception(
            "[CustomActions][PTP] Failed to check for existing groups.",
            exc_info=ex,
        )


def _rehost_to_ptpimg(
    image_url_list,
):  # TODO: will this raise any exceptions ??
    return ptpimg_uploader.upload(
        api_key=PTPImgConfig().API_KEY, files_or_urls=image_url_list, timeout=15
    )


def rehost_screens_to_ptpimg(torrent_info, tracker_settings, _):
    if "screenshots_data" not in torrent_info:
        logging.info(
            "[CustomActions][PTP] No screenshots available for re-hosting"
        )
        return

    # checking whether the "screenshots_data" have `ptp_rehosted`. If present, then we will
    # use it and proceed. Else we'll reupload the urls and save to screenshots_data
    console.print(
        "[bold magenta] Re-hosting non ptpimg screenshots to ptpimg[/bold magenta]"
    )
    logging.info(
        "[CustomActions][PTP] Re-uploading non-ptpimg screenshots to ptpimg"
    )
    screenshots_data = json.load(open(torrent_info["screenshots_data"]))

    if (
        "ptp_rehosted" in screenshots_data
        and screenshots_data["ptp_rehosted"] is not None
        and len(screenshots_data["ptp_rehosted"]) > 0
    ):
        logging.info(
            "[CustomActions][PTP] Obtained rehosted url from screenshot_data. Proceeding with this value"
        )
        logging.info(
            f"[CustomActions][PTP] Rehosted url from screenshot_data: {screenshots_data['ptp_rehosted']}"
        )
        tracker_settings["ptp_rehosted"] = screenshots_data["ptp_rehosted"]
        return

    ptp_img_urls = list(
        filter(
            lambda url: len(url) > 0,
            map(
                lambda url: url.replace("\n", ""),
                filter(
                    lambda url: "ptpimg.me" in url,
                    torrent_info["url_images"].split("\n"),
                ),
            ),
        )
    )
    non_ptp_img_urls = list(
        filter(
            lambda url: len(url) > 0,
            map(
                lambda url: url.replace("\n", ""),
                filter(
                    lambda url: "ptpimg.me" not in url,
                    torrent_info["url_images"].split("\n"),
                ),
            ),
        )
    )

    logging.info(f"[CustomActions][PTP] Ptpimg urls: {ptp_img_urls}")
    logging.info(f"[CustomActions][PTP] Non Ptpimg urls: {non_ptp_img_urls}")

    if len(non_ptp_img_urls) > 0:
        ptp_img_upload = _rehost_to_ptpimg(non_ptp_img_urls)
        logging.info(
            f"[CustomActions][PTP] Reuploaded screenshots response: {ptp_img_upload}"
        )
        ptp_img_upload.extend(ptp_img_urls)
        logging.info(
            f"[CustomActions][PTP] Reuploaded screenshots ptpimg url: {ptp_img_upload}"
        )
        tracker_settings["ptp_rehosted"] = ptp_img_upload
    else:
        tracker_settings["ptp_rehosted"] = ptp_img_urls
    screenshots_data["ptp_rehosted"] = tracker_settings["ptp_rehosted"]

    with open(torrent_info["screenshots_data"], "w") as screenshots_file:
        screenshots_file.write(json.dumps(screenshots_data))
    logging.info(
        "[CustomActions][PTP] Finished re uploading non-ptpimg screenshots to ptpimg"
    )


def rewrite_description(torrent_info, tracker_settings, tracker_config):
    # TODO: PTP needs mediainfo and on e screenshot from each file.
    # currently we support only movies, hence there will only be one file and ignoring this for now

    # to set remaster = "on" if remaster_title is not empty (ie: some tags are present)
    # internalrip for personal releases
    logging.info(
        "[CustomActions][PTP] Preparing description in template needed for PTP"
    )
    ptp_description_file = torrent_info["description"].replace(
        "description.txt", "ptp_description.txt"
    )

    # writing custom_descriptions
    if (
        "custom_user_inputs" in torrent_info
        and torrent_info["custom_user_inputs"] is not None
    ):
        write_cutsom_user_inputs_to_description(
            torrent_info=torrent_info,
            description_file_path=ptp_description_file,
            config=tracker_config,
            tracker="PTP",
            bbcode_line_break=tracker_config["bbcode_line_break"],
            debug=True,
        )

    with open(ptp_description_file, "a") as ptp_description:
        # writing mediainfo to description
        mediainfo = open(torrent_info["mediainfo"]).read()
        ptp_description.write(f"[mediainfo]{mediainfo}[/mediainfo]\n")
        # writing screenshots to description
        ptp_description.write("[align=center]..:: Screenshots ::..\n")
        for screenshot in tracker_settings["ptp_rehosted"]:
            ptp_description.write(f"[img]{screenshot}[/img]\n")
        if torrent_info["release_group"] == "DrDooFenShMiRtZ":
            ptp_description.write(
                "Uploaded with [color=#ff0000]❤[/color] using GG-BOT Upload Assistantinator[/align]"
            )
        else:
            ptp_description.write(
                "Uploaded with [color=#ff0000]❤[/color] using GG-BOT Upload Assistant[/align]"
            )

    tracker_settings["release_desc"] = ptp_description_file
    logging.info("[CustomActions][PTP] Finished creating description for PTP")


def get_ptp_type(torrent_info, tracker_settings, _):
    # TODO: get the type from PTP
    # TODO: multi audio being identified even when its not multi audio.
    # TODO: check cases when we don't get imdb id.
    tracker_settings["type"] = None
    logging.info(
        "[CustomActions][PTP] Attempting to identify the type applicable to PTP"
    )
    try:
        movie_details = Cinemagoer().get_movie(torrent_info["imdb"])
    except Exception:
        movie_details = None

    # Interesting data in movie_details are
    # "cover url", imdbID, kind,
    # languages, "language codes",
    # runtimes, title, year
    if movie_details is not None:
        # we we can get the `kind` from IMDb we can use that to find the PTP type.
        kind = movie_details.get("kind", "movie").lower()
        # TODO: this doesn't seem to work always. Find another way to get this working
        if kind in ("movie", "tv movie"):
            # if this is a movie, then we need to compare the runtimes to decide between Feature and Short Films
            if int(movie_details.get("runtimes", ["0"])[0]) >= 45:
                tracker_settings["type"] = "Feature Film"
            else:
                tracker_settings["type"] = "Short Film"
        elif kind == "comedy":
            tracker_settings["type"] = "Stand-up Comedy"
        elif kind == "concert":
            tracker_settings["type"] = "Concert"
        elif kind == "short":
            tracker_settings["type"] = "Short Film"
        elif kind == "tv mini series":
            tracker_settings["type"] = "Miniseries"
    else:
        # In cases where we do not have a `kind` value from IMDb we need to choose a type from the `keywords`.
        # keywords will be all lower case
        keywords = (
            torrent_info["tmdb_metadata"]["keywords"]
            if torrent_info["tmdb_metadata"] is not None
            else []
        )
        if torrent_info["type"] == "movie":
            duration_in_minutes = int(
                (int(torrent_info["duration"]) / 6) / 10000
            )
            if duration_in_minutes >= 45:
                tracker_settings["type"] = "Feature Film"
            else:
                tracker_settings["type"] = "Short Film"
            if "miniseries" in keywords:
                tracker_settings["type"] = "Miniseries"
            if (
                "short" in keywords
                or "short film" in keywords
                or "short-film" in keywords
            ):
                tracker_settings["type"] = "Short Film"
            elif (
                "stand-up comedy" in keywords
                or "stand up comedy" in keywords
                or "stand-up-comedy" in keywords
            ):
                tracker_settings["type"] = "Stand-up Comedy"
            elif "concert" in keywords:
                tracker_settings["type"] = "Concert"

    if tracker_settings["type"] is None:
        console.print("[red]We couldn't detect the type for PTP[/red]")
        tracker_settings["type"] = Prompt.ask(
            "Please provide the type manually: ",
            choices=[
                "Feature Film",
                "Short Film",
                "Miniseries",
                "Stand-up Comedy",
                "Concert",
                "Movie Collection",
            ],
        )

    logging.info(
        f"[CustomActions][PTP] Successfully identified the type as {tracker_settings['type']} for PTP"
    )


def _is_english_subs_present(subtitles=None):
    if subtitles is None:
        subtitles = []
    for subs in subtitles:
        if subs == 3:
            return True
    return False


def _is_non_english_release(torrent_info):
    original_language = (
        torrent_info["tmdb_metadata"]["original_language"]
        if torrent_info["tmdb_metadata"] is not None
        else ""
    )
    return original_language != "en"


def _no_subs_in_release(subtitles=None):
    if subtitles is None:
        subtitles = []
    for subs in subtitles:
        if subs == 44:
            return True
    return False


def add_trumpable_flags(torrent_info, tracker_settings, tracker_config):
    is_non_english_release = _is_non_english_release(torrent_info)
    is_english_subs_present = _is_english_subs_present(
        tracker_settings["subtitles[]"]
    )
    no_subs_in_release = _no_subs_in_release(tracker_settings["subtitles[]"])

    trumpable = None
    # for all non-english release if there are no subtiles or if english subtitle is not present
    if is_non_english_release and (
        no_subs_in_release or not is_english_subs_present
    ):
        trumpable = _get_trumpable_flags()
    else:
        logging.info(
            "[CustomActions][PTP] Subtitle is present / english audio release. No need to add any trumpable tags."
        )
    tracker_settings["trumpable[]"] = trumpable


def _get_trumpable_flags():
    trumpable_values = {"Hardcoded Subs (Full)": 4, "No English Subs": 14}
    console.print("[red]Possible trumpable release.[/red]")
    console.print("1. Hardcoded Subs")
    console.print("2. No English Subs")
    console.print("3. Non-Trumpable")
    trumpable = Prompt.ask(
        "Select one of the flags that apply: ", choices=["1", "2"], default="3"
    )
    if trumpable == "1":
        return 4
    elif trumpable == "2":
        return 14
    return None


def add_subtitle_information(torrent_info, tracker_settings, _):
    subtitle_mapping = {
        ("English", "eng", "en", "English (CC)", "English - SDH"): 3,
        ("Spanish", "spa", "es"): 4,
        ("French", "fre", "fr"): 5,
        ("German", "ger", "de"): 6,
        ("Russian", "rus", "ru"): 7,
        ("Japanese", "jpn", "ja"): 8,
        ("Dutch", "dut", "nl"): 9,
        ("Danish", "dan", "da"): 10,
        ("Swedish", "swe", "sv"): 11,
        ("Norwegian", "nor", "no"): 12,
        ("Romanian", "rum", "ro"): 13,
        (
            "Chinese",
            "chi",
            "zh",
            "Chinese (Simplified)",
            "Chinese (Traditional)",
        ): 14,
        ("Finnish", "fin", "fi"): 15,
        ("Italian", "ita", "it"): 16,
        ("Polish", "pol", "pl"): 17,
        ("Turkish", "tur", "tr"): 18,
        ("Korean", "kor", "ko"): 19,
        ("Thai", "tha", "th"): 20,
        ("Portuguese", "por", "pt"): 21,
        ("Arabic", "ara", "ar"): 22,
        ("Croatian", "hrv", "hr", "scr"): 23,
        ("Hungarian", "hun", "hu"): 24,
        ("Vietnamese", "vie", "vi"): 25,
        ("Greek", "gre", "el"): 26,
        ("Icelandic", "ice", "is"): 28,
        ("Bulgarian", "bul", "bg"): 29,
        ("Czech", "cze", "cz", "cs"): 30,
        ("Serbian", "srp", "sr", "scc"): 31,
        ("Ukrainian", "ukr", "uk"): 34,
        ("Latvian", "lav", "lv"): 37,
        ("Estonian", "est", "et"): 38,
        ("Lithuanian", "lit", "lt"): 39,
        ("Hebrew", "heb", "he"): 40,
        ("Hindi" "hin", "hi"): 41,
        ("Slovak", "slo", "sk"): 42,
        ("Slovenian", "slv", "sl"): 43,
        ("Indonesian", "ind", "id"): 47,
        ("Brazilian Portuguese", "Brazilian", "Portuguese-BR", "pt-br"): 49,
        ("English - Forced", "English (Forced)", "en (Forced)"): 50,
        (
            "English Intertitles",
            "English (Intertitles)",
            "English - Intertitles",
            "en (Intertitles)",
        ): 51,
        ("Persian", "fa", "far"): 52,
    }

    logging.info(
        "[CustomActions][PTP] Adding subtitles information to tracker payload"
    )
    available_subtitles = []
    # TODO: test the performance impact of this nested looping.
    # If its too bad, then opt to denormalize data
    # TODO: Test with a brazilian portuguese and eng forced subs
    for subtitle in torrent_info["subtitles"]:
        # english subs have some variations
        if subtitle["language_code"] == "en":
            if subtitle["Forced"] == "Yes":
                subtitle["language_code"] = "en (Forced)"
            if "intertitles" in subtitle["Title"].lower():
                subtitle["language_code"] = "en (Intertitles)"

        for lang, subtitleId in subtitle_mapping.items():
            if (
                subtitle["language_code"] in lang
                or ("title" in subtitle and subtitle["title"] in lang)
                and subtitleId not in available_subtitles
            ):
                available_subtitles.append(subtitleId)

    if len(torrent_info["subtitles"]) < 1:
        logging.info(
            "[CustomActions][PTP] There are not subtitles available from mediainfo summary"
        )

    if len(available_subtitles) < 1:
        logging.info(
            "[CustomActions][PTP] Couldn't identify any subtitles using the provided mapping."
        )
        available_subtitles = [44]  # id for no Subtitle

    logging.info(
        f"[CustomActions][PTP] Adding the following subtitle ids to tracker payload : {available_subtitles}"
    )
    tracker_settings["subtitles[]"] = available_subtitles


def mark_scene_release_if_applicable(torrent_info, tracker_settings, _):
    if "scene" in torrent_info and torrent_info["scene"] == "true":
        logging.info(
            "[CustomActions][PTP] Marking the upload as a scene release for PTP"
        )
        tracker_settings["scene"] = "on"
    else:
        logging.info(
            "[CustomActions][PTP] Upload is not a scene release. Removing scene info from tacker payload."
        )
        tracker_settings.pop("scene", None)


def fix_other_resolution(_, tracker_settings, __):
    if tracker_settings["resolution"] == "Other":
        logging.info(
            "[CustomActions][PTP] Uploader identified resolution as 'Other'. Removing the resolution from payload"
        )
        # if we couldn't map the video resolution to one, that is applicable to ptp groups, then we can just remove
        # the resolution key and PTP will detect and upload the width and height.
        tracker_settings.pop("resolution", None)
    else:
        logging.info(
            "[CustomActions][PTP] Resolution is not 'Other'. No actions needed"
        )


def get_crsf_token(torrent_info, tracker_settings, tracker_config):
    tracker_env_config = TrackerConfig("PTP")
    # first lets create a cookies folder to store ptp login cookies.
    if not Path(f"{torrent_info['cookies_dump']}cookies").is_dir():
        Path(f"{torrent_info['cookies_dump']}cookies").mkdir(
            parents=True, exist_ok=True
        )

    cookiefile = f"{torrent_info['cookies_dump']}cookies/cookie.dat"

    with requests.Session() as session:
        # if we have a cookie file saved previously (user running with resume flag), then we can reuse it.
        if Path(cookiefile).is_file():
            session.cookies.update(pickle.load(open(cookiefile, "rb")))
            uploadresponse = session.get(tracker_config["upload_form"])
            if (
                uploadresponse.text.find(
                    """Dear, Hacker! Do you really have nothing better do than this?"""
                )
                != -1
            ):
                logging.info(
                    "[CustomAction][PTP] Could not login to PTP using the stored cookies."
                )
            else:
                crsf_token = re.search(
                    r'data-AntiCsrfToken="(.*)"', uploadresponse.text
                ).group(1)
                tracker_settings["AntiCsrfToken"] = crsf_token
                return cookiefile

        logging.info(
            "[CustomActions][PTP] PTP Cookies not found. Creating new session."
        )
        tracker_passkey = re.match(
            r"https?://please\.passthepopcorn\.me:?\d*/(.+)/announce",
            tracker_env_config.ANNOUNCE_URL,
        ).group(1)
        data = {
            "username": tracker_env_config.get_config("PTP_USER_NAME"),
            "password": tracker_env_config.get_config("PTP_USER_PASSWORD"),
            "passkey": tracker_passkey,
            "keeplogged": "1",
        }
        # adding tfa code if user has tfa enabled
        if tracker_env_config.get_config("PTP_2FA_ENABLED", False):
            data["TfaType"] = "normal"
            logging.info(
                "[CustomActions][PTP] User has 2FA enabled. Trying to generate TOTP code."
            )
            data["TfaCode"] = get_totp_token(
                tracker_env_config.get_config("PTP_2FA_CODE", "")
            )

        headers = {}
        session_response = session.post(
            "https://passthepopcorn.me/ajax.php?action=login",
            data=data,
            headers=headers,
        )
        session_response = session_response.json()

        if session_response["Result"] != "Ok":
            raise Exception(
                f"Failed to login to PTP. Bad 'username' / 'password' / '2fa_key' provided: {session_response}"
            )

        logging.info(
            "[CustomActions][PTP] Successfully logged in to PTP and obtained cross site request forgery token."
        )
        pickle.dump(session.cookies, open(cookiefile, "wb"))
        tracker_settings["AntiCsrfToken"] = session_response["AntiCsrfToken"]
        return cookiefile


def check_successful_upload(response):
    response_text = response.text

    # If the response contains our announce url then we are on the upload page and the upload wasn't successful.
    if (
        response_text is not None
        and response_text.find(TrackerConfig("PTP").ANNOUNCE_URL) != -1
    ):
        # Get the error message.
        # <div class="alert alert--error text--center">No torrent file uploaded, or file is empty.</div>
        errorMessage = ""
        match = re.search(
            r"""<div class="alert alert--error.*?><div>(.+?)<\/div>""",
            response_text,
        )
        if match is not None:
            errorMessage = match.group(1)
        else:
            match = re.search(
                r"""<a class="alert-bar__link" href="user\.php\?action=sessions">(.+?)<\/a><\/div>""",
                response_text,
            )
            if match is not None:
                errorMessage = match.group(1)
        logging.error(
            f"[CustomActions][PTP] Upload to tracker failed due to: {errorMessage}"
        )
        return False, errorMessage

    # URL format in case of successful upload: https://passthepopcorn.me/torrents.php?id=9329&torrentid=91868
    match = re.match(
        r"http[s]*:\/\/passthepopcorn\.me\/torrents\.php\?id=(\d+)&torrentid=(\d+)",
        response.url,
    )
    if match is None:
        return (
            False,
            f"Unexpected result. Couldn't detect torrent url:: {response.url}",
        )
    else:
        logging.info(
            f"[CustomAction][PTP] Upload to PTP successful. Group ID :: {match[0]}, Torrent ID :: {match[1]}"
        )
    return True, "Successfully Uploaded to PTP"
