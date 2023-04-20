import logging

import requests
from rich.console import Console

from modules.image_hosts.image_host_base import GGBotImageHostBase
from modules.image_hosts.image_upload_status import GGBotImageUploadStatus

# For more control over rich terminal content, import and construct a Console object.
console = Console()


class PixhostImageHost(GGBotImageHostBase):
    def __init__(self, image_path):
        super().__init__(image_path=image_path)

    @property
    def img_host(self) -> str:
        return "pixhost"

    def upload(self):
        data = {"content_type": "0", "max_th_size": self.thumb_size}
        files = {"img": open(self.image_path, "rb")}
        img_upload_request = requests.post(
            url="https://api.pixhost.to/images", data=data, files=files
        )

        img_upload_response = img_upload_request.json()
        if img_upload_request.ok:
            logging.debug(
                f"[PixhostImageHost::upload] Image upload response: {img_upload_response}"
            )
            image_url = (
                img_upload_response["th_url"]
                .replace("t77", "img77")
                .replace("/thumbs/", "/images/")
            )
            self.upload_status = GGBotImageUploadStatus(
                status=True,
                bb_code_medium_thumb=f'[url={img_upload_response["show_url"]}][img={self.thumb_size}]{image_url}[/img][/url]',
                bb_code_medium=f'[url={img_upload_response["show_url"]}][img]{image_url}[/img][/url]',
                bb_code_thumb=f'[url={img_upload_response["show_url"]}][img]{img_upload_response["th_url"]}[/img][/url]',
                image_url=image_url,
            )
        else:
            logging.error(
                f"[PixhostImageHost::upload] {self.img_host} upload failed. JSON Response: {img_upload_response}"
            )
            console.print(
                f"{self.img_host} upload failed. Status code: [bold]{img_upload_request.status_code}[/bold]",
                style="red3",
                highlight=False,
            )
