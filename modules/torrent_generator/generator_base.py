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

from abc import ABC, abstractmethod
from datetime import datetime
from functools import cached_property
from typing import List


class GGBotTorrentGeneratorBase(ABC):
    def __init__(
        self, *, media, announce, source, torrent_title, torrent_path_prefix
    ):
        self.media = media
        self.announce = announce
        self.source = source
        self.private = True
        self.comment = "Torrent created by GG-Bot Upload Assistant"
        self.created_by = "GG-Bot Upload Assistant"
        self.created_at = datetime.now()
        self.torrent_title = torrent_title
        self.torrent_path = f"{torrent_path_prefix}-{torrent_title}.torrent"

    @cached_property
    def default_exclude_globs(self) -> List:
        return [
            "*.txt",
            "*.jpg",
            "*.png",
            "*.nfo",
            "*.svf",
            "*.rar",
            "*.screens",
            "*.sfv",
        ]

    @cached_property
    @abstractmethod
    def size(self):
        raise NotImplementedError

    @abstractmethod
    def get_piece_size(self) -> int:
        raise NotImplementedError

    @abstractmethod
    def generate_torrent(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def do_post_generation_task(self) -> None:
        raise NotImplementedError
