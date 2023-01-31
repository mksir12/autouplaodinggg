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

import glob
import hashlib
import importlib
import json
import logging
import os
import re
import shutil
import subprocess
import time
import unicodedata
from pathlib import Path
from pprint import pformat

import pyfiglet
from dotenv import dotenv_values
from guessit import guessit
from rich.console import Console

import modules.env as Environment
from modules.constants import (
    EXTERNAL_SITE_TEMPLATES_DIR,
    EXTERNAL_TRACKER_ACRONYM_MAPPING,
    SCREENSHOTS_PATH,
    VALIDATED_SITE_TEMPLATES_DIR,
    WORKING_DIR,
)
from modules.torrent_client import Clients, TorrentClientFactory

console = Console()


def get_hash(string):
    hashed = hashlib.new("sha256")
    hashed.update(string.encode())
    return hashed.hexdigest()


def write_cutsom_user_inputs_to_description(
    torrent_info,
    description_file_path,
    config,
    tracker,
    bbcode_line_break,
    debug=False,
):
    # -------- Add custom descriptions to description.txt --------
    if (
        "custom_user_inputs" in torrent_info
        and torrent_info["custom_user_inputs"] is not None
    ):
        # If the user is uploading to multiple sites we don't want to keep appending to the same description.txt file so remove it each time and write clean bbcode to it
        #  (Note, this doesn't delete bbcode_images.txt so you aren't uploading the same images multiple times)
        if os.path.isfile(description_file_path):
            os.remove(description_file_path)

        # we need to make sure that the tracker supports custom description for torrents.
        # If tracker supports custom descriptions, the the tracker config will have the `description_components` key.
        if "description_components" in config:
            logging.debug(
                "[CustomUserInputs] User has provided custom inputs for torrent description"
            )
            # here we iterate through all the custom inputs provided by the user
            # then we check whether this component is supported by the target tracker. If tracker supports it then the `key` will be present in the tracker config.
            with open(description_file_path, "a") as description:
                description_components = config["description_components"]
                logging.debug(
                    f"[CustomUserInputs] Custom Message components configured for tracker {tracker} are {pformat(description_components)}"
                )
                for custom_user_input in torrent_info["custom_user_inputs"]:
                    # getting the component type
                    logging.debug(
                        f"[CustomUserInputs] Custom input data {pformat(custom_user_input)}"
                    )
                    if custom_user_input["key"] not in description_components:
                        logging.debug(
                            "[CustomUserInputs] This type of component is not supported by the tracker. Writing input to description as plain text"
                        )
                        # the provided component is not present in the trackers list. hence we adds this to the description directly (plain text)
                        description.write(custom_user_input["value"])
                    else:
                        # provided component is present in the tracker list, so first we'll format the content to be added to the tracker template
                        input_wrapper_type = description_components[
                            custom_user_input["key"]
                        ]
                        logging.debug(
                            f"[CustomUserInputs] Component wrapper :: `{input_wrapper_type}`"
                        )
                        formatted_value = custom_user_input["value"].replace(
                            "\\n", bbcode_line_break
                        )
                        # next we need to check whether the text component has any title
                        if (
                            "title" in custom_user_input
                            and custom_user_input["title"] is not None
                        ):
                            logging.debug(
                                "[CustomUserInputs] User has provided a title for this component"
                            )
                            # if user has provided title, next we'll make sure that the tracker supports title for the component.
                            if "TITLE_PLACEHOLDER" in input_wrapper_type:
                                logging.debug(
                                    f'[CustomUserInputs] Adding title [{custom_user_input["title"].strip()}] to this component'
                                )
                                input_wrapper_type = input_wrapper_type.replace(
                                    "TITLE_PLACEHOLDER",
                                    custom_user_input["title"].strip(),
                                )
                            else:
                                logging.debug(
                                    f'[CustomUserInputs] Title is not supported for this component {custom_user_input["key"]} in this tracker {tracker}. Skipping title placement'
                                )
                        # in cases where tracker supports title and user hasn't provided any title, we'll just remove the title placeholder
                        # note that the = is intentional. since title would be [spoiler=TITLE]. we need to remove =TITLE
                        # if title has already been repalced the below statement won't do anything
                        input_wrapper_type = input_wrapper_type.replace(
                            "=TITLE_PLACEHOLDER", ""
                        )

                        if debug:  # just for debugging purposes
                            if "][" in input_wrapper_type:
                                logging.debug(
                                    "[CustomUserInputs] ][ is present in the wrapper type"
                                )
                            elif "><" in input_wrapper_type:
                                logging.debug(
                                    "[CustomUserInputs] >< is present in the wrapper type"
                                )
                            else:
                                logging.debug(
                                    "[CustomUserInputs] No special characters present in the wrapper type"
                                )
                            logging.debug(
                                f"[CustomUserInputs] Wrapper type before formatting {input_wrapper_type}"
                            )

                        if "][" in input_wrapper_type:
                            final_formatted_data = input_wrapper_type.replace(
                                "][", f"]{formatted_value}["
                            )
                        elif "><" in input_wrapper_type:
                            final_formatted_data = input_wrapper_type.replace(
                                "><", f">{formatted_value}<"
                            )
                        else:
                            final_formatted_data = formatted_value
                        description.write(final_formatted_data)
                        logging.debug(
                            f"[CustomUserInputs] Formatted value being appended to torrent description {final_formatted_data}"
                        )

                    description.write(bbcode_line_break)
        else:  # else for "description_components" in config
            logging.debug(
                f"[Utils] The tracker {tracker} doesn't support custom descriptions. Skipping custom description placements."
            )


