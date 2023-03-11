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

import glob
import logging
import os
from functools import cached_property
from pathlib import Path

from modules.torrent_generator.generator_base import GGBotTorrentGeneratorBase
from modules.torrent_generator.torf_generator import GGBOTTorrent


class GGBotMkTorrentGenerator(GGBotTorrentGeneratorBase):
    """
    mktorrent options
        -v => Be verbose.
        -p => Set the private flag.
        -a => Specify the full announce URLs.  Additional -a adds backup trackers.
        -o => Set the path and filename of the created file.  Default is <name>.torrent.
        -c => Add a comment to the metainfo.
        -s => Add source string embedded in infohash.
        -l => piece size (potency of 2)

        -e *.txt,*.jpg,*.png,*.nfo,*.svf,*.rar,*.screens,*.sfv
        # TODO to be added when supported mktorrent is available in alpine
    current version of mktorrent pulled from alpine package doesn't have the -e flag.
    Once an updated version is available, the flag can be added
    """

    def __init__(
        self, *, media, announce, source, torrent_title, torrent_path_prefix
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

    @cached_property
    def size(self):
        return (
            self._get_size_of_dir()
            if os.path.isdir(self.media)
            else os.path.getsize(self.media)
        )

    def _get_size_of_dir(self):
        return sum(
            f.stat().st_size
            for f in Path(self.media).glob("**/*")
            if f.is_file()
        )

    def get_piece_size(self) -> int:
        """
        How pieces are calclated when using mktorrent...

        2^19 = 524 288 = 512 KiB for filesizes between 512 MiB - 1024 MiB
        2^20 = 1 048 576 = 1024 KiB for filesizes between 1 GiB - 2 GiB
        2^21 = 2 097 152 = 2048 KiB for filesizes between 2 GiB - 4 GiB
        2^22 = 4 194 304 = 4096 KiB for filesizes between 4 GiB - 8 GiB
        2^23 = 8 388 608 = 8192 KiB for filesizes between 8 GiB - 16 GiB
        2^24 = 16 777 216 = 16384 KiB for filesizes between 16 GiB - 512 GiB This is the max you should ever have to use.
        2^25 = 33 554 432 = 32768 KiB (note that utorrent versions before 3.x CANNOT load torrents with this or higher piece-size)
        """
        if self.size <= 2**30:  # < 1024 MiB
            return 19
        elif self.size <= 2 * 2**30:  # 1 GiB - 2 GiB
            return 20
        elif self.size <= 4 * 2**30:  # 2 GiB - 4 GiB
            return 21
        elif self.size <= 8 * 2**30:  # 4 GiB - 8 GiB
            return 22
        elif self.size <= 16 * 2**30:  # 8 GiB - 16 GiB
            return 23
        elif self.size <= 64 * 2**30:  # 16 GiB - 64 GiB
            return 24
        else:  # anything > 64 GiB
            return 25

    def generate_torrent(self) -> None:
        logging.info(
            f"[GGBotMkTorrentGenerator] Size of the torrent: {self.size}"
        )
        logging.info(
            f"[GGBotMkTorrentGenerator] Piece Size of the torrent: {self.get_piece_size()}"
        )
        os.system(
            f"mktorrent -v -p -l {self.get_piece_size()} -c \"{self.comment}\" -s '{self.source}' "
            f'-a \'{self.announce[0]}\' -o "{self.torrent_path}" "{self.media}"'
        )
        logging.info(
            "[GGBotMkTorrentGenerator] Mktorrent .torrent write into {}".format(
                "[" + self.source + "]" + self.torrent_title + ".torrent"
            )
        )

    def do_post_generation_task(self) -> None:
        logging.info(
            "[GGBotMkTorrentGenerator] Using torf to do some cleanup on the created torrent"
        )
        edit_torrent: GGBOTTorrent = GGBOTTorrent.read(
            glob.glob(self.torrent_path)[0]
        )
        edit_torrent.created_by = self.created_by
        edit_torrent.metainfo["created by"] = self.created_by
        if len(self.announce) > 1:
            # multiple announce urls
            edit_torrent.metainfo["announce-list"] = []
            for announce_url in self.announce:
                edit_torrent.metainfo["announce-list"].append([announce_url])
        GGBOTTorrent.copy(edit_torrent).write(
            filepath=self.torrent_path,
            overwrite=True,
        )
