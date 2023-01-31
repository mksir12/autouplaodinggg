import logging
from typing import List

from rich.console import Console

import modules.env as Environment
from .image_host_base import GGBotImageHostBase
from .image_upload_status import GGBotImageUploadStatus
from .vendor.chevereto.freeimage import FreeImageImageHost
from .vendor.chevereto.imgbb import ImgbbImageHost
from .vendor.chevereto.imgfi import ImgFiImageHost
from .vendor.chevereto.lensdump import LensdumpImageHost
from .vendor.chevereto.snappie import SnappieImageHost
from .vendor.dummy import DummyImageHost
from .vendor.imgbox import ImgboxImageHost
from .vendor.imgur import ImgurImageHost
from .vendor.pixhost import PixhostImageHost
from .vendor.ptpimg import PTPImgImageHost

# For more control over rich terminal content, import and construct a Console object.
console = Console()


class GGBotImageHostManager:
    def __init__(self, torrent_title):
        self.image_hosts: List = self._get_valid_configured_image_hosts()
        self.thumb_size = Environment.get_thumb_size()
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
            img_host = Environment.get_image_host_by_priority(index)
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
            if Environment.get_image_host_api_key(image_host) is not None:
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