def add_bbcode_images_to_description(
    torrent_info, config, description_file_path, bbcode_line_break
):
    screenshot_type = (
        config["screenshot_type"] if "screenshot_type" in config else None
    )
    if screenshot_type is not None and screenshot_type in torrent_info:
        # Screenshots will be added to description only if no custom screenshot payload method is provided.
        # Possible payload mechanisms for screenshot are 1. bbcode, 2. url, 3. post data
        # TODO implement proper screenshot payload mechanism. [under technical_jargons?????]
        #
        # if custom_user_inputs is already present in torrent info, then the delete operation would have already be done
        # so we just need to append screenshots to the description.txt
        if "custom_user_inputs" not in torrent_info and os.path.isfile(
            description_file_path
        ):
            os.remove(description_file_path)

        # Now open up the correct files and format all the bbcode/tags below
        with open(description_file_path, "a") as description:
            # First add the [center] tags, "Screenshots" header, Size tags etc etc. This only needs to be written once which is why its outside of the 'for loop' below
            description.write(
                f"{bbcode_line_break}[center] ---------------------- [size=22]Screenshots[/size] ---------------------- {bbcode_line_break}{bbcode_line_break}"
            )
            # Now write in the actual screenshot bbcode
            description.write(torrent_info[screenshot_type])
            description.write("[/center]")


def write_uploader_signature_to_description(
    description_file_path, tracker, bbcode_line_break, release_group
):
    # TODO what will happen if custom_user_inputs and bbcode_images are not present
    # will then open throw some errors???
    with open(description_file_path, "a") as description:
        # Finally append the entire thing with some shameless self promotion ;) and some line breaks
        if (
            Environment.get_uploader_signature()
            and len(Environment.get_uploader_signature()) > 0
        ):
            logging.debug(
                "[Utils] User has provided custom uploader signature to use."
            )
            # the user has provided a custom signature to be used. hence we'll use that.
            uploader_signature = Environment.get_uploader_signature()
            logging.debug(
                f"[Utils] User provided signature :: {uploader_signature}"
            )
            if not uploader_signature.startswith(
                "[center]"
            ) and not uploader_signature.endswith("[/center]"):
                uploader_signature = f"[center]{uploader_signature}[/center]"
            uploader_signature = f"{uploader_signature}{bbcode_line_break}[center]Powered by GG-BOT Upload Assistant[/center]"
            description.write(
                f"{bbcode_line_break}{bbcode_line_break}{uploader_signature}"
            )
        else:
            logging.debug(
                "[Utils] User has not provided any custom uploader signature to use. Using default signature"
            )
            if release_group == "DrDooFenShMiRtZ":
                description.write(
                    f'{bbcode_line_break}{bbcode_line_break}[center] Uploaded with [color=red]{"<3" if str(tracker).upper() in ("BHD", "BHDTV") or os.name == "nt" else "❤"}[/color] using GG-BOT Upload Assistantinator[/center]'
                )
            else:
                description.write(
                    f'{bbcode_line_break}{bbcode_line_break}[center] Uploaded with [color=red]{"<3" if str(tracker).upper() in ("BHD", "BHDTV") or os.name == "nt" else "❤"}[/color] using GG-BOT Upload Assistant[/center]'
                )


def has_user_provided_type(user_type):
    if user_type:
        if user_type[0] in ("tv", "movie"):
            logging.info(f"[Utils] Using user provided type {user_type[0]}")
            return True
        else:
            logging.error(
                f"[Utils] User has provided invalid media type as argument {user_type[0]}. Type will be detected dynamically!"
            )
            return False
    else:
        logging.info(
            "[Utils] Type not provided by user. Type will be detected dynamically!"
        )
        return False


def delete_leftover_files(working_folder, file, resume=False):
    """
    Used to remove temporary files (mediainfo.txt, description.txt, screenshots) from the previous upload
    Func is called at the start of each run to make sure there are no mix up with wrong screenshots being uploaded etc.

    Not much significance when using the containerized solution, however if the `temp_upload` folder in container
    is mapped to a docker volume / host path, then clearing would be best. Hence keeping this method.
    """
    # We need these folders to store things like screenshots, .torrent & description files.
    # So create them now if they don't exist
    working_dir = WORKING_DIR.format(base_path=working_folder)
    if Path(working_dir).is_dir():
        # this means that the directory exists
        # If they do already exist then we need to remove any old data from them
        if resume:
            logging.info(
                f"[Utils] Resume flag provided by user. Preserving the contents of the folder: {working_dir}"
            )
        else:
            files = glob.glob(f"{working_dir}*")
            for f in files:
                if os.path.isfile(f):
                    os.remove(f)
                else:
                    shutil.rmtree(f)
            logging.info(
                f"[Utils] Deleted the contents of the folder: {working_dir}"
            )
    else:
        os.mkdir(working_dir)

    if Environment.is_readable_temp_data_needed():
        files = (
            f"{file}/".replace("//", "/")
            .strip()
            .replace(" ", ".")
            .replace(":", ".")
            .replace("'", "")
            .split("/")[:-1]
        )
        files.reverse()
        unique_hash = files[0]
    else:
        unique_hash = get_hash(file)
    unique_hash = f"{unique_hash}/"

    if not Path(f"{working_dir}{unique_hash}").is_dir():
        os.mkdir(f"{working_dir}{unique_hash}")

    if not Path(
        SCREENSHOTS_PATH.format(
            base_path=working_folder, sub_folder=unique_hash
        )
    ).is_dir():
        os.mkdir(
            SCREENSHOTS_PATH.format(
                base_path=working_folder, sub_folder=unique_hash
            )
        )

    logging.info(f"[Utils] Created subfolder {unique_hash} for file {file}")
    return unique_hash


