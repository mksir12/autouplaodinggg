import base64
from typing import Dict

from modules.image_hosts.vendor.chevereto.chevereto_base import (
    CheveretoImageHostBase,
)


class LensdumpImageHost(CheveretoImageHostBase):
    @property
    def data(self) -> Dict:
        return {
            "key": self.api_key,
            "format": "json",
            "source": base64.b64encode(open(self.image_path, "rb").read()),
        }

    @property
    def files(self) -> Dict:
        return {}

    @property
    def headers(self) -> Dict:
        return {"X-API-Key": self.api_key}

    @property
    def response_data_key(self) -> str:
        return "image"

    @property
    def url(self) -> str:
        return "https://lensdump.com/api/1/upload"

    @property
    def img_host(self) -> str:
        return "lensdump"
