import base64
from typing import Dict

from modules.image_hosts.vendor.chevereto.chevereto_base import (
    CheveretoImageHostBase,
)


class FreeImageImageHost(CheveretoImageHostBase):
    @property
    def data(self) -> Dict:
        return {
            "key": self.api_key,
            "image": base64.b64encode(open(self.image_path, "rb").read()),
        }

    @property
    def files(self) -> Dict:
        return {}

    @property
    def headers(self) -> Dict:
        return {}

    @property
    def url(self) -> str:
        return "https://freeimage.host/api/1/upload"

    @property
    def response_data_key(self) -> str:
        return "image"

    @property
    def img_host(self) -> str:
        return "freeimage"