def write_file_contents_to_log_as_debug(file_path):
    """
    Method reads and writes the contents of the provided `file_path` to the log as debug lines.
    note that the method doesn't check for debug mode or not, those checks needs to be done by the caller
    """
    with open(file_path) as file_contents:
        lines = file_contents.readlines()
        _ = [logging.debug(line.replace("\\n", "").strip()) for line in lines]


def perform_guessit_on_filename(file_name):
    guessit_start_time = time.perf_counter()

    if file_name.endswith("/"):
        file_name_split = file_name[0 : len(file_name) - 1].split("/")
    else:
        file_name_split = file_name.split("/")
    file_name = file_name_split[len(file_name_split) - 1]

    guess_it_result = guessit(file_name)
    guessit_end_time = time.perf_counter()
    logging.debug(
        f"[Utils] Time taken for guessit regex operations :: {guessit_end_time - guessit_start_time}"
    )
    logging.debug(
        "::::::::::::::::::::::::::::: GuessIt output result :::::::::::::::::::::::::::::"
    )
    logging.debug(f"\n{pformat(guess_it_result)}")
    return guess_it_result


def check_for_dir_and_extract_rars(file_path):
    """
    Return values -> Status, Actual File Path

    Status indicates whether the file/folder validation was performed successfully.
    I case of any errors, status will be false and the upload of that file can be skipped
    """
    # If the path the user specified is a folder with .rar files in it then we unpack the video file & set the torrent_info key equal to the extracted video file
    if Path(file_path).is_dir():
        logging.info(f"[Utils] User wants to upload a folder: {file_path}")

        # Now we check to see if the dir contains rar files
        rar_file = glob.glob(f"{os.path.join(file_path, '')}*rar")
        if rar_file:
            logging.info(
                f"[Utils] '{file_path}' is a .rar archive, extracting now..."
            )
            logging.info(f"[Utils] Rar file: {rar_file[0]}")

            # Now verify that unrar is installed
            unrar_sys_package = "/usr/bin/unrar"
            if os.path.isfile(unrar_sys_package):
                logging.info(
                    "[Utils] Found 'unrar' system package, Using it to extract the video file now"
                )

                # run the system package unrar and save the extracted file to its parent dir
                subprocess.run([unrar_sys_package, "e", rar_file[0], file_path])
                logging.debug(
                    f"[Utils] Successfully extracted file : {rar_file[0]}"
                )

                # This is how we identify which file we just extracted (Last modified)
                list_of_files = glob.glob(f"{os.path.join(file_path, '')}*")
                latest_file = max(list_of_files, key=os.path.getctime)

                logging.info(
                    f"[Utils] Using the extracted {latest_file} for further processing"
                )
                # the value for 'upload_media' with the path to the video file we just extracted
                return True, latest_file
            else:
                # If the user doesn't have unrar installed then we let them know here and move on to the next file (if exists)
                console.print(
                    "unrar is not installed, Unable to extract the rar archinve\n",
                    style="bold red",
                )
                logging.critical(
                    "[Utils] `unrar` is not installed, Unable to extract rar archive"
                )
                logging.info(
                    '[Utils] Perhaps first try "sudo apt-get install unrar" then run this script again'
                )
                # Skip this entire 'file upload' & move onto the next (if exists)
                return False, file_path
        return True, file_path
    else:
        logging.info(f"[Utils] Uploading the following file: {file_path}")
        return True, file_path


def prepare_and_validate_tracker_api_keys_dict(api_keys_file_path):
    """
    Reads the apis keys from environment and returns as a dictionary.

    Method will read the available api_keys from the `api_keys_file_path`, and for each of the mentioned keys, the value will be
    read from the environment variables. This method also checks whether the TMDB api key has been provided or not.

    In cases where the TMDB api key has not been configured, the method will raise an `AssertionError`.
    """
    api_keys = json.load(open(api_keys_file_path))
    api_keys_dict = dict()
    for value in api_keys:
        api_keys_dict[value] = Environment.get_property_or_default(
            value.upper(), ""
        )

    # Make sure the TMDB API is provided [Mandatory Property]
    try:
        if len(api_keys_dict["tmdb_api_key"]) == 0:
            raise AssertionError("TMDB API key is required")
    except AssertionError as err:  # Log AssertionError in the logfile and quit here
        logging.exception("TMDB API Key is required")
        raise err

    return api_keys_dict


