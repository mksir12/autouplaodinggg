import logging
from abc import ABCMeta, abstractmethod
from typing import Dict

import requests
from rich.console import Console

from modules.config import ImageHostConfig
from modules.image_hosts.image_host_base import GGBotImageHostBase
from modules.image_hosts.image_upload_status import GGBotImageUploadStatus

# For more control over rich terminal content, import and construct a Console object.
console = Console()


class CheveretoImageHostBase(GGBotImageHostBase, metaclass=ABCMeta):
    def __init__(self, image_path: str):
        super().__init__(image_path)
        self.api_key = ImageHostConfig().IMAGE_HOST_BY_API_KEY(self.img_host)

    @property
    @abstractmethod
    def data(self) -> Dict:
        raise NotImplementedError

    @property
    @abstractmethod
    def files(self) -> Dict:
        raise NotImplementedError

    @property
    @abstractmethod
    def headers(self) -> Dict:
        raise NotImplementedError

    @property
    @abstractmethod
    def response_data_key(self) -> str:
        raise NotImplementedError

    @property
    @abstractmethod
    def url(self) -> str:
        raise NotImplementedError

    def upload(self):
        try:
            img_upload_request = requests.post(
                url=self.url,
                data=self.data,
                files=self.files,
                headers=self.headers,
            )
            if img_upload_request.ok:
                img_upload_response = img_upload_request.json()
                logging.debug(
                    f"[CheveretoImageHostBase::upload] Image upload response: {img_upload_response} from host {self.img_host}"
                )
                self.parse_response(img_upload_response)
            else:
                logging.error(
                    f"[CheveretoImageHostBase::upload] {self.img_host} upload failed. JSON Response: {img_upload_request.json()}"
                )
                console.print(
                    f"{self.img_host} upload failed. Status code: [bold]{img_upload_request.status_code}[/bold]",
                    style="red3",
                    highlight=False,
                )
        except requests.exceptions.RequestException:
            logging.exception(
                f"[CheveretoImageHostBase::upload] Failed to upload {self.image_path} to {self.img_host}"
            )
            console.print(
                f"upload to [bold]{self.img_host}[/bold] has failed!",
                style="Red",
            )

    def parse_response(self, img_upload_response: Dict) -> None:
        try:
            # By default, we'll use the original image to fill the response
            self.upload_status = GGBotImageUploadStatus(
                status=True,
                bb_code_medium_thumb=f'[url={img_upload_response["url_viewer"]}][img={self.thumb_size}]{img_upload_response["url"]}[/img][/url]',
                bb_code_medium=f'[url={img_upload_response["url_viewer"]}][img]{img_upload_response["url"]}[/img][/url]',
                bb_code_thumb=f'[url={img_upload_response["url_viewer"]}][img]{img_upload_response["url"]}[/img][/url]',
                image_url=img_upload_response["url"],
            )
            if "thumb" in img_upload_response:
                self.upload_status.bb_code_medium_thumb = f'[url={img_upload_response["url_viewer"]}][img={self.thumb_size}]{img_upload_response["thumb"]["url"]}[/img][/url]'
                self.upload_status.bb_code_medium = f'[url={img_upload_response["url_viewer"]}][img]{img_upload_response["thumb"]["url"]}[/img][/url]'
                self.upload_status.bb_code_thumb = f'[url={img_upload_response["url_viewer"]}][img]{img_upload_response["thumb"]["url"]}[/img][/url]'

            if "medium" in img_upload_response:
                self.upload_status.bb_code_medium_thumb = f'[url={img_upload_response["url_viewer"]}][img={self.thumb_size}]{img_upload_response["medium"]["url"]}[/img][/url] '
                self.upload_status.bb_code_medium = f'[url={img_upload_response["url_viewer"]}][img]{img_upload_response["medium"]["url"]}[/img][/url]'
                self.upload_status.bb_code_thumb = f'[url={img_upload_response["url_viewer"]}][img]{img_upload_response["medium"]["url"]}[/img][/url]'

            if "thumb" in img_upload_response:
                # if thumbnail is present, then we'll prefer that for `bb_code_thumb`
                self.upload_status.bb_code_thumb = f'[url={img_upload_response["url_viewer"]}][img]{img_upload_response["thumb"]["url"]}[/img][/url]'
        except KeyError as key_error:
            logging.error(
                f"[CheveretoImageHostBase::parse_response] {self.img_host} json KeyError: {key_error}"
            )
            self.upload_status = GGBotImageUploadStatus(status=False)
