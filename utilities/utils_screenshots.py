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

import asyncio
import base64
import json
import logging
import os
import re
from datetime import datetime
from pathlib import Path

import ptpimg_uploader
import pyimgbox
import requests
from ffmpy import FFmpeg
from imgurpython import ImgurClient
from rich.console import Console
from rich.progress import track

import modules.env as Environment
from modules.constants import (
    BB_CODE_IMAGES_PATH,
    IMAGE_HOST_URLS,
    SCREENSHOTS_PATH,
    SCREENSHOTS_RESULT_FILE_PATH,
    UPLOADS_COMPLETE_MARKER_PATH,
    URL_IMAGES_PATH,
)

from .utils import normalize_for_system_path

# For more control over rich terminal content, import and construct a Console object.
console = Console()


def _get_ss_range(duration, num_of_screenshots):
    # If no spoilers is enabled, then screenshots are taken from first half of the movie or tv show
    # otherwise screenshots are taken at regular intervals from the whole movie or tv show
    no_spoilers = Environment.is_no_spoiler_screenshot()
    first_time_stamp = (
        int(int(duration) / 2) if no_spoilers else int(duration)
    ) / int(int(num_of_screenshots) + 1)

    list_of_ss_timestamps = []
    for num_screen in range(1, int(num_of_screenshots) + 1):
        millis = round(first_time_stamp) * num_screen
        list_of_ss_timestamps.append(
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
    return list_of_ss_timestamps


def _upload_screens(
    img_host, img_host_api, image_path, torrent_title, base_path
):
    # ptpimg does all for us to upload multiple images at the same time but to simplify things &
    # allow for simple "backup hosts"/upload failures we instead upload 1 image at a time
    #
    # Both imgbb & freeimage are based on Chevereto which the API has us upload 1 image at a time while imgbox uses something custom
    # and we upload a list of images at the same time
    #
    # Annoyingly pyimgbox requires every upload be apart of a "gallery", This is fine if you're uploading a list of multiple images at the same time
    # but because of the way we deal with "backup" image hosts/upload failures its not realistic to pass a list of all the images to imgbox at the same time.
    # so instead we just upload 1 image at a time to imgbox (also creates 1 gallery per image)
    #
    # Return values:
    # 1. Status
    # 2. BBCode|Medium|SizeLimit
    # 3. BBCode|Medium|NoSizeLimit
    # 4. BBCode|Thumbnail|NoSizeLimit
    # 5. Full Image URL
    #
    thumb_size = Environment.get_thumb_size()
    if img_host == "DUMMY":
        # this is a case just for testing screenshots feature
        return [
            True,
            f'[url=http://ggbot/img1][img={thumb_size}]{"m.".join("http://ggbot/img1".rsplit(".", 1))}[/img][/url]',
            f'[url=http://ggbot/img1][img]{"m.".join("http://ggbot/img1".rsplit(".", 1))}[/img][/url]',
            f'[url=http://ggbot/img1][img]{"t.".join("http://ggbot/img1".rsplit(".", 1))}[/img][/url]',
            "http://ggbot/img1",
        ]

    elif img_host == "pixhost":
        data = {"content_type": "0", "max_th_size": thumb_size}
        files = {"img": open(image_path, "rb")}
        img_upload_request = requests.post(
            url="https://api.pixhost.to/images", data=data, files=files
        )

        if img_upload_request.ok:
            img_upload_response = img_upload_request.json()
            logging.debug(
                f"[Screenshots] Image upload response: {img_upload_response}"
            )
            image_url = (
                img_upload_response["th_url"]
                .replace("t77", "img77")
                .replace("/thumbs/", "/images/")
            )
            return [
                True,
                f'[url={img_upload_response["show_url"]}][img={thumb_size}]{image_url}[/img][/url]',
                f'[url={img_upload_response["show_url"]}][img]{image_url}[/img][/url]',
                f'[url={img_upload_response["show_url"]}][img]{img_upload_response["th_url"]}[/img][/url]',
                image_url,
            ]
        else:
            logging.error(
                f"[Screenshots] {img_host} upload failed. JSON Response: {img_upload_request.json()}"
            )
            console.print(
                f"{img_host} upload failed. Status code: [bold]{img_upload_request.status_code}[/bold]",
                style="red3",
                highlight=False,
            )
            return False

    elif img_host == "imgur":
        try:
            client = ImgurClient(
                client_id=Environment.get_imgur_client_id(),
                client_secret=Environment.get_imgur_api_key(),
            )
            response = client.upload_from_path(image_path)
            logging.debug(
                f"[Screenshots] Imgur image upload response: {response}"
            )
            # return data
            return [
                True,
                f'[url={response["link"]}][img={thumb_size}]{"m.".join(response["link"].rsplit(".", 1))}[/img][/url]',
                f'[url={response["link"]}][img]{"m.".join(response["link"].rsplit(".", 1))}[/img][/url]',
                f'[url={response["link"]}][img]{"t.".join(response["link"].rsplit(".", 1))}[/img][/url]',
                response["link"],
            ]
        except Exception:
            logging.error(
                "[Screenshots] imgur upload failed, double check the imgur API Key & try again."
            )
            console.print(
                "\\imgur upload failed. double check the [bold]imgur_client_id[/bold] and in [bold]imgur_api_key[/bold] [bold]config.env[/bold]\n",
                style="Red",
                highlight=False,
            )
            return False

    elif img_host == "ptpimg":
        try:
            ptp_img_upload = ptpimg_uploader.upload(
                api_key=Environment.get_ptpimg_api_key(),
                files_or_urls=[image_path],
                timeout=15,
            )
            # Make sure the response we get from ptpimg is a list
            if not isinstance(ptp_img_upload, list):
                return False
            # assuming it is, we can then get the img url, format it into bbcode & return it
            logging.debug(
                f"[Screenshots] Ptpimg image upload response: {ptp_img_upload}"
            )
            # TODO need to see the response and decide on the thumnail image and size
            # Pretty sure ptpimg doesn't compress/host multiple 'versions' of the same image so we use the direct image link for both parts of the bbcode (url & img)
            return [
                True,
                f"[url={ptp_img_upload[0]}][img={thumb_size}]{ptp_img_upload[0]}[/img][/url]",
                f"[url={ptp_img_upload[0]}][img]{ptp_img_upload[0]}[/img][/url]",
                f"[url={ptp_img_upload[0]}][img]{ptp_img_upload[0]}[/img][/url]",
                ptp_img_upload[0],
            ]
        except AssertionError:
            logging.exception(
                "[Screenshots] ptpimg uploaded an image but returned something unexpected (should be a list)"
            )
            console.print(
                "\nUnexpected response from ptpimg upload (should be a list). No image link found\n",
                style="Red",
                highlight=False,
            )
            return False
        except Exception:
            logging.exception(
                "[Screenshots] ptpimg upload failed, double check the ptpimg API Key & try again."
            )
            console.print(
                "\nptpimg upload failed. double check the [bold]ptpimg_api_key[/bold] in [bold]config.env[/bold]\n",
                style="Red",
                highlight=False,
            )
            return False

    elif img_host in ("imgbb", "freeimage", "imgfi", "snappie", "lensdump"):
        # Get the correct image host url/json key
        available_image_host_urls = json.load(
            open(IMAGE_HOST_URLS.format(base_path=base_path))
        )

        parent_key = "data" if img_host == "imgbb" else "image"

        # Load the img_host_url, api key & img encoded in base64 into a dict called 'data' & post it
        image_host_url = available_image_host_urls[img_host]
        try:
            img_upload_request = None
            data = {"key": img_host_api}
            if img_host in ("imgfi", "snappie", "lensdump"):
                headers = {}
                if img_host == "lensdump":
                    # lensdump needs api key in headers and have a different multipart format
                    data["format"] = "json"
                    data["source"] = base64.b64encode(
                        open(image_path, "rb").read()
                    )
                    headers = {
                        "X-API-Key": Environment.get_image_host_api_key(
                            img_host
                        )
                    }
                    files = {}
                else:
                    files = {"source": open(image_path, "rb")}
                img_upload_request = requests.post(
                    url=image_host_url, data=data, files=files, headers=headers
                )
            else:
                data["image"] = base64.b64encode(open(image_path, "rb").read())
                img_upload_request = requests.post(
                    url=image_host_url, data=data
                )

            if img_upload_request.ok:
                img_upload_response = img_upload_request.json()
                logging.debug(
                    f"[Screenshots] Image upload response: {img_upload_response}"
                )
                # When you upload an image you get a few links back, you get 'medium', 'thumbnail', 'url', 'url_viewer'
                try:
                    returnList = []
                    # setting the return status as true
                    returnList.append(True)

                    if "medium" in img_upload_response[parent_key]:
                        img_type = "medium"
                        # if medium sized image is present then we'll use that as the second and ththirdrid entry in the list.
                        # second one with thumbnail size limit and third without
                        returnList.append(
                            f'[url={img_upload_response[parent_key]["url_viewer"]}][img={thumb_size}]{img_upload_response[parent_key][img_type]["url"]}[/img][/url]'
                        )
                        returnList.append(
                            f'[url={img_upload_response[parent_key]["url_viewer"]}][img]{img_upload_response[parent_key][img_type]["url"]}[/img][/url]'
                        )
                        if "thumb" not in img_upload_response[parent_key]:
                            # thumbnail sized image is not present, hence we'll use medium sized image as fourth entry
                            returnList.append(
                                f'[url={img_upload_response[parent_key]["url_viewer"]}][img]{img_upload_response[parent_key][img_type]["url"]}[/img][/url]'
                            )

                    if "thumb" in img_upload_response[parent_key]:
                        img_type = "thumb"
                        if len(returnList) == 3:
                            # if medium sized image was present, then the size of the list would be 3
                            # hence we only need to add the 4th one as the thumbnail sized image without any size limits
                            returnList.append(
                                f'[url={img_upload_response[parent_key]["url_viewer"]}][img]{img_upload_response[parent_key][img_type]["url"]}[/img][/url]'
                            )
                        else:
                            # no medium image type is present. hence we'll use thumb for those as well
                            # second will be the thumbnail sized image with size limit
                            # third and fourth will be thumbnail sized image without any limits
                            returnList.append(
                                f'[url={img_upload_response[parent_key]["url_viewer"]}][img={thumb_size}]{img_upload_response[parent_key][img_type]["url"]}[/img][/url]'
                            )
                            returnList.append(
                                f'[url={img_upload_response[parent_key]["url_viewer"]}][img]{img_upload_response[parent_key][img_type]["url"]}[/img][/url]'
                            )
                            returnList.append(
                                f'[url={img_upload_response[parent_key]["url_viewer"]}][img]{img_upload_response[parent_key][img_type]["url"]}[/img][/url]'
                            )

                    if len(returnList) != 4:
                        # neither of medium nor thumbnail sized image was present, so we'll just add the full image url as 2 3 and 4th entry
                        returnList.append(
                            f'[url={img_upload_response[parent_key]["url_viewer"]}][img={thumb_size}]{img_upload_response[parent_key][img_type]["url"]}[/img][/url]'
                        )
                        returnList.append(
                            f'[url={img_upload_response[parent_key]["url_viewer"]}][img]{img_upload_response[parent_key]["url"]}[/img][/url]'
                        )
                        returnList.append(
                            f'[url={img_upload_response[parent_key]["url_viewer"]}][img]{img_upload_response[parent_key]["url"]}[/img][/url]'
                        )

                    returnList.append(img_upload_response[parent_key]["url"])
                    return returnList
                except KeyError as key_error:
                    logging.error(
                        f"[Screenshots] {img_host} json KeyError: {key_error}"
                    )
                    return False
            else:
                logging.error(
                    f"[Screenshots] {img_host} upload failed. JSON Response: {img_upload_request.json()}"
                )
                console.print(
                    f"{img_host} upload failed. Status code: [bold]{img_upload_request.status_code}[/bold]",
                    style="red3",
                    highlight=False,
                )
                return False
        except requests.exceptions.RequestException:
            logging.exception(
                f"[Screenshots] Failed to upload {image_path} to {img_host}"
            )
            console.print(
                f"upload to [bold]{img_host}[/bold] has failed!", style="Red"
            )
            return False

    # Instead of coding our own solution we'll use the awesome project https://github.com/plotski/pyimgbox to upload to imgbox
    elif img_host == "imgbox":

        async def imgbox_upload(filepaths):
            async with pyimgbox.Gallery(
                title=torrent_title, thumb_width=int(thumb_size)
            ) as gallery:
                async for submission in gallery.add(filepaths):
                    logging.debug(
                        f"[Screenshots] Imgbox image upload response: {submission}"
                    )
                    if not submission["success"]:
                        logging.error(
                            f"[Screenshots] {submission['filename']}: {submission['error']}"
                        )
                        return False
                    else:
                        logging.info(
                            f'[Screenshots] imgbox edit url for {image_path}: {submission["edit_url"]}'
                        )
                        return [
                            True,
                            f'[url={submission["web_url"]}][img={thumb_size}]{submission["image_url"]}[/img][/url]',
                            f'[url={submission["web_url"]}][img]{submission["image_url"]}[/img][/url]',
                            f'[url={submission["web_url"]}][img]{submission["thumbnail_url"]}[/img][/url]',
                            submission["image_url"],
                        ]

        if os.path.getsize(image_path) >= 10485760:  # Bytes
            logging.error(
                "[Screenshots] Screenshot size is over imgbox limit of 10MB, Trying another host (if available)"
            )
            return False

        imgbox_asyncio_upload = asyncio.run(
            imgbox_upload(filepaths=[image_path])
        )
        if imgbox_asyncio_upload:
            return [
                True,
                imgbox_asyncio_upload[1],
                imgbox_asyncio_upload[2],
                imgbox_asyncio_upload[3],
                imgbox_asyncio_upload[4],
            ]

    else:
        logging.fatal(
            f"[Screenshots] Invalid imagehost {img_host}. Cannot upload screenshots."
        )
        return False


def take_upload_screens(
    duration,
    upload_media_import,
    torrent_title_import,
    base_path,
    hash_prefix,
    skip_screenshots=False,
):
    console.line(count=2)
    console.rule("Screenshots", style="red", align="center")
    console.line(count=1)

    # getting the number of screenshots to be taken
    num_of_screenshots = Environment.get_num_of_screenshots()

    logging.info(
        f"[Screenshots] Sanitizing the torrent title `{torrent_title_import}` since this is from TMDB"
    )
    torrent_title_import = normalize_for_system_path(torrent_title_import)
    logging.info(
        f"[Screenshots] Using {upload_media_import} to generate screenshots"
    )
    logging.info(
        f"[Screenshots] Screenshots will be save with prefix {torrent_title_import}"
    )
    console.print(
        f"\nTaking [chartreuse1]{str(num_of_screenshots)}[/chartreuse1] screenshots",
        style="Bold Blue",
    )

    enabled_img_hosts_list = []
    if skip_screenshots:
        # user has provided the `skip_screenshots` in the command line arguments. Hence we are going to skip taking screenshots
        logging.info(
            "[Screenshots] User has provided the `skip_screenshots` argument. Hence continuing without screenshots."
        )
        console.print(
            "\nUser provided the argument `[red]skip_screenshots[/red]`. Overriding screenshot configurations in config.env",
            style="bold green",
        )
    # ---------------------- check if 'num_of_screenshots=0' or not set ---------------------- #
    elif num_of_screenshots == "0":
        # if user has set number of screenshots to 0, then we don't have to take any screenshots.
        logging.error(
            f'[Screenshots] num_of_screenshots is {"not set" if num_of_screenshots is None else f"set to {num_of_screenshots}"}, continuing without screenshots.'
        )
        console.print(
            f'\nnum_of_screenshots is {"not set" if num_of_screenshots is None else f"set to {num_of_screenshots}"}, \n',
            style="bold red",
        )
    else:
        # ---------------------- verify at least 1 image-host is set/enabled ---------------------- #
        # here we are looking for the number of image hosts enabled (img_host_1, img_host_2, img_host_3...)
        enabled_img_host_num_loop = 0
        while (
            Environment.get_image_host_by_priority(
                enabled_img_host_num_loop + 1
            )
            is not None
            and len(
                Environment.get_image_host_by_priority(
                    enabled_img_host_num_loop + 1
                )
            )
            > 0
        ):
            enabled_img_hosts_list.append(
                Environment.get_image_host_by_priority(
                    enabled_img_host_num_loop + 1
                )
            )
            enabled_img_host_num_loop += 1

        # now check if the loop ^^ found any enabled image hosts
        if len(enabled_img_hosts_list) == 0:
            logging.error(
                '[Screenshots] All image-hosts are disabled/not set (try setting "img_host_1=imgbox" in config.env)'
            )
            console.print(
                "\nNo image-hosts are enabled, maybe try setting [dodger_blue2][bold]img_host_1=imgbox[/bold][/dodger_blue2] in [dodger_blue2]config.env[/dodger_blue2]\n",
                style="bold red",
            )
        else:
            logging.info(
                f"[Screenshots] User has configured the following image hosts: {enabled_img_hosts_list}"
            )

        # -------------------- verify an API key is set for 'enabled_img_hosts' -------------------- #
        for img_host_api_check in enabled_img_hosts_list:
            # Check if an API key is set for the image host
            logging.debug(
                f"[Screenshots] Doing api key validation for {img_host_api_check}"
            )
            if Environment.get_image_host_api_key(img_host_api_check) is None:
                logging.error(
                    f"[Screenshots]Can't upload to {img_host_api_check} without an API key"
                )
                console.print(
                    f"\nCan't upload to [bold]{img_host_api_check}[/bold] without an API key\n",
                    style="red3",
                    highlight=False,
                )
                # If the api key is missing then remove the img_host from the 'enabled_img_hosts_list' list
                enabled_img_hosts_list.remove(img_host_api_check)
        # log the leftover enabled image hosts
        logging.info(
            f"[Screenshots] Image host order we will try & upload to: {enabled_img_hosts_list}"
        )

    # -------------------------- Check if any img_hosts are still in the 'enabled_img_hosts_list' list -------------------------- #
    # if no image_hosts are left then we show the user an error that we will continue the upload with screenshots & return back to auto_upload.py
    # TODO: update this to work in line with the new json screenshot data
    if len(enabled_img_hosts_list) == 0:
        with open(
            BB_CODE_IMAGES_PATH.format(
                base_path=base_path, sub_folder=hash_prefix
            ),
            "w",
        ) as no_images, open(
            URL_IMAGES_PATH.format(base_path=base_path, sub_folder=hash_prefix),
            "a",
        ) as append_url_txt:
            no_images.write(
                "[b][color=#FF0000][size=22]No Screenshots Available[/size][/color][/b]"
            )
            append_url_txt.write("No Screenshots Available")
            append_url_txt.close()
            no_images.close()
        logging.error(
            "[Screenshots] Continuing upload without screenshots because no image hosts has been configured properly"
        )
        console.print(
            "Continuing without screenshots. [red bold]No imagehosts configured properly[/red bold]\n",
            style="chartreuse1",
        )
        return False  # indicates that screenshots are NOT available

    # ##### Now that we've verified that at least 1 imghost is available & has an api key etc we can try & upload the screenshots ##### #
    # We only generate screenshots if a valid image host is enabled/available
    # Figure out where exactly to take screenshots by evenly dividing up the length of the video
    ss_timestamps_list = []
    screenshots_to_upload_list = []
    image_data_paths = []
    output_path = SCREENSHOTS_PATH.format(
        base_path=base_path, sub_folder=hash_prefix
    )
    for ss_timestamp in track(
        _get_ss_range(duration=duration, num_of_screenshots=num_of_screenshots),
        description="Taking screenshots..",
    ):
        stripped_time_stamp = ss_timestamp.replace(":", ".")
        output_file = (
            f"{output_path}{torrent_title_import} - ({stripped_time_stamp}).png"
        )
        # Save the ss_ts to the 'ss_timestamps_list' list
        ss_timestamps_list.append(ss_timestamp)
        screenshots_to_upload_list.append(output_file)
        # Now with each of those timestamps we can take a screenshot and update the progress bar
        # `-itsoffset -2` added for Frame accurate screenshot
        if not Path(output_file).is_file():
            FFmpeg(
                inputs={
                    upload_media_import: [
                        "-loglevel",
                        "panic",
                        "-ss",
                        ss_timestamp,
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
        else:
            logging.info(
                f"[Screenshots] Continuing with existing screenshot instead of taking new one: {torrent_title_import} - ({stripped_time_stamp}).png"
            )
        image_data_paths.append(output_file)

    console.print("Finished taking screenshots!\n", style="sea_green3")
    # log the list of screenshot timestamps
    logging.info(
        f"[Screenshots] Took screenshots at the following timestamps {ss_timestamps_list}"
    )

    # checking whether we have previously uploaded all the screenshots. If we have, then no need to upload them again
    # if screenshots were not uploaded previously, then we'll upload them.
    # As of now partial uploads are not discounted for. During upload, all screenshots will be uploaded

    if Path(
        UPLOADS_COMPLETE_MARKER_PATH.format(
            base_path=base_path, sub_folder=hash_prefix
        )
    ).is_file():
        logging.info(
            "[Screenshots] Noticed that all screenshots have been uploaded to image hosts. Skipping Uploads"
        )
        console.print(
            "Reusing previously uploaded screenshot urls!\n", style="sea_green3"
        )
        return True  # indicates that screenshots are available
    else:
        # ---------------------------------------------------------------------------------------- #
        # all different type of screenshots that the upload takes.
        images_data = {
            "bbcode_images": "",
            "bbcode_images_nothumb": "",
            "bbcode_thumb_nothumb": "",
            "url_images": "",
            "data_images": "",
        }

        for image_path in image_data_paths:
            images_data[
                "data_images"
            ] = f'{image_path}\n{images_data["data_images"]}'

        logging.info(
            "[Screenshots] Starting to upload screenshots to image hosts."
        )
        console.print(
            f"Image host order: [chartreuse1]{' [bold blue]:arrow_right:[/bold blue] '.join(enabled_img_hosts_list)}[/chartreuse1]",
            style="Bold Blue",
        )

        successfully_uploaded_image_count = 0
        for ss_to_upload in track(
            screenshots_to_upload_list, description="Uploading screenshots..."
        ):
            # This is how we fall back to a second host if the first fails
            for img_host in enabled_img_hosts_list:
                # call the function that uploads the screenshot
                upload_image = _upload_screens(
                    img_host=img_host,
                    img_host_api=Environment.get_image_host_api_key(img_host),
                    image_path=ss_to_upload,
                    torrent_title=torrent_title_import,
                    base_path=base_path,
                )
                # If the upload function returns True, we add it to bbcode_images.txt and url_images.txt
                if upload_image:
                    logging.debug(
                        f"[Screenshots] Response from image host: {upload_image}"
                    )
                    images_data[
                        "bbcode_images"
                    ] = f'{upload_image[1]} {images_data["bbcode_images"]}'
                    images_data[
                        "bbcode_images_nothumb"
                    ] = f'{upload_image[2]} {images_data["bbcode_images_nothumb"]}'
                    images_data[
                        "bbcode_thumb_nothumb"
                    ] = f'{upload_image[3]} {images_data["bbcode_thumb_nothumb"]}'
                    images_data[
                        "url_images"
                    ] = f'{upload_image[4]}\n{images_data["url_images"]}'
                    successfully_uploaded_image_count += 1
                    # Since the image uploaded successfully, we need to break now so we don't reupload to the backup image host (if exists)
                    break

        logging.info(
            "[Screenshots] Uploaded screenshots. Saving urls and bbcodes..."
        )
        with open(
            SCREENSHOTS_RESULT_FILE_PATH.format(
                base_path=base_path, sub_folder=hash_prefix
            ),
            "w",
        ) as screenshots_file:
            screenshots_file.write(json.dumps(images_data))

        # Depending on the image upload outcome we print a success or fail message showing the user what & how many images failed/succeeded
        if len(screenshots_to_upload_list) == successfully_uploaded_image_count:
            console.print(
                f"Uploaded {successfully_uploaded_image_count}/{len(screenshots_to_upload_list)} screenshots",
                style="sea_green3",
                highlight=False,
            )
            logging.info(
                f"[Screenshots] Successfully uploaded {successfully_uploaded_image_count}/{len(screenshots_to_upload_list)} screenshots"
            )
            upload_marker = Path(
                UPLOADS_COMPLETE_MARKER_PATH.format(
                    base_path=base_path, sub_folder=hash_prefix
                )
            )
            with upload_marker.open("w", encoding="utf-8") as f:
                f.write("ALL_SCREENSHOT_UPLOADED_SUCCESSFULLY")
                logging.debug(
                    "[Screenshots] Marking that all screenshots have been uploaded successfully"
                )
        else:
            console.print(
                f"{len(screenshots_to_upload_list) - successfully_uploaded_image_count}/{len(screenshots_to_upload_list)} screenshots failed to upload",
                style="bold red",
                highlight=False,
            )
            logging.error(
                f"[Screenshots] {len(screenshots_to_upload_list) - successfully_uploaded_image_count}/{len(screenshots_to_upload_list)} screenshots failed to upload"
            )
        return True  # indicates that screenshots are available
