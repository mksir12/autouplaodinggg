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
import logging
import re
import sys
from pathlib import Path

import requests
import urllib3
from rich.console import Console
from rich.prompt import Prompt

console = Console()


def miscellaneous_perform_scene_group_capitalization(
    scene_groups_path, torrent_info
):
    # suppressing https verify false error
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    # Scene releases after they unrared are all lowercase (usually) so we fix the torrent title here (Never rename the actual file)
    # new groups can be added in the `scene_groups.json`
    scene_group_capitalization = json.load(open(scene_groups_path))
    release_group = torrent_info["release_group"]

    # compare the release group we extracted to the groups in the dict above ^^
    if str(release_group).lower() in scene_group_capitalization.keys():
        # replace the "release_group" with the dict value we have
        # Also save the fact that this is a scene group for later (we can add a 'scene' tag later to BHD)
        return "true", scene_group_capitalization[str(release_group).lower()]

    # if we don't have this particular group not stored in the metadata, we can check whether the release is scene using pre.corroupt-net and srrdb api
    raw_file_name = torrent_info["raw_file_name"]
    if "raw_video_file" not in torrent_info:
        # user wants to upload a single file, we need to get scene release name from `raw_file_name` after removing the file format
        idx_dots = [idx for idx, x in enumerate(raw_file_name) if x == "."]
        raw_file_name = raw_file_name[: max(idx_dots)]

    # searching in pre.corrupt-net.org to check whether its a scene release or not.
    logging.info(
        "[MiscellaneousUtils] Checking for scene release in 'pre.corrupt-net'"
    )
    try:
        precorrupt_response = requests.get(
            f"https://pre.corrupt-net.org/search.php?search={raw_file_name}",
            headers={"Accept-Language": "en-US,en;q=0.8"},
            verify=False,
        ).text
    except Exception as ex:
        logging.fatal(
            f"[MiscellaneousUtils] Error from pre corroupt db.", exc_info=ex
        )
        precorrupt_response = f"Nothing found for: {raw_file_name}"

    if f"Nothing found for: {raw_file_name}" in precorrupt_response:
        # no results found in pre.corrupt-net.org. We can check srrdb api also just to be sure.
        logging.info(
            "[MiscellaneousUtils] Could not match upload to a scene release in 'pre.corroupt-net'"
        )
        logging.info(
            "[MiscellaneousUtils] Checking for scene release in 'srrdb'"
        )

        try:
            srrdb_response = requests.get(
                f"https://api.srrdb.com/v1/search/r:{raw_file_name}"
            ).json()
        except Exception as ex:
            logging.fatal(
                f"[MiscellaneousUtils] Error from srrdb.", exc_info=ex
            )
            srrdb_response = {}

        if (
            "results" not in srrdb_response
            or len(srrdb_response["results"]) < 1
        ):
            logging.info(
                "[MiscellaneousUtils] Could not match upload to a scene release in 'srrdb'"
            )
            return "false", release_group
        else:
            # TODO: is it possible to do scene group capitalization here?
            logging.info(
                "[MiscellaneousUtils] This release has been matched to a scene release in 'srrdb'"
            )
            # TODO: call https://api.srrdb.com/v1/imdb/{release_name} api to check and vverify the imdb id
            return "true", release_group
    else:
        # TODO: is it possible to do scene group capitalization here?
        logging.info(
            "[MiscellaneousUtils] This release has been matched to a scene release in 'pre.corroupt-net'"
        )
        return "true", release_group

    return "false", release_group


def miscellaneous_identify_bluray_edition(upload_media):
    # use regex (sourced and slightly modified from official radarr repo) to find torrent editions (Extended, Criterion, Theatrical, etc)
    # https://github.com/Radarr/Radarr/blob/5799b3dc4724dcc6f5f016e8ce4f57cc1939682b/src/NzbDrone.Core/Parser/Parser.cs#L21
    try:
        torrent_editions = re.search(
            r"((Recut.|Extended.|Ultimate.|Criterion.|International.)?(Director.?s|Collector.?s|Theatrical|Ultimate|Final|Criterion|International(?=(.(Cut|Edition|Version|Collection)))|Extended|Rogue|Special|Despecialized|\d{2,3}(th)?.Anniversary)(.(Cut|Edition|Version|Collection))?(.(Extended|Uncensored|Remastered|Unrated|Uncut|IMAX|FANRES|Fan.?Edit))?|(Uncensored|Remastered|Unrated|Uncut|IMAX|Fan.?Edit|FANRES|Edition|Restored|(234)in1))",
            upload_media,
        )
        logging.info(
            f"[MiscellaneousUtils] extracted '{str(torrent_editions.group()).replace('.', ' ')}' as the 'edition' for the final torrent name"
        )
        return str(torrent_editions.group()).replace(".", " ")
    except AttributeError:
        logging.error(
            "[MiscellaneousUtils] No custom 'edition' found for this torrent"
        )
    return None