def validate_env_file(sample_env_location):
    sample_env_keys = dotenv_values(sample_env_location).keys()
    # validating env file with expected keys from sample file
    for key in sample_env_keys:
        if Environment.get_property_or_default(key, None) is None:
            console.print(
                f"Outdated config.env file. Variable [red][bold]{key}[/bold][/red] is missing.",
                style="blue",
            )
            logging.error(
                f"Outdated config.env file. Variable {key} is missing."
            )


def get_and_validate_configured_trackers(
    trackers, all_trackers, api_keys_dict, all_trackers_list
):
    upload_to_trackers = []
    # small sanity check
    if trackers is not None and len(trackers) < 1:
        trackers = None

    tracker_list = all_trackers_list
    if all_trackers:  # user wants to upload to all the trackers possible
        logging.info(
            f"[Utils] User has chosen to upload to add possible trackers: {tracker_list}"
        )
    else:
        logging.info(
            "[Utils] Attempting check and validate and default trackers configured"
        )
        tracker_list = Environment.get_default_trackers_list(default="")
        if len(tracker_list) > 0:
            tracker_list = [x.strip() for x in tracker_list.split(",")]

    for tracker in trackers or tracker_list or []:
        tracker = str(tracker)
        if f"{tracker.lower()}_api_key" in api_keys_dict:
            # Make sure that an API key is set for that site
            if len(api_keys_dict[f"{tracker.lower()}_api_key"]) <= 1:
                continue
            if tracker.upper() not in upload_to_trackers:
                upload_to_trackers.append(tracker.upper())
        else:
            logging.error(
                f"[Utils] We can't upload to '{tracker}' because that site is not supported"
            )

    if "PTP" in upload_to_trackers:
        logging.info(
            "[Utils] User wants to upload to PTP. Checking whether ptpimg has been configured or not"
        )
        if not _can_upload_to_ptp():
            logging.error(
                "[Main] Cannot upload to 'PTP' since 'ptpimg' is not enabled / configured properly."
            )
            upload_to_trackers.remove("PTP")

    # Make sure that the user provides at least 1 valid tracker we can upload to
    # if len(upload_to_trackers) == 0 that means that the user either
    #   1. didn't provide any site at all,
    #   2. the site is not supported, or
    #   3. the API key isn't provided
    if len(upload_to_trackers) < 1:
        logging.exception(
            "[Utils] No valid trackers specified for upload destination (e.g. BHD, BLU, ACM)"
        )
        raise AssertionError(
            "Provide at least 1 tracker we can upload to (e.g. BHD, BLU, ACM)"
        )

    logging.debug(f"[Utils] Trackers selected by bot: {upload_to_trackers}")
    return upload_to_trackers


def _get_client_translated_path(torrent_info):
    # before we can upload the torrent to the client, we might need to do some path translations.
    # suppose, we are trying to upload a movie with the user provided path (-p argument) as
    """/home/user/data/movie_name/movie.mkv"""
    # when we add to client and sets the save location, it needs to be set as '/home/user/data/movie_name/'
    # if the user is running the torrent client in a docker container, or the uploader is running in a docker container 😉,
    # the paths accessible to the torrent client will be different. It could be ...
    """ /media/downloads/movie_name/movie.mkv """
    # In these cases we may need to perform path translations.
    """
        From: /home/user/data/movie_name/movie.mkv
        To: /media/downloads/movie_name/movie.mkv
    """

    if Environment.is_translation_needed():
        logging.info(
            '[Utils] Translating paths... ("translation_needed" flag set to True in config.env) '
        )

        # Just in case the user didn't end the path with a forward slash...
        uploader_accessible_path = f"{Environment.get_uploader_accessible_path('__MISCONFIGURED_PATH__')}/".replace(
            "//", "/"
        )
        client_accessible_path = f"{Environment.get_client_accessible_path('__MISCONFIGURED_PATH__')}/".replace(
            "//", "/"
        )

        if "__MISCONFIGURED_PATH__/" in [
            client_accessible_path,
            uploader_accessible_path,
        ]:
            logging.error(
                "[Utils] User have enabled translation, but haven't provided the translation paths. Stopping cross-seeding..."
            )
            return False

        # log the changes
        logging.info(f'[Utils] Uploader path: {torrent_info["upload_media"]}')
        logging.info(
            f'[Utils] Translated path: {torrent_info["upload_media"].replace(uploader_accessible_path, client_accessible_path)}'
        )

        # Now we replace the remote path with the system one
        torrent_info["upload_media"] = torrent_info["upload_media"].replace(
            uploader_accessible_path, client_accessible_path
        )
    return f'{torrent_info["upload_media"]}/'.replace("//", "/")


