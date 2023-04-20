from typing import Dict

from modules.image_hosts.vendor.chevereto.chevereto_base import (
    CheveretoImageHostBase,
)


class SnappieImageHost(CheveretoImageHostBase):
    @property
    def data(self) -> Dict:
        return {"key": self.api_key}

    @property
    def files(self) -> Dict:
        return {"source": open(self.image_path, "rb")}

    @property
    def headers(self) -> Dict:
        return {}

    @property
    def response_data_key(self) -> str:
        return "image"

    @property
    def url(self) -> str:
        return "https://snappie.net/api/1/upload"

    @property
    def img_host(self) -> str:
        return "snappie"