def miscellaneous_identify_bluray_disc_type(
    screen_size, upload_media, test_size=None
):
    # This is just based on resolution & size so we just match that info up to the key we create below
    possible_types = [25, 50, 66, 100]
    bluray_prefix = "uhd" if screen_size == "2160p" else "bd"
    if test_size is not None:
        total_size = test_size
    else:
        total_size = sum(
            f.stat().st_size
            for f in Path(upload_media).glob("**/*")
            if f.is_file()
        )

    for possible_type in possible_types:
        if total_size < int(possible_type * 1000000000):
            return str(f"{bluray_prefix}_{possible_type}")
    return None


def miscellaneous_identify_repacks(raw_file_name):
    match_repack = re.search(
        r"RERIP|PROPER2|PROPER3|PROPER4|PROPER|REPACK2|REPACK3|REPACK4|REPACK",
        raw_file_name,
        re.IGNORECASE,
    )
    if match_repack is not None:
        logging.info(
            f'[MiscellaneousUtils] Used Regex to extract: "{match_repack.group()}" from the filename'
        )
        return match_repack.group()
    return None


def miscellaneous_identify_web_streaming_source(
    streaming_services,
    streaming_services_reverse,
    raw_file_name,
    guess_it_result,
):
    """
    First priority is given to guessit
    If guessit can get the `streaming_service`, then we'll use that
    Otherwise regex is used to detect the streaming service
    """
    # reading stream sources param json.
    # You can add more streaming platforms to the json file.
    # The value of the json keys will be used to create the torrent file name.
    # the keys are used to match the output from guessit
    streaming_sources = json.load(open(streaming_services))
    web_source = guess_it_result.get("streaming_service", "")
    web_source_name = None

    if isinstance(web_source, list):
        logging.info(
            f"[MiscellaneousUtils] GuessIt identified multiple streaming services [{web_source}]. Proceeding with the first in the list."
        )
        web_source = web_source[0]
    web_source = streaming_sources.get(web_source)

    if web_source is None:
        source_regex = (
            r"[\.|\ ](" + "|".join(streaming_sources.values()) + r")[\.|\ ]"
        )
        match_web_source = re.search(source_regex, raw_file_name.upper())
        if match_web_source is not None:
            logging.info(
                f'[MiscellaneousUtils] Used Regex to extract the WEB Source: {match_web_source.group().replace(".", "").strip()}'
            )
            web_source = match_web_source.group().replace(".", "").strip()
        else:
            logging.error(
                "[MiscellaneousUtils] Not able to extract the web source information from REGEX and GUESSIT"
            )
    else:
        logging.info(
            f"[MiscellaneousUtils] Used guessit to extract the WEB Source: {web_source}"
        )

    if web_source is not None:
        # if we have got a value for the web_source, let's also identify its full name
        streaming_sources_reverse = json.load(open(streaming_services_reverse))
        web_source_name = streaming_sources_reverse.get(web_source)

    return web_source, web_source_name


def miscellaneous_identify_source_type(raw_file_name, auto_mode, source):
    logging.debug(
        "[MiscellaneousUtils] Source type is not available. Trying to identify source type"
    )
    match_source = re.search(
        r"(?P<bluray_remux>(.*blu(.ray|ray).*remux.*)|(.*remux.*blu(.ray|ray)))|"
        r"(?P<bluray_disc>.*blu(.ray|ray)((?!x(264|265)|h.(265|264)|H.(265|264)|H(265|264)).)*$)|"
        r"(?P<webrip>.*web(.rip|rip).*)|"
        r"(?P<webdl>.*web(.dl|dl|).*)|"
        r"(?P<bluray_encode>.*blu(.ray|ray).*|x(264|265)|h.(265|264)|H.(265|264)|H(265|264)|x.(265|264))|"
        r"(?P<dvd>HD(.DVD|DVD)|.*DVD.*)|"
        r"(?P<hdtv>.*HDTV.*)",
        raw_file_name,
        re.IGNORECASE,
    )
    return_source_type = None
    if match_source is not None:
        for source_type in [
            "bluray_disc",
            "bluray_remux",
            "bluray_encode",
            "webdl",
            "webrip",
            "dvd",
            "hdtv",
        ]:
            if match_source.group(source_type) is not None:
                return_source_type = source_type

    # Well firstly if we got this far with auto_mode enabled that means we've somehow figured out the 'parent' source but now can't figure out its 'final form'
    # If auto_mode is disabled we can prompt the user
    elif not auto_mode:
        # Yeah yeah this is just copy/pasted from the original user_input source code, it works though ;)
        basic_source_to_source_type_dict = {
            # this dict is used to associate a 'parent' source with one if its possible final forms
            "bluray": ["disc", "remux", "encode"],
            "web": ["rip", "dl"],
            "hdtv": "hdtv",
            "dvd": ["disc", "remux", "rip"],
            "pdtv": "pdtv",
            "sdtv": "sdtv",
        }
        # Since we already know the 'parent source' from an earlier function we don't need to prompt the user for it twice
        if str(
            source
        ).lower() in basic_source_to_source_type_dict and isinstance(
            basic_source_to_source_type_dict[str(source).lower()], list
        ):
            console.print(
                "\nError: Unable to detect this medias 'format'", style="red"
            )
            console.print(
                f"\nWe've successfully detected the 'parent source': [bold]{source}[/bold] but are unable to detect its 'final form'",
                highlight=False,
            )
            logging.error(
                f"[MiscellaneousUtils] We've successfully detected the 'parent source': [bold]{source}[/bold] but are unable to detect its 'final form'"
            )

            # Now prompt the user
            specific_source_type = Prompt.ask(
                f"\nNow select one of the following 'formats' for [green]'{source}'[/green]: ",
                choices=basic_source_to_source_type_dict[source],
            )
            # The user is given a list of options that are specific to the parent source they choose earlier (e.g.  bluray --> disc, remux, encode )
            return_source_type = f"{source}_{specific_source_type}"
        else:
            # Right now only HDTV doesn't have any 'specific' variation so this will only run if HDTV is the source
            return_source_type = f"{source}"

    # Well this sucks, we got pretty far this time but since 'auto_mode=true' we can't prompt the user & it probably isn't a great idea to start making assumptions about a media files source,
    # that seems like a good way to get a warning/ban so instead we'll just quit here and let the user know why
    else:
        logging.critical(
            "[MiscellaneousUtils] auto_mode is enabled (no user input) & we can not auto extract the 'source_type'"
        )
        # let the user know the error/issue
        console.print(
            "\nCritical error when trying to extract: 'source_type' (more specific version of 'source', think bluray_remux & just bluray) ",
            style="red bold",
        )
        console.print("Quitting now..")
        # and finally exit since this will affect all trackers we try and upload to, so it makes no sense to try the next tracker
        sys.exit()
    logging.debug(
        f"[MiscellaneousUtils] Source type identified as '{return_source_type}'"
    )
    return return_source_type


