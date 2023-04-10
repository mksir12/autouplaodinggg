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

from abc import abstractmethod, ABC

from modules.image_hosts.image_upload_status import GGBotImageUploadStatus
from modules.config import ImageHostConfig


class GGBotImageHostBase(ABC):
    def __init__(self, image_path: str):
        self.thumb_size = ImageHostConfig().THUMB_SIZE
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
