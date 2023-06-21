# GG Bot Upload Assistant
# Copyright (C) 2023  Noob Master669

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
import os
import pickle
from json import JSONDecodeError
from pprint import pformat
from typing import Dict, List, Tuple

import requests
from rich import box
from rich.prompt import Prompt
from rich.table import Table

import utilities.utils as utils


class GGBotTrackerUploader:
    def __init__(
        self,
        *,
        logger,
        tracker,
        uploader_config,
        tracker_settings,
        torrent_info,
        api_keys_dict,
        site_templates_path,
        auto_mode,
        console,
        dry_run,
        acronym_to_tracker,
    ):
        self.logger = logger
        self.tracker = tracker
        self.uploader_config = uploader_config
        self.torrent_info = torrent_info
        self.auto_mode = auto_mode
        self.console = console
        self.dry_run = dry_run
        self.upload_response = None
        self.tracker_settings = tracker_settings
        self.tracker_config = self._load_tracker_config(
            tracker=tracker,
            site_templates_path=site_templates_path,
            acronym_to_tracker=acronym_to_tracker,
        )
        self.tracker_api_key = self._get_tracker_api_key(
            tracker=tracker, api_keys_dict=api_keys_dict
        )

    @staticmethod
    def _load_tracker_config(
        *, tracker, site_templates_path, acronym_to_tracker
    ):
        return json.load(
            open(
                site_templates_path
                + str(acronym_to_tracker.get(str(tracker).lower()))
                + ".json",
                encoding="utf-8",
            )
        )

    @staticmethod
    def _get_tracker_api_key(*, tracker: str, api_keys_dict: Dict) -> str:
        return api_keys_dict[f"{str(tracker).lower()}_api_key"]

    def _log_tracker_settings(self):
        self.logger.debug(
            "::::::::::::::::::::::::::::: Tracker settings that will be used for creating payload "
            "::::::::::::::::::::::::::::: "
        )
        self.logger.debug(f"\n{pformat(self.tracker_settings)}")

    def _log_tracker_payload(self, *, url_masked, payload, files):
        self.logger.debug(
            "::::::::::::::::::::::::::::: Tracker Payload :::::::::::::::::::::::::::::"
        )
        self.logger.debug(f"\n{pformat(payload)}")
        self.logger.fatal(
            f"[TrackerUpload] URL: {url_masked} \n Data: {payload} \n Files: {files}"
        )

    def _get_headers_for_tracker(self):
        if (
            self.tracker_config["technical_jargons"]["authentication_mode"]
            == "API_KEY"
        ):
            self.logger.info(
                f"Tracker {self.tracker} uses api key based auth. No need for headers..."
            )
            return None

        if (
            self.tracker_config["technical_jargons"]["authentication_mode"]
            == "BEARER"
        ):
            self.logger.info(
                f"Using Bearer Token authentication method for tracker {self.tracker}"
            )
            return {"Authorization": f"Bearer {self.tracker_api_key}"}

        if (
            self.tracker_config["technical_jargons"]["authentication_mode"]
            == "HEADER"
        ):
            if len(self.tracker_config["technical_jargons"]["headers"]) == 0:
                self.logger.fatal(
                    f"[TrackerUpload] Header based authentication cannot be done without `header_key`"
                    f" for tracker {self.tracker}. "
                )
                return None

            headers = {}
            self.logger.info(
                f"[TrackerUpload] Using Header based authentication method for tracker {self.tracker}"
            )
            for header in self.tracker_config["technical_jargons"]["headers"]:
                self.logger.info(
                    f"[TrackerUpload] Adding header '{header['key']}' to request"
                )
                headers[header["key"]] = (
                    self.tracker_api_key
                    if header["value"] == "API_KEY"
                    else self.uploader_config.get_config(
                        f"{self.tracker}_{header['value']}", ""
                    )
                )
            return headers

    def _initialize_tracker_payload(self) -> Dict:
        if (
            self.tracker_config["technical_jargons"]["authentication_mode"]
            == "API_KEY_PAYLOAD"
        ):
            return {
                self.tracker_config["technical_jargons"][
                    "auth_payload_key"
                ]: self.tracker_api_key
            }
        return {}

    def _initialize_requests_orchestrator(self):
        if (
            self.tracker_config["technical_jargons"]["authentication_mode"]
            != "COOKIE"
        ):
            return requests

        self.logger.info(
            "[TrackerUpload] User wants to use cookie based auth for tracker."
        )

        if (
            self.tracker_config["technical_jargons"]["cookie"]["provider"]
            != "custom_action"
        ):
            # TODO add support for cookie based authentication
            self.logger.fatal(
                "[TrackerUpload] Cookie based authentication is not supported as for now."
            )
            return requests

        self.logger.info(
            f'[TrackerUpload] Cookie Provider: [{self.tracker_config["technical_jargons"]["cookie"]["provider"]}]'
            f' => [{self.tracker_config["technical_jargons"]["cookie"]["data"]}]'
        )
        self.logger.info("[TrackerUpload] Loading custom action to get cookie")
        requests_orchestrator = requests.Session()
        custom_action = utils.load_custom_actions(
            self.tracker_config["technical_jargons"]["cookie"]["data"]
        )
        cookie_file = custom_action(
            self.torrent_info, self.tracker_settings, self.uploader_config
        )

        self.logger.info("[TrackerUpload] Setting cookie to session")
        # here we are storing the session on the requests_orchestrator object
        requests_orchestrator.cookies.update(
            pickle.load(open(cookie_file, "rb"))
        )
        return requests_orchestrator

    def _get_settings_type(self, setting):
        return (
            "Required"
            if setting in self.tracker_config["Required"]
            else "Optional"
            if setting in self.tracker_config["Optional"]
            else "Default"
        )

    def _prepare_payloads_for_upload(self) -> Tuple[List, Dict, Dict]:
        files = []
        display_files = {}
        payload = self._initialize_tracker_payload()

        for key, val in self.tracker_settings.items():
            req_opt = self._get_settings_type(key)

            # keys in tracker settings that doesn't belong to tracker template are ignored
            if key not in self.tracker_config[req_opt]:
                continue

            # ---------------- Special Payload Data Formats ----------------
            # setting file to tracker payload
            if str(self.tracker_config[req_opt][key]) == "file":
                if os.path.isfile(self.tracker_settings[key]):
                    post_file = f"{key}", open(self.tracker_settings[key], "rb")
                    files.append(post_file)
                    display_files[key] = self.tracker_settings[key]
                else:
                    self.logger.critical(
                        f"[TrackerUpload] The file/path `{self.tracker_settings[key]}` "
                        f"for key {req_opt} does not exist!"
                    )
                continue

            # adding multiple files as an array to tracker payload
            if str(self.tracker_config[req_opt][key]) == "file|array":
                if os.path.isfile(self.tracker_settings[key]):
                    with open(self.tracker_settings[key]) as file_data:
                        for line in file_data.readlines():
                            post_file = f"{key}[]", open(line.strip(), "rb")
                            files.append(post_file)
                            display_files[key] = self.tracker_settings[key]
                else:
                    self.logger.critical(
                        f"[TrackerUpload] The file/path `{self.tracker_settings[key]}` "
                        f"for key {req_opt} does not exist!"
                    )
                continue

            # setting content of a file as an array to tracker payload
            if str(self.tracker_config[req_opt][key]) == "file|string|array":
                """
                for file|array we read the contents of the file line by line,
                where each line becomes and element of the array or list
                """
                if os.path.isfile(self.tracker_settings[key]):
                    self.logger.debug(
                        f"[TrackerUpload] Setting file {self.tracker_settings[key]} as string array for key '{key}'"
                    )
                    with open(self.tracker_settings[key]) as file_contents:
                        file_content_list = self._fill_string_array_data(
                            iterable_lines=file_contents.readlines()
                        )
                        payload[
                            self._get_multi_part_payload_key(key)
                        ] = file_content_list
                        self.logger.debug(
                            f"[TrackerUpload] String array data for key {key} :: {file_content_list}"
                        )
                else:
                    self.logger.critical(
                        f"[TrackerUpload] The file/path `{self.tracker_settings[key]}` "
                        f"for key '{req_opt}' does not exist!"
                    )
                continue

            # setting tracker payload data as an array
            if str(self.tracker_config[req_opt][key]) == "string|array":
                """
                for string|array we split the data with by new line,
                where each line becomes and element of the array or list
                """
                self.logger.debug(
                    f"[TrackerUpload] Setting data {self.tracker_settings[key]} as string array for key '{key}'"
                )
                file_content_list = self._fill_string_array_data(
                    iterable_lines=self.tracker_settings[key].split("\n")
                )
                payload[
                    self._get_multi_part_payload_key(key)
                ] = file_content_list
                self.logger.debug(
                    f"[TrackerUpload] String array data for key '{key}' :: {file_content_list}"
                )
                continue

            # setting file encoded as base64 string
            if str(self.tracker_config[req_opt][key]) == "file|base64":
                if os.path.isfile(self.tracker_settings[key]):
                    self.logger.debug(
                        f"[TrackerUpload] Setting file|base64 for key {key}"
                    )
                    with open(self.tracker_settings[key], "rb") as binary_file:
                        payload[key] = self._encode_file_as_base64(
                            file_pointer=binary_file
                        )
                else:
                    self.logger.critical(
                        f"[TrackerUpload] The file/path `{self.tracker_settings[key]}` "
                        f"for key {req_opt} does not exist!"
                    )
                continue

            # setting file content to payload
            if str(val).endswith(".nfo") or str(val).endswith(".txt"):
                self._create_file_if_not_exists(file_name=val)
                with open(val, encoding="utf-8") as txt_file:
                    payload[key] = txt_file.read()
                continue
            # ---------------- Special Payload Data Formats ----------------

            if req_opt == "Optional":
                self.logger.info(
                    f"[TrackerUpload] Optional key {key} will be added to payload"
                )
            elif req_opt == "Default":
                self.logger.info(
                    f"[TrackerUpload] Default key {key} will be added to payload"
                )

            payload[key] = val

        return files, display_files, payload

    @staticmethod
    def _create_file_if_not_exists(file_name):
        if not os.path.exists(file_name):
            create_file = open(file_name, "w+")
            create_file.close()

    @staticmethod
    def _encode_file_as_base64(*, file_pointer):
        import base64

        return base64.b64encode(file_pointer.read()).decode("utf-8")

    def _get_multi_part_payload_key(self, key):
        return (
            f"{key}[]"
            if self.tracker_config["technical_jargons"]["payload_type"]
            == "MULTI-PART"
            else key
        )

    @staticmethod
    def _fill_string_array_data(iterable_lines):
        return [line.strip() for line in iterable_lines if line.strip()]

    def _display_payload_table(self, payload):
        # ------- Show the user a table of the API KEY/VAL (TEXT) that we are about to send ------- #
        review_table = Table(
            title=f"\n\n\n\n[bold][deep_pink1]{self.tracker} Upload data (Text):[/bold][/deep_pink1]",
            show_header=True,
            header_style="bold cyan",
            box=box.HEAVY,
            border_style="dim",
            show_lines=True,
        )
        review_table.add_column("Key", justify="left")
        review_table.add_column("Value (TEXT)", justify="left")
        # Insert the data into the table, raw data (no paths)
        for payload_k, payload_v in sorted(payload.items()):
            # Add torrent_info data to each row
            review_table.add_row(
                f"[deep_pink1]{payload_k}[/deep_pink1]",
                f"[dodger_blue1]{payload_v}[/dodger_blue1]",
            )
        self.console.print(review_table, justify="center")

    def _display_files_table(self, display_files):
        # Displaying FILES data if present
        review_upload_settings_files_table = Table(
            title=f"\n\n\n\n[bold][green3]{self.tracker} Upload data (FILES):[/green3][/bold]",
            show_header=True,
            header_style="bold cyan",
            box=box.HEAVY,
            border_style="dim",
            show_lines=True,
        )

        review_upload_settings_files_table.add_column("Key", justify="left")
        review_upload_settings_files_table.add_column(
            "Value (FILE)", justify="left"
        )
        # Insert the path to the files we are uploading
        for payload_file_k, payload_file_v in sorted(display_files.items()):
            # Add torrent_info data to each row
            review_upload_settings_files_table.add_row(
                f"[green3]{payload_file_k}[/green3]",
                f"[dodger_blue1]{payload_file_v}[/dodger_blue1]",
            )
        self.console.print(review_upload_settings_files_table, justify="center")

    def _stop_upload(self):
        if (
            Prompt.ask(
                "Do you want to upload with these settings?", choices=["y", "n"]
            )
            == "y"
        ):
            return False
        self.console.print(
            f"\nCanceling upload to [bright_red]{self.tracker}[/bright_red]"
        )
        self.logger.error(
            f"[TrackerUpload] User chose to cancel the upload to {self.tracker}"
        )
        return True

    def _log_dry_run_message(self):
        self.logger.info(
            "[TrackerUpload] Dry-Run mode... Skipping upload to tracker"
        )
        self.console.print(
            "[bold red] Dry Run Mode [bold red] Skipping upload to tracker"
        )

    def _log_tracker_upload_response(self, *, url, response):
        self.logger.info(f"[TrackerUpload] POST Request: {url}")
        self.logger.info(
            f"[TrackerUpload] Response Code: {response.status_code}"
        )
        self.logger.info(f"[TrackerUpload] Response URL: {response.url}")
        self.console.print(
            f"\nSite response: [blue]{response.text[0:200]}...[/blue]"
        )

    def upload(self) -> bool:
        self.logger.info(
            f"[TrackerUpload] Attempting to upload to: {self.tracker}"
        )
        self._log_tracker_settings()

        url = str(self.tracker_config["upload_form"]).format(
            api_key=self.tracker_api_key
        )
        url_masked = str(self.tracker_config["upload_form"]).format(
            api_key="REDACTED"
        )
        headers = self._get_headers_for_tracker()
        requests_orchestrator = self._initialize_requests_orchestrator()

        files, display_files, payload = self._prepare_payloads_for_upload()
        self._log_tracker_payload(
            payload=payload, url_masked=url_masked, files=files
        )

        if self.auto_mode is False:
            # prompt the user to verify everything looks OK before uploading
            self._display_payload_table(payload=payload)
            self._display_files_table(display_files=display_files)
            stop_upload = self._stop_upload()
            if stop_upload:
                return False

        if self.dry_run:
            self._log_dry_run_message()
            return False

        request_items = {
            "method": "POST",
            "url": url,
            "files": files,
            "headers": headers,
            "json"
            if self.tracker_config["technical_jargons"]["payload_type"]
            == "JSON"
            else "data": payload,
        }
        response = requests_orchestrator.request(**request_items)
        self._log_tracker_upload_response(url=url, response=response)

        self._process_upload_response(response=response)

    def _process_upload_response(self, response) -> bool:
        self.console.print(
            f"[bold]HTTP response status code: [red]{response.status_code}[/red][/bold]"
        )
        if response.status_code in (200, 201):
            return self._parse_possible_success_response(response=response)
        if response.status_code == 404:
            return self._log_404_error()
        if response.status_code == 500:
            return self._log_500_error()
        if response.status_code == 400:
            return self._log_400_error(response=response)
        return self._log_other_error()

    def _parse_possible_success_response(self, response) -> bool:
        self.logger.info(
            f"[TrackerUpload] Upload response for {self.tracker}:::::::::::::::::::::::::\n {response.text}"
        )
        if self.tracker_config["technical_jargons"]["response_type"] == "TEXT":
            return self._parse_text_response(response=response)

        response_json = response.json()
        self.upload_response = response_json
        if "success" in response_json:
            return self._parse_success_key_from_json(
                response_json=response_json
            )

        if "status" in response_json:
            return self._parse_status_key_from_json(response_json=response_json)

        if "success" in str(response_json).lower():
            return self._parse_success_text_from_json(
                response_json=response_json
            )

        if "status" in str(response_json).lower():
            return self._parse_status_text_from_json(
                response_json=response_json
            )

        return self._log_unknown_upload_error()

    def _log_404_error(self) -> bool:
        self.console.print("Upload failed", style="bold red")
        self.logger.critical(
            f"[TrackerUpload] 404 was returned on that upload, this is a problem with the site ({self.tracker})"
        )
        self.logger.error("[TrackerUpload] Upload failed")
        self.upload_response = 404
        return False

    def _log_500_error(self) -> bool:
        self.console.print(
            "The upload might have [red]failed[/], the site isn't returning the uploads status"
        )
        # This is to deal with the 500 internal server error responses BLU has been recently returning
        self.logger.error(
            f"[TrackerUpload] HTTP response status code '500' was returned (500=Internal "
            f"Server Error) "
        )
        self.logger.info(
            "[TrackerUpload] This doesn't mean the upload failed, instead the site simply isn't returning the "
            "upload status "
        )
        self.upload_response = 500
        return False

    def _log_400_error(self, response) -> bool:
        self.console.print(
            "Upload failed. See logs for error...", style="bold red"
        )
        try:
            self.logger.critical(
                f"[TrackerUpload] 400 was returned on that upload, this is a problem with the site ({self.tracker})."
                f' Error: Error {response.json()["error"] if "error" in response.json() else response.json()} '
            )
        except (KeyError, TypeError, AttributeError, JSONDecodeError) as e:
            self.logger.critical(
                f"[TrackerUpload] 400 was returned on that upload, this is a problem with the site ({self.tracker})."
            )
            self.logger.critical(
                f"An exception occurred: {type(e).__name__}: {str(e)}"
            )
        self.logger.error("[TrackerUpload] Upload failed")
        self.upload_response = 400
        return False

    def _log_other_error(self) -> bool:
        self.console.print(
            "The status code isn't [green]200[/green] so something failed, upload may have failed"
        )
        self.logger.error(
            "[TrackerUpload] Status code is not 200, upload might have failed"
        )
        self.upload_response = "Unknown Error"
        return False

    def _log_unknown_upload_error(self) -> bool:
        self.console.print("Upload to tracker failed.", style="bold red")
        self.logger.critical(
            f"[TrackerUpload] Something really went wrong when uploading to {self.tracker} and we didn't even get a "
            f"'success' json key "
        )
        return False

    def _parse_text_response(self, response) -> bool:
        # trackers that send text as upload response instead of json.
        # since parsing this could be different, we just use a custom action
        self.logger.info(
            "[TrackerUpload] Response parsing is of type 'TEXT'. Invoking custom action to parse the "
            "response. "
        )
        try:
            custom_action = utils.load_custom_actions(
                self.tracker_config["technical_jargons"]["response_action"]
            )
            upload_status, error_message = custom_action(response)
            if not upload_status:
                self.console.print(
                    f"Upload to tracker failed. Error: [bold red]{error_message}[/bold red]"
                )
            self.upload_response = upload_status
            return upload_status
        except Exception as ex:
            self.logger.exception(
                "[TrackerUpload] Custom action to parse response text failed. Marking upload as failed",
                exc_info=ex,
            )
            self.upload_response = "Custom Action Failed"
            return False

    def _parse_success_key_from_json(self, response_json) -> bool:
        if str(response_json["success"]).lower() == "true":
            self.logger.info(
                f"[TrackerUpload] Upload to {self.tracker} was a success!"
            )
            self.console.line(count=2)
            self.console.rule(
                f"\n :thumbsup: Successfully uploaded to {self.tracker} :balloon: \n",
                style="bold green1",
                align="center",
            )
            return True
        else:
            self.console.print("Upload to tracker failed.", style="bold red")
            self.logger.critical(
                f"[TrackerUpload] Upload to {self.tracker} failed"
            )
            return False

    def _parse_status_key_from_json(self, response_json) -> bool:
        if str(response_json["status"]).lower() in {"true", "success"}:
            pass
            self.logger.info(
                "[TrackerUpload] Upload to {} was a success!".format(
                    self.tracker
                )
            )
            self.console.line(count=2)
            self.console.rule(
                f"\n :thumbsup: Successfully uploaded to {self.tracker} :balloon: \n",
                style="bold green1",
                align="center",
            )
            return True
        else:
            self.console.print("Upload to tracker failed.", style="bold red")
            self.logger.critical(
                f"[TrackerUpload] Upload to {self.tracker} failed"
            )
            return False

    def _parse_success_text_from_json(self, response_json) -> bool:
        # TODO: this method might be redundant
        if str(response_json["success"]).lower() == "true":
            self.logger.info(
                "[TrackerUpload] Upload to {} was a success!".format(
                    self.tracker
                )
            )
            self.console.line(count=2)
            self.console.rule(
                f"\n :thumbsup: Successfully uploaded to {self.tracker} :balloon: \n",
                style="bold green1",
                align="center",
            )
            return True
        else:
            self.console.print("Upload to tracker failed.", style="bold red")
            self.logger.critical(
                f"[TrackerUpload] Upload to {self.tracker} failed"
            )
            return False

    def _parse_status_text_from_json(self, response_json) -> bool:
        if str(response_json["status"]).lower() == "true":
            self.logger.info(
                "[TrackerUpload] Upload to {} was a success!".format(
                    self.tracker
                )
            )
            self.console.line(count=2)
            self.console.rule(
                f"\n :thumbsup: Successfully uploaded to {self.tracker} :balloon: \n",
                style="bold green1",
                align="center",
            )
            return True
        else:
            self.console.print("Upload to tracker failed.", style="bold red")
            self.logger.critical(
                f"[TrackerUpload] Upload to {self.tracker} failed"
            )
            return False
