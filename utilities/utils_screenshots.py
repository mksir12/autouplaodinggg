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
from datetime import datetime
from pathlib import Path
from typing import Tuple, List, Dict

from ffmpy import FFmpeg
from rich.console import Console
from rich.progress import track

from modules.config import UploaderConfig
from modules.constants import (
    BB_CODE_IMAGES_PATH,
    URL_IMAGES_PATH,
    SCREENSHOTS_PATH,
    UPLOADS_COMPLETE_MARKER_PATH,
    SCREENSHOTS_RESULT_FILE_PATH,
)
from modules.image_hosts.image_host_manager import GGBotImageHostManager
from modules.image_hosts.image_upload_status import GGBotImageUploadStatus
from utilities.utils import normalize_for_system_path

# For more control over rich terminal content, import and construct a Console object.
console = Console()


def _get_ss_range(duration: int, num_of_screenshots: int) -> List[str]:
    # If no spoilers is enabled, then screenshots are taken from first half of the movie or tv show
    # otherwise screenshots are taken at regular intervals from the whole movie or tv show
    first_time_stamp = (int(duration / 2)) / (num_of_screenshots + 1)

    timestamps = []
    for num_screen in range(1, num_of_screenshots + 1):
        millis = round(first_time_stamp) * num_screen
        timestamps.append(
            str(
                datetime.strptime(
                    "%d:%d:%d"
                    % (
                        int((millis / (1000 * 60 * 60)) % 24),
                        int((millis / (1000 * 60)) % 60),
                        int((millis / 1000) % 60),
                    ),
                    "%H:%M:%S",
                ).time()
            )
        )
    return timestamps