def fill_dual_multi_and_commentary(original_language, audio_tracks):
    chinese_variants = ["zh", "cn", "cmn"]
    norwegian_variants = ["no", "nb"]
    commentary = False
    dualaudio, multiaudio = "", ""
    audio_lang_code = set()

    # the below flags indicate whether english tracker and original language tracks are present
    english, original = False, False
    for audio_track in audio_tracks:
        audio_language = audio_track.language

        # checking for commentary tracks
        if "commentary" in (
            audio_track.title.lower() if audio_track.title is not None else ""
        ):
            commentary = True
        else:  # we are not bothered about the commentary language
            audio_lang_code.add(audio_language)

        if original_language != "en" and original_language != "":
            # check for english
            if (
                not english
                and audio_language == "en"
                and "commentary"
                not in (
                    audio_track.title.lower()
                    if audio_track.title is not None
                    else ""
                )
            ):
                english = True

            # check for original
            if not original:
                if (
                    audio_language == original_language
                    and "commentary"
                    not in (
                        audio_track.title.lower()
                        if audio_track.title is not None
                        else ""
                    )
                ):
                    original = True

                # catching chinese and norwegian variants
                if (
                    audio_language in chinese_variants
                    and original_language in chinese_variants
                ):
                    original = True
                elif (
                    audio_language in norwegian_variants
                    and original_language in norwegian_variants
                ):
                    original = True

    if english and original:
        # TODO: what about TrueHD tracks with a compatibility track??
        expected_tracks = 3 if commentary else 2
        if len(audio_tracks) == expected_tracks:  # if there are
            dualaudio = "Dual-Audio"
        else:
            multiaudio = "Multi"

    # for multi audio tag, multiple tracks needs to be present and they should be of different language
    # also if there are only two tracks and one of which is english, then we can treat it as Dual-Audio
    if (
        len(dualaudio) == 0
        and len(audio_lang_code) > 1
        and len(audio_tracks) > 1
    ):
        multiaudio = "Multi"

    return dualaudio, multiaudio, commentary


def detect_anamorphic_video_and_pixel_ratio(video_track):
    pixel_aspect_ratio = 1.000
    try:
        pixel_aspect_ratio = float(
            f"{float(video_track.pixel_aspect_ratio):.3f}"
        )
    except ValueError:
        logging.error(
            "[MiscellaneousUtils] Failed to get proper pixel aspect ratio for detcting anamorphic video"
        )
        logging.info(
            f"[MiscellaneousUtils] Pixel aspect ratio from mediainfo: {video_track.pixel_aspect_ratio}"
        )
        logging.info(
            "[MiscellaneousUtils] Assuming non anamorphic video and proceeding with upload..."
        )

    anamorphic_video = pixel_aspect_ratio != 1.000
    logging.info(
        f"[MiscellaneousUtils] Anamorphic Video :: '{anamorphic_video}' <==> Pixel Aspect Ratio :: '{pixel_aspect_ratio}'"
    )
    return anamorphic_video, pixel_aspect_ratio
