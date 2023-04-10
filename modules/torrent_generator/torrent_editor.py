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
from typing import List

from modules.torrent_generator.torf_generator import GGBOTTorrent


class GGBotTorrentEditor:
    def __init__(self, torrent_prefix):
        self.torrent_prefix = torrent_prefix

    def edit_torrent(
        self, *, announce: List, tracker: str, source: str, torrent_title: str
    ):
        # just choose whichever, doesn't really matter since we replace the same info anyway
        edit_torrent = GGBOTTorrent.read(
            glob.glob(f"{self.torrent_prefix}*.torrent")[0]
        )

        if len(announce) == 1:
            logging.debug(
                f"[DotTorrentGeneration] Only one announce url provided for tracker {tracker}."
            )
            self._remove_announce_list(edit_torrent=edit_torrent)
        else:
            logging.debug(
                f"[DotTorrentGeneration] Multiple announce urls provided for tracker {tracker}. Updating announce-list"
            )
            self._add_all_announce_urls(
                edit_torrent=edit_torrent, announce=announce
            )

        edit_torrent.metainfo["announce"] = announce[0]
        edit_torrent.metainfo["info"]["source"] = source
        # Edit the previous .torrent and save it as a new copy
        GGBOTTorrent.copy(edit_torrent).write(
            filepath=f"{self.torrent_prefix}{tracker}-{torrent_title}.torrent",
            overwrite=True,
        )

    @staticmethod
    def _remove_announce_list(*, edit_torrent: GGBOTTorrent):
        logging.debug(
            "[GGBotTorrentEditor] Removing announce-list if present in existing torrent."
        )
        edit_torrent.metainfo.pop("announce-list", "")

    @staticmethod
    def _add_all_announce_urls(*, edit_torrent: GGBOTTorrent, announce: List):
        edit_torrent.metainfo.pop("announce-list", "")
        edit_torrent.metainfo["announce-list"] = []
        for announce_url in announce:
            logging.debug(
                f"[DotTorrentGeneration] Adding secondary announce url {announce_url}"
            )
            edit_torrent.metainfo["announce-list"].append([announce_url])
        logging.debug(
            f"[DotTorrentGeneration] Final announce-list in torrent metadata {edit_torrent.metainfo['announce-list']}"
        )
