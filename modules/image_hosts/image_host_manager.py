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

import logging
from typing import List

from rich.console import Console

from modules.image_hosts.image_host_base import GGBotImageHostBase
from modules.image_hosts.image_upload_status import GGBotImageUploadStatus
from modules.image_hosts.vendor.chevereto.freeimage import FreeImageImageHost
from modules.image_hosts.vendor.chevereto.imgbb import ImgbbImageHost
from modules.image_hosts.vendor.chevereto.imgfi import ImgFiImageHost
from modules.image_hosts.vendor.chevereto.lensdump import LensdumpImageHost
from modules.image_hosts.vendor.chevereto.snappie import SnappieImageHost
from modules.image_hosts.vendor.dummy import DummyImageHost
from modules.image_hosts.vendor.imgbox import ImgboxImageHost
from modules.image_hosts.vendor.imgur import ImgurImageHost
from modules.image_hosts.vendor.pixhost import PixhostImageHost
from modules.image_hosts.vendor.ptpimg import PTPImgImageHost
from modules.config import ImageHostConfig

# For more control over rich terminal content, import and construct a Console object.
console = Console()


class GGBotImageHostManager:
    def __init__(self, torrent_title):
        self.config = ImageHostConfig()
        self.image_hosts: List = self._get_valid_configured_image_hosts()
        self.thumb_size = self.config.THUMB_SIZE
        self.torrent_title = torrent_title

    @property
    def no_of_image_hosts(self) -> int:
        return len(self.image_hosts)

    def _get_valid_configured_image_hosts(self) -> List:
        # ---------------------- verify at least 1 image-host is set/enabled ---------------------- #
        # here we are looking for the number of image hosts enabled (img_host_1, img_host_2, img_host_3...)
        image_hosts = []
        index = 1
        while True:
            img_host = self.config.IMAGE_HOST_BY_PRIORITY(index)
            if img_host is None or len(img_host) == 0:
                break
            index += 1
            image_hosts.append(img_host)
        if len(image_hosts) == 0:
            logging.error(
                "[GGBotScreenshotManager::init] All image-hosts are disabled/not set "
                '(try setting "img_host_1=imgbox" in config.env)'
            )
        else:
            logging.info(
                f"[GGBotScreenshotManager::init] User has configured the following image hosts: "
                f"{image_hosts}"
            )
        return self._remove_image_hosts_without_api_key(image_hosts)

    @staticmethod
    def _remove_image_hosts_without_api_key(image_hosts) -> List:
        valid_image_hosts = []
        for image_host in image_hosts:
            # Check if an API key is set for the image host
            logging.debug(
                f"[GGBotScreenshotManager::init] Doing api key validation for {image_host}"
            )
            if ImageHostConfig().IMAGE_HOST_BY_API_KEY(image_host) is not None:
                valid_image_hosts.append(image_host)
                continue
            logging.error(
                f"[GGBotScreenshotManager::init]Can't upload to {image_host} without an API key"
            )
            console.print(
                f"\nCan't upload to [bold]{image_host}[/bold] without an API key\n",
                style="red3",
                highlight=False,
            )
        return valid_image_hosts

    def upload_screenshots(self, image_path: str) -> GGBotImageUploadStatus:
        for image_host in self.image_hosts:
            image_host_manager: GGBotImageHostBase = (
                self._create_image_host_uploader(
                    image_path=image_path, image_host=image_host
                )
            )
            assert image_host_manager is not None
            image_host_manager.upload()
            status: GGBotImageUploadStatus = image_host_manager.status
            if status.status:
                logging.debug(
                    f"[Screenshots] Response from image host: {status}"
                )
                return status
        return GGBotImageUploadStatus(status=False)

    def _create_image_host_uploader(
        self, *, image_host: str, image_path: str
    ) -> GGBotImageHostBase:
        if image_host == "DUMMY":
            return DummyImageHost(image_path=image_path)
        if image_host == "pixhost":
            return PixhostImageHost(image_path=image_path)
        if image_host == "imgur":
            return ImgurImageHost(image_path=image_path)
        if image_host == "ptpimg":
            return PTPImgImageHost(image_path=image_path)
        if image_host == "imgbb":
            return ImgbbImageHost(image_path=image_path)
        if image_host == "freeimage":
            return FreeImageImageHost(image_path=image_path)
        if image_host == "imgfi":
            return ImgFiImageHost(image_path=image_path)
        if image_host == "snappie":
            return SnappieImageHost(image_path=image_path)
        if image_host == "lensdump":
            return LensdumpImageHost(image_path=image_path)
        if image_host == "imgbox":
            return ImgboxImageHost(
                image_path=image_path, torrent_title=self.torrent_title
            )
        logging.fatal(
            f"[GGBotImageHostManager::upload_screenshots] Invalid image host {image_host}. Cannot upload screenshots."
        )
        # TODO: what should be done here?