class GGBotScreenshotManager:
    def __init__(
        self,
        *,
        torrent_title,
        duration,
        upload_media,
        skip_screenshots,
        base_path,
        hash_prefix,
    ):
        self.skip_screenshots = skip_screenshots
        self.upload_media = upload_media
        self.duration = duration
        self.num_of_screenshots: int = UploaderConfig().NO_OF_SCREENSHOTS
        self.torrent_title = normalize_for_system_path(torrent_title)
        self.image_host_manager = GGBotImageHostManager(self.torrent_title)

        self.bb_code_images_path = BB_CODE_IMAGES_PATH.format(
            base_path=base_path, sub_folder=hash_prefix
        )
        self.url_images_path = URL_IMAGES_PATH.format(
            base_path=base_path, sub_folder=hash_prefix
        )
        self.screenshots_path = SCREENSHOTS_PATH.format(
            base_path=base_path, sub_folder=hash_prefix
        )
        self.screenshots_result_path = SCREENSHOTS_RESULT_FILE_PATH.format(
            base_path=base_path, sub_folder=hash_prefix
        )
        self.marker_path = UPLOADS_COMPLETE_MARKER_PATH.format(
            base_path=base_path, sub_folder=hash_prefix
        )

        logging.info(
            f"[GGBotScreenshotManager::init] Screenshots will be save with prefix {self.torrent_title}"
        )
        logging.info(
            f"[GGBotScreenshotManager::init] Using {upload_media} to generate screenshots"
        )

    def _display_heading(self) -> None:
        console.line(count=2)
        console.rule("Screenshots", style="red", align="center")
        console.line(count=1)
        console.print(
            f"\nTaking [chartreuse1]{str(self.num_of_screenshots)}[/chartreuse1] screenshots",
            style="Bold Blue",
        )

    def _skip_screenshot_generation(self) -> bool:
        # user has provided the `skip_screenshots` in the command line arguments.
        # Hence we are going to skip taking screenshots
        logging.info(
            "[GGBotScreenshotManager::generate_screenshots] User has provided the `skip_screenshots` argument. "
            "Hence continuing without screenshots."
        )
        console.print(
            "\nUser provided the argument `[red]skip_screenshots[/red]`. "
            "Overriding screenshot configurations in config.env",
            style="bold green",
        )
        return self._write_no_screenshot_data()

    def _zero_screenshots_needed(self) -> bool:
        # if user has set number of screenshots to 0, then we don't have to take any screenshots.
        logging.error(
            f"[GGBotScreenshotManager::generate_screenshots] No of screenshots is "
            f'{"not set" if self.num_of_screenshots == 0 else f"set to {self.num_of_screenshots}"}, '
            f"continuing without screenshots."
        )
        console.print(
            f"\nNo of screenshots is "
            f'{"not set" if self.num_of_screenshots == 0 else f"set to {self.num_of_screenshots}"}, \n',
            style="bold red",
        )
        return self._write_no_screenshot_data()

    def _write_no_screenshot_data(self) -> bool:
        # TODO: update this to work in line with the new json screenshot data
        with open(self.bb_code_images_path, "w") as file1, open(
            self.url_images_path, "w"
        ) as file2:
            file1.write(
                "[b][color=#FF0000][size=22]No Screenshots Available[/size][/color][/b]"
            )
            file2.write("No Screenshots Available")
        logging.error(
            "[GGBotScreenshotManager::generate_screenshots] Continuing upload without screenshots "
            "because no image hosts have been configured properly"
        )
        console.print(
            "Continuing without screenshots. [red bold]No image hosts configured properly[/red bold]\n",
            style="chartreuse1",
        )
        return False

    @staticmethod
    def _does_screenshot_exist(output_file):
        return Path(output_file).is_file()

    def _have_uploaded_screenshots_previously(self):
        return Path(self.marker_path).is_file()

    @staticmethod
    def _run_ffmpeg(*, upload_media, timestamp, output_file):
        FFmpeg(
            inputs={
                upload_media: [
                    "-loglevel",
                    "panic",
                    "-ss",
                    timestamp,
                    "-itsoffset",
                    "-2",
                ]
            },
            outputs={
                output_file: [
                    "-vf",
                    "scale='max(sar,1)*iw':'max(1/sar,1)*ih'",
                    "-frames:v",
                    "1",
                    "-q:v",
                    "10",
                    "-pix_fmt",
                    "rgb24",
                ]
            },
        ).run()

    def _generate_screenshot(self, *, output_file, timestamp):
        if not self._does_screenshot_exist(output_file):
            self._run_ffmpeg(
                upload_media=self.upload_media,
                timestamp=timestamp,
                output_file=output_file,
            )
        else:
            logging.info(
                f"[GGBotScreenshotManager::generate_screenshots] Continuing with existing screenshot "
                f"instead of taking new one: {self.torrent_title} - ({timestamp}).png"
            )

    def _get_timestamp_outfile_tuple(
        self, ss_timestamps
    ) -> List[Tuple[str, str]]:
        return [
            (
                timestamp,
                f"{self.screenshots_path}{self.torrent_title} - ({timestamp.replace(':', '.')}).png",
            )
            for timestamp in ss_timestamps
        ]

    def _generate_screenshots(self, timestamp_outfile_tuple):
        for timestamp_file in track(
            timestamp_outfile_tuple,
            description="Taking screenshots..",
        ):
            self._generate_screenshot(
                timestamp=timestamp_file[0], output_file=timestamp_file[1]
            )

    def generate_screenshots(self) -> bool:
        self._display_heading()

        if self.skip_screenshots:
            return self._skip_screenshot_generation()
        if self.num_of_screenshots == 0:
            return self._zero_screenshots_needed()
        if self.image_host_manager.no_of_image_hosts == 0:
            return self._write_no_screenshot_data()

        # Figure out where exactly to take screenshots by evenly dividing up the length of the video
        ss_timestamps: List[str] = _get_ss_range(
            duration=int(self.duration),
            num_of_screenshots=self.num_of_screenshots,
        )
        timestamp_outfile_tuple = self._get_timestamp_outfile_tuple(
            ss_timestamps
        )
        self._generate_screenshots(timestamp_outfile_tuple)

        console.print("Finished taking screenshots!\n", style="sea_green3")
        # log the list of screenshot timestamps
        logging.info(
            f"[GGBotScreenshotManager::generate_screenshots] Took screenshots at: {ss_timestamps}"
        )

        # checking whether we have previously uploaded all the screenshots.
        # If we have, then no need to upload them again
        # if screenshots were not uploaded previously, then we'll upload them.
        # As of now partial uploads are not discounted for. During upload, all screenshots will be uploaded
        if self._have_uploaded_screenshots_previously():
            logging.info(
                "[GGBotScreenshotManager::generate_screenshots] Noticed that all screenshots have been "
                "uploaded to image hosts. Skipping Uploads"
            )
            console.print(
                "Reusing previously uploaded screenshot urls!\n",
                style="sea_green3",
            )
            return True  # indicates that screenshots are available
        else:
            return self._upload_screenshots(timestamp_outfile_tuple)

    @staticmethod
    def _get_init_images_data(timestamp_outfile_tuple: List[Tuple]):
        # all different type of screenshots that the upload takes.
        images_data = {
            "bbcode_images": "",
            "bbcode_images_nothumb": "",
            "bbcode_thumb_nothumb": "",
            "url_images": "",
            "data_images": "",
        }
        for outfile in timestamp_outfile_tuple:
            images_data[
                "data_images"
            ] = f'{outfile[1]}\n{images_data["data_images"]}'
        return images_data

    def _upload_screenshots(self, timestamp_outfile_tuple: List[Tuple]) -> bool:
        images_data = self._get_init_images_data(timestamp_outfile_tuple)
        logging.info(
            "[Screenshots] Starting to upload screenshots to image hosts."
        )
        console.print(
            f"Image host order: [chartreuse1]{' [bold blue]:arrow_right:[/bold blue] '.join(self.image_host_manager.image_hosts)}[/chartreuse1]",
            style="Bold Blue",
        )
        successfully_uploaded_image_count = 0
        for tuple_item in track(
            timestamp_outfile_tuple, description="Uploading screenshots..."
        ):
            status: GGBotImageUploadStatus = (
                self.image_host_manager.upload_screenshots(
                    image_path=tuple_item[0]
                )
            )
            if status.status:
                successfully_uploaded_image_count += 1
                images_data[
                    "bbcode_images"
                ] = f'{status.bb_code_medium_thumb} {images_data["bbcode_images"]}'
                images_data[
                    "bbcode_images_nothumb"
                ] = f'{status.bb_code_medium} {images_data["bbcode_images_nothumb"]}'
                images_data[
                    "bbcode_thumb_nothumb"
                ] = f'{status.bb_code_thumb} {images_data["bbcode_thumb_nothumb"]}'
                images_data[
                    "url_images"
                ] = f'{status.image_url}\n{images_data["url_images"]}'

        logging.info(
            "[Screenshots] Uploaded screenshots. Saving urls and bbcodes..."
        )
        self._save_screenshot_upload_data(images_data)

        if len(timestamp_outfile_tuple) == successfully_uploaded_image_count:
            console.print(
                f"Uploaded {successfully_uploaded_image_count}/{len(timestamp_outfile_tuple)} screenshots",
                style="sea_green3",
                highlight=False,
            )
            logging.info(
                f"[Screenshots] Successfully uploaded {successfully_uploaded_image_count}/{len(timestamp_outfile_tuple)} screenshots"
            )
            self._create_upload_success_marker()
        else:
            console.print(
                f"{len(timestamp_outfile_tuple) - successfully_uploaded_image_count}/{len(timestamp_outfile_tuple)} screenshots failed to upload",
                style="bold red",
                highlight=False,
            )
            logging.error(
                f"[Screenshots] {len(timestamp_outfile_tuple) - successfully_uploaded_image_count}/{len(timestamp_outfile_tuple)} screenshots failed to upload"
            )
        return True

    def _create_upload_success_marker(self) -> None:
        with open(
            self.marker_path,
            "w",
        ) as f:
            f.write("ALL_SCREENSHOT_UPLOADED_SUCCESSFULLY")
            logging.debug(
                "[Screenshots] Marking that all screenshots have been uploaded successfully"
            )

    def _save_screenshot_upload_data(self, screenshot_data: Dict) -> None:
        with open(
            self.screenshots_result_path,
            "w",
        ) as file:
            file.write(json.dumps(screenshot_data))