def _post_mode_cross_seed(
    torrent_client, torrent_info, working_folder, tracker, allow_multiple_files
):
    # TODO check and validate connection to torrent client.
    # or should this be done at the start?? Just because torrent client connection cannot be established
    # doesn't mean that we cannot do the upload. Maybe show a warning at the start that cross-seeding is enabled and
    # client is not or misconfigured ???
    # we perform cross-seeding only if tracker upload was successful
    if (
        f"{tracker}_upload_status" in torrent_info
        and torrent_info[f"{tracker}_upload_status"] == True
    ):
        logging.info(
            "[Utils] Attempting to upload dot torrent to configured torrent client."
        )
        logging.info(
            f"[Utils] `upload_media` :: '{torrent_info['upload_media']}' `client_path` :: '{torrent_info['client_path']}' "
        )
        console.print(f"\nFile Path: \t{torrent_info['upload_media']}")
        console.print(f"Client Save Path: \t{torrent_info['client_path']}")

        if (
            allow_multiple_files == False
            and "raw_video_file" in torrent_info
            and torrent_info["type"] == "movie"
        ):
            logging.info(
                f'[Utils] `raw_video_file` :: {torrent_info["raw_video_file"]}'
            )
            save_path = torrent_info["client_path"]
        else:
            save_path = torrent_info["client_path"].replace(
                f'/{torrent_info["raw_file_name"]}', ""
            )

        # getting the proper .torrent file for the provided tracker
        torrent_file = None
        for file in glob.glob(
            f"{WORKING_DIR.format(base_path=working_folder)}{torrent_info['working_folder']}"
            + r"/*.torrent"
        ):
            if f"/{tracker}-" in file:
                torrent_file = file
                console.print(
                    f"Identified .torrent file \t'{file}' for tracker as '{tracker}'"
                )
                logging.info(
                    f"[Utils] Identified .torrent file '{file}' for tracker '{tracker}'"
                )

        if torrent_file is not None:
            res = torrent_client.upload_torrent(
                torrent=torrent_file,
                save_path=save_path,
                use_auto_torrent_management=False,
                is_skip_checking=True,
            )
        else:
            logging.error(
                f"[Utils] Could not identify the .torrent file for tracker '{tracker}'"
            )
            console.print(
                f"⚠️ ☠️ ⚠️ [bold red]Could not identify the .torrent file for tracker [green]{tracker}[/green]."
                + " [/bold red] Please seed this tracker's torrent manually. ⚠️ ☠️ ⚠️"
            )
            res = None
        return res if res is not None else True
    return False


def _post_mode_watch_folder(torrent_info, working_folder):
    move_locations = {
        "torrent": f"{Environment.get_dot_torrent_move_location()}",
        "media": f"{Environment.get_media_move_location()}",
    }
    logging.debug(
        f"[Utils] Move locations configured by user :: {move_locations}"
    )
    torrent_info["post_processing_complete"] = True

    console.print(
        f"Torrent move location :: [bold green]{move_locations['torrent']}[/bold green]"
    )
    console.print(
        f"Media move location :: [bold green]{move_locations['media']}[/bold green]"
    )

    for move_location_key, move_location_value in move_locations.items():
        # If the user supplied a path & it exists we proceed
        if len(move_location_value) == 0:
            logging.debug(
                f"[Utils] Move location not configured for {move_location_key}"
            )
            continue
        if os.path.exists(move_location_value):
            logging.info(f"[Utils] The move path {move_location_value} exists")

            if move_location_key == "torrent":
                sub_folder = "/"
                if Environment.is_type_based_move_enabled():
                    sub_folder = sub_folder + torrent_info["type"] + "/"
                    # os.makedirs(os.path.dirname(move_locations["torrent"] + sub_folder), exist_ok=True)
                    if os.path.exists(
                        f"{move_locations['torrent']}{sub_folder}"
                    ):
                        logging.info(
                            f"[Utils] Sub location '{move_locations['torrent']}{sub_folder}' exists."
                        )
                    else:
                        logging.info(
                            f"[Utils] Creating Sub location '{move_locations['torrent']}{sub_folder}'."
                        )
                        Path(f"{move_locations['torrent']}{sub_folder}").mkdir(
                            parents=True, exist_ok=True
                        )
                # The user might have upload to a few sites so we need to move all files that end with .torrent to the new location
                list_dot_torrent_files = glob.glob(
                    f"{WORKING_DIR.format(base_path=working_folder)}{torrent_info['working_folder']}*.torrent"
                )
                for dot_torrent_file in list_dot_torrent_files:
                    # Move each .torrent file we find into the directory the user specified
                    logging.debug(
                        f'[Utils] Moving {dot_torrent_file} to {move_locations["torrent"]}{sub_folder}'
                    )
                    try:
                        shutil.move(
                            dot_torrent_file,
                            f'{move_locations["torrent"]}{sub_folder}',
                        )
                    except Exception:
                        logging.exception(
                            f'[Utils] Cannot move torrent {dot_torrent_file} to location {move_locations["torrent"] + sub_folder}'
                        )
                        console.print(
                            f"[bold red]Failed to move [green]{dot_torrent_file}[/green] to location [green]{move_locations['torrent'] + sub_folder}[/green] [/bold red]"
                        )

            # Media files are moved instead of copied so we need to make sure they don't already exist in the path the user provides
            if move_location_key == "media":
                if (
                    str(f"{Path(torrent_info['upload_media']).parent}/")
                    == move_location_value
                ):
                    console.print(
                        f'\nError, {torrent_info["upload_media"]} is already in the move location you specified: "{move_location_value}"\n',
                        style="red",
                        highlight=False,
                    )
                    logging.error(
                        f"[Utils] {torrent_info['upload_media']} is already in {move_location_value}, Not moving the media"
                    )
                else:
                    sub_folder = "/"
                    if Environment.is_type_based_move_enabled():
                        sub_folder = sub_folder + torrent_info["type"] + "/"
                        move_location_value = move_location_value + sub_folder
                        os.makedirs(
                            os.path.dirname(move_location_value), exist_ok=True
                        )
                    logging.info(
                        f"[Utils] Moving {torrent_info['upload_media']} to {move_location_value }"
                    )
                    try:
                        shutil.move(
                            torrent_info["upload_media"], move_location_value
                        )
                    except Exception:
                        logging.exception(
                            f"[Utils] Cannot move media {torrent_info['upload_media']} to location {move_location_value}"
                        )
                        console.print(
                            f"[bold red]Failed to move [green]{torrent_info['upload_media']}[/green] to location [green]{move_location_value}[/green] [/bold red]"
                        )
        else:
            logging.error(
                f"[Utils] Move path doesn't exist for {move_location_key} as {move_location_value}"
            )
            console.print(
                f"[bold red]Location [green]{move_location_value}[/green] doesn't exit. Cannot move [green]{move_location_key}[/green][/bold red]"
            )


