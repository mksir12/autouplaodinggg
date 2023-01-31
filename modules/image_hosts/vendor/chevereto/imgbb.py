import base64
from typing import Dict

from .chevereto_base import CheveretoImageHostBase


class ImgbbImageHost(CheveretoImageHostBase):
    @property
    def files(self) -> Dict:
        return {}

    @property
    def headers(self) -> Dict:
        return {}

    @property
    def data(self) -> Dict:
        return {
            "key": self.api_key,
            "image": base64.b64encode(open(self.image_path, "rb").read()),
        }

    @property
    def img_host(self) -> str:
        return "imgbb"

    @property
    def response_data_key(self) -> str:
        return "data"

    @property
    def url(self) -> str:
        return "https://api.imgbb.com/1/upload"
