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

import logging
import math
from functools import cached_property
from typing import Callable

from torf import Torrent

from modules.torrent_generator.generator_base import GGBotTorrentGeneratorBase


class GGBOTTorrent(Torrent):
    piece_size_max = 32 * 1024 * 1024  # 32MB as max piece size


class GGBotTorfTorrentGenerator(GGBotTorrentGeneratorBase):
    def __init__(
        self,
        *,
        media,
        announce,
        source,
        torrent_title,
        torrent_path_prefix,
        progress_callback: Callable,
    ):
        super().__init__(
            media=media,
            announce=announce,
            source=source,
            torrent_title=torrent_title,
            torrent_path_prefix=torrent_path_prefix,
        )
        self.torrent = GGBOTTorrent(
            path=self.media,
            trackers=self.announce,
            source=self.source,
            comment=self.comment,
            created_by=self.created_by,
            exclude_globs=self.default_exclude_globs,
            private=self.private,
            creation_date=self.created_at,
        )
        self.progress_callback = progress_callback

    @cached_property
    def size(self):
        return self.torrent.size

    def get_piece_size(self) -> int:
        """
        Return the piece size for a total torrent size of ``size`` bytes

        For torrents up to 1 GiB, the maximum number of pieces is 1024 which
        means the maximum piece size is 1 MiB.  With increasing torrent size
        both the number of pieces and the maximum piece size are gradually
        increased up to 10,240 pieces of 8 MiB.  For torrents larger than 80 GiB
        the piece size is :attr:`piece_size_max` with as many pieces as
        necessary.

        It is safe to override this method to implement a custom algorithm.

        :return: calculated piece size
        """
        pieces = self.size / 4096  # 32 MiB max
        if self.size <= 1 * 2**30:  # 1 GiB / 1024 pieces = 1 MiB max
            pieces = self.size / 1024
        elif self.size <= 2 * 2**30:  # 2 GiB / 2048 pieces = 2 MiB max
            pieces = self.size / 1024
        elif self.size <= 4 * 2**30:  # 4 GiB / 2048 pieces = 2 MiB max
            pieces = self.size / 1024
        elif self.size <= 8 * 2**30:  # 8 GiB / 2048 pieces = 4 MiB max
            pieces = self.size / 2048
        elif self.size <= 16 * 2**30:  # 16 GiB / 2048 pieces = 8 MiB max
            pieces = self.size / 2048
        elif self.size <= 32 * 2**30:  # 32 GiB / 2048 pieces = 16 MiB max
            pieces = self.size / 2048
        elif self.size <= 64 * 2**30:  # 64 GiB / 4096 pieces = 16 MiB max
            pieces = self.size / 4096
        elif self.size > 64 * 2**30:
            pieces = self.size / 4096  # 32 MiB max
        # Math is magic!
        # piece_size_max :: 32 * 1024 * 1024 => 16MB
        return int(
            min(
                max(1 << max(0, math.ceil(math.log(pieces, 2))), 16 * 1024),
                32 * 1024 * 1024,
            )
        )

    def generate_torrent(self) -> None:
        print("Using python torf to generate the torrent")
        logging.info(
            f"[GGBotTorfTorrentGenerator] Size of the torrent: {self.torrent.size}"
        )
        logging.info(
            f"[GGBotTorfTorrentGenerator] Piece Size of the torrent: {self.torrent.piece_size}"
        )
        self.torrent.generate(callback=self.progress_callback)
        self.torrent.write(self.torrent_path)

    def do_post_generation_task(self) -> None:
        self.torrent.verify_filesize(self.media)
        logging.info(
            "[GGBotTorfTorrentGenerator] Trying to write into {}".format(
                "[" + self.source + "]" + self.torrent_title + ".torrent"
            )
        )