def get_torrent_client_if_needed():
    logging.debug(
        f"[Utils] enable_post_processing {Environment.is_post_processing_needed()}"
    )
    logging.debug(
        f"[Utils] post_processing_mode {Environment.get_post_processing_mode()}"
    )
    if (
        Environment.is_post_processing_needed()
        and Environment.get_post_processing_mode() == "CROSS_SEED"
    ):
        # getting an instance of the torrent client factory
        torrent_client_factory = TorrentClientFactory()
        # creating the torrent client using the factory based on the users configuration
        torrent_client = torrent_client_factory.create(
            Clients[Environment.get_client_type()]
        )
        # checking whether the torrent client connection has been created successfully or not
        torrent_client.hello()
        return torrent_client
    else:
        logging.info("[Utils] Skipping torrent client creation...")
        return None


def perform_post_processing(
    torrent_info,
    torrent_client,
    working_folder,
    tracker,
    allow_multiple_files=False,
):
    # After we finish uploading, we can add all the dot torrent files to a torrent client to start seeding immediately.
    # This post processing step can be enabled or disabled based on the users configuration
    if Environment.is_post_processing_needed():
        # When running in a bare meta, there is a chance for the user to provide relative paths.
        """data/movie_name/movie.mkv"""
        # the way to identify a relative path is to check whether the `upload_media` starts with a `/`
        if not torrent_info["upload_media"].startswith("/"):
            torrent_info[
                "upload_media"
            ] = f'{working_folder}/{torrent_info["upload_media"]}'
            logging.info(
                f'[Utils] User has provided relative path. Converting to absolute path for torrent client :: "{torrent_info["upload_media"]}"'
            )

        # apply path translations and getting translated paths
        translated_path = _get_client_translated_path(torrent_info)
        if translated_path == False:
            return False
        torrent_info["client_path"] = translated_path

        post_processing_mode = Environment.get_post_processing_mode()
        if post_processing_mode == "CROSS_SEED":
            console.print(
                "[bold] 🌱 Detected [red]Cross Seed[/red] as the post processing mode. 🌱 [/bold]",
                justify="center",
            )
            return _post_mode_cross_seed(
                torrent_client,
                torrent_info,
                working_folder,
                tracker,
                allow_multiple_files,
            )
        elif post_processing_mode == "WATCH_FOLDER":
            console.print(
                "[bold] ⌚ Detected [red]Watch Folder[/red] as the post processing mode. ⌚ [/bold]",
                justify="center",
            )
            return _post_mode_watch_folder(torrent_info, working_folder)
        else:
            logging.error(
                f"[Utils] Post processing is enabled, but invalid mode provided: '{post_processing_mode}'"
            )
            return False
    else:
        logging.info(
            "[Utils] No process processing steps needed, as per users configuration"
        )
        console.print(
            "\n[bold magenta] 😞  Oops!!. No post processing steps have been configured. 😞 [/bold magenta]",
            justify="center",
        )
        return False


def display_banner(mode):
    gg_bot = pyfiglet.figlet_format("GG-BOT", font="banner3-D")
    mode = pyfiglet.figlet_format(mode, font="banner3-D", width=210)

    console.print(f"[bold green]{gg_bot}[/bold green]", justify="center")
    console.print(
        f"[bold blue]{mode}[/bold blue]", justify="center", style="#38ACEC"
    )
    return True


