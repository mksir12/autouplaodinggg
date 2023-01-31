from abc import abstractmethod, ABC

from .image_upload_status import GGBotImageUploadStatus
import modules.env as Environment


class GGBotImageHostBase(ABC):
    def __init__(self, image_path: str):
        self.thumb_size = Environment.get_thumb_size()
        self.upload_status: GGBotImageUploadStatus = GGBotImageUploadStatus(
            status=False
        )
        self.image_path = image_path

    @property
    def status(self) -> GGBotImageUploadStatus:
        return self.upload_status

    @property
    @abstractmethod
    def img_host(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def upload(self):
        raise NotImplementedError
