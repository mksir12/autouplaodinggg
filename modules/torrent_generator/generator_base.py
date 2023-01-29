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