def sanitize_release_group_from_guessit(torrent_info):
    # setting NOGROUP as group if the release_group cannot be identified from guessit
    if (
        "release_group" in torrent_info
        and len(torrent_info["release_group"]) > 0
    ):
        logging.debug(
            f"[Utils] Release group identified by guessit: '{torrent_info['release_group']}'"
        )
        # sometimes, guessit identifies wrong release groups. So we just do another sanity check just to ensure that the release group
        # provided by guessit is correct.
        # removing the trailing / if present
        upload_media = (
            torrent_info["upload_media"][:-1]
            if torrent_info["upload_media"].endswith("/")
            else torrent_info["upload_media"]
        )
        # if title has spaces in it, then we remove them. [...H.264 - RELEASE_GROUP  ==> ...H.264-RELEASE_GROUP]
        upload_media = upload_media.replace(" ", "")
        temp_upload_media = upload_media.replace(".mkv", "").replace(".mp4", "")
        if temp_upload_media.endswith(f"{torrent_info['release_group']}"):
            # well the release group identified by guessit seems correct.
            if torrent_info["release_group"].startswith("X-"):
                # a special case where title ends with DTS-X-GROUP and guess it extracts release group as X-GROUP
                logging.info(
                    f'[Utils] Guessit identified release group as \'{torrent_info["release_group"]}\'. Since this starts with X- (probably from DTS-X-RELEASE_GROUP), overwriting release group as \'{torrent_info["release_group"][2:]}\''
                )
                return torrent_info["release_group"][2:]
            elif torrent_info["release_group"].startswith("AV1-"):
                # TODO: remove this condition once guessit identifies this pattern properly
                # a special case where title ends with AV1-GROUP and guess it extracts release group as AV1-GROUP
                logging.info(
                    f'[Utils] Guessit identified release group as \'{torrent_info["release_group"]}\'. Since this starts with AV1- (probably from AV1-RELEASE_GROUP), overwriting release group as \'{torrent_info["release_group"][4:]}\''
                )
                return torrent_info["release_group"][4:]
            elif torrent_info["release_group"].endswith("k-DDH"):
                # TODO: remove this condition once guessit identifies this pattern properly
                # these guys adds audio bits to title and this messes with guessit result
                logging.info("[Utils] Applying hotfix for 'DDH' release group.")
                return "DDH"
        else:
            logging.debug(
                "[Utils] Improper release group identified by guessit. Setting release group as NOGROUP"
            )
            return "NOGROUP"
    else:
        logging.debug(
            "[Utils] Release group could not be identified by guessit. Setting release group as NOGROUP"
        )
        return "NOGROUP"
    return torrent_info["release_group"]


def load_custom_actions(full_method_string):
    """
    dynamically load a method from a string
    """

    method_data = full_method_string.split(".")
    module_path = ".".join(method_data[:-1])
    method_string = method_data[-1]

    module = importlib.import_module(module_path)
    # Finally, we retrieve the Class
    return getattr(module, method_string)


def prepare_headers_for_tracker(technical_jargons, search_site, tracker_api):
    if technical_jargons["authentication_mode"] == "API_KEY":
        return None

    if technical_jargons["authentication_mode"] == "BEARER":
        logging.info(
            f"[DupeCheck] Using Bearer Token authentication method for tracker {search_site}"
        )
        return {"Authorization": f"Bearer {tracker_api}"}

    if technical_jargons["authentication_mode"] == "HEADER":
        if len(technical_jargons["headers"]) > 0:
            headers = {}
            logging.info(
                f"[DupeCheck] Using Header based authentication method for tracker {search_site}"
            )
            for header in technical_jargons["headers"]:
                logging.info(
                    f"[DupeCheck] Adding header '{header['key']}' to request"
                )
                headers[header["key"]] = (
                    tracker_api
                    if header["value"] == "API_KEY"
                    else Environment.get_property_or_default(
                        f"{search_site}_{header['value']}", ""
                    )
                )
            return headers
        else:
            logging.fatal(
                f"[DupeCheck] Header based authentication cannot be done without `header_key` for tracker {search_site}."
            )
    elif technical_jargons["authentication_mode"] == "COOKIE":
        logging.fatal(
            "[DupeCheck] Cookie based authentication is not supported yet."
        )

    return None


def _can_upload_to_ptp():
    # to upload to ptp the image host ptpimg needs to be configured and enabled.
    enabled_img_host_num_loop = 0
    found_ptpimg = False
    # checking whether user has enabled ptpimg in img_host_X env variable
    while (
        Environment.get_image_host_by_priority(enabled_img_host_num_loop + 1)
        is not None
    ):
        if (
            Environment.get_image_host_by_priority(
                enabled_img_host_num_loop + 1
            )
            == "ptpimg"
        ):
            found_ptpimg = True
            break
        enabled_img_host_num_loop += 1

    # if user has not configured ptpimg, then we can say with confidence that user cannot upload to ptp
    if not found_ptpimg:
        return False

    # now lets check whether user has provided the ptpimg api key
    if (
        Environment.get_image_host_api_key("ptpimg") is None
        or len(Environment.get_image_host_api_key("ptpimg")) <= 0
    ):
        return False

    return True


def validate_templates_in_path(template_dir, template_validator):
    valid_templates = list(
        map(
            lambda entry: entry.name.replace(".json", ""),
            filter(
                template_validator.is_valid,  # validating the template against the site_templates json schema.
                filter(
                    lambda entry: entry.is_file()
                    and entry.suffix
                    == ".json",  # we are only interested in .json files
                    Path(template_dir).glob("**/*"),
                ),  # getting all the files in the provided directory
            ),
        )
    )
    return valid_templates


def copy_template(valid_templates, source_dir, target_dir):
    # creating the target dir if it doesn't exist
    Path(target_dir).mkdir(parents=True, exist_ok=True)
    for template in valid_templates:
        # if a template already exists, it'll be overwritten.
        shutil.copy(
            str(Path(f"{source_dir}{template}.json")),
            str(Path(f"{target_dir}{template}.json")),
        )


def validate_and_load_external_templates(template_validator, working_folder):
    """
    The first this we need to do is check whether there are any external templates available.
    If there are some custom templates, we'll validate them using the `schema/site_template_schema.json` file.

    If there are any validation errors, then we log them to file and display it to the user via console.

    If there are any external templates that pass the validations, then we need to check whether the environment variables
    have been set or not.
    THe api keys and the corresponding values need to be saved in `api_keys_dict`.

    If api key validations are also successful, then we need to copy those templates to VALIDATED_SITE_TEMPLATES_DIR
    and we return the value for VALIDATED_SITE_TEMPLATES_DIR

    Before we copy we need to ensure that the VALIDATED_SITE_TEMPLATES_DIR exists and all the templates in that folder has been deleted

    """
    external_templates_dir = EXTERNAL_SITE_TEMPLATES_DIR.format(
        base_path=working_folder
    )
    external_trackers_acronym = EXTERNAL_TRACKER_ACRONYM_MAPPING.format(
        base_path=working_folder
    )

    # checking whether the external template directory is available or not
    if not Path(external_templates_dir).is_dir():
        logging.error(
            "[Utils] User wants to load external templates, but external templates folder is not available."
        )
        return [], {}, {}

    if not Path(external_trackers_acronym).is_file():
        logging.error(
            "[Utils] User wants to load external templates, but external templates acronym mapping is not available."
        )
        return [], {}, {}

    # counting the total number of templates in the external folder.
    total_number_templates = len(
        list(
            filter(
                lambda entry: entry.is_file() and entry.suffix == ".json",
                Path(external_templates_dir).glob("**/*"),
            )
        )
    )

    if total_number_templates == 0:
        logging.error(
            "[Utils] User wants to load external templates, but couldn't find any site tempalates."
        )
        return [], {}, {}

    valid_templates = []
    has_failed = False
    # getting all the files in the external template directory
    # here we are not going to reuse method `validate_templates_in_path` for logging purposes
    for entry in Path(external_templates_dir).glob("**/*"):
        if (
            entry.is_file() and entry.suffix == ".json"
        ):  # we are only interested in .json files
            logging.info(f"[Utils] Validating custom template: {entry.name}")
            # First lets check whether user is trying to override the configs on already available templates
            if template_validator.is_valid(
                entry
            ):  # validating the external template against the site_templates json schema.
                # TODO: should users be allowed to override the configs in built-in templates ???
                # TODO: prevent users from overriding the config of built-in templates
                valid_templates.append(entry.name.replace(".json", ""))
            else:
                has_failed = True
                logging.error(
                    f"[Utils] Template validation failed for file: {entry.name}"
                )
                console.print(
                    f"[cyan bold] ❌ Validation failed for template: {entry.name} [/cyan bold]"
                )

    if len(valid_templates) > 0:
        if has_failed:
            console.print(
                "Please see log for more details regarding template validaion failures..."
            )

        # now that we identified that the template is valid, we need to ensure that the user has provided
        # valid configs for tracker name -> acronym mapping and that the api key is available in env.
        tracker_to_acronym = json.load(open(external_trackers_acronym))
        for tracker in valid_templates:
            if tracker not in tracker_to_acronym:
                valid_templates.remove(tracker)
                logging.error(
                    f"[Utils] A valid template tracker {tracker} doesn't have a valid tracker->acronym mapping provided. Ignoring this template..."
                )

        # now we have valid template and a proper acronym.
        # now lets ensure that the api key and announce url have been set properly in environment variables.
        api_key_dict = {}
        for tracker in valid_templates:
            api_key = Environment.get_property_or_default(
                f"{tracker_to_acronym[tracker].upper()}_API_KEY",
                "INVALID_API_KEY",
            )
            if api_key == "INVALID_API_KEY":
                valid_templates.remove(tracker)
                logging.error(
                    f"[Utils] A valid template tracker {tracker} doesn't have its api key available in environment. Ignoring this template..."
                )
            else:
                api_key_dict[f"{tracker_to_acronym[tracker]}_api_key"] = api_key

        temp_template_dir = VALIDATED_SITE_TEMPLATES_DIR.format(
            base_path=working_folder
        )
        # once we have got some valid templates, we need to copy them to a temporary working directory.
        copy_template(
            valid_templates, external_templates_dir, temp_template_dir
        )
        return (
            valid_templates,
            api_key_dict,
            {v: k for k, v in tracker_to_acronym.items()},
        )
    else:
        return [], {}, {}


def add_argument_tags(argument_tags):
    logging.info(f"[Utils] User provided tags from arguments: {argument_tags}")
    return (
        None
        if argument_tags is None or len(argument_tags) == 0
        else sorted(list(set(argument_tags)))
    )


def normalize_for_system_path(file_path: str) -> str:
    file_path = (
        unicodedata.normalize("NFKD", str(file_path))
        .encode("ascii", "ignore")
        .decode("ascii")
    )
    return re.sub(
        r"[-\s]+", "_", re.sub(r"[^\w\s-]", "", file_path.lower())
    ).strip("__")
