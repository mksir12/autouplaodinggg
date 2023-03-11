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

import enum
from typing import Union


# Using enum class create enumerations
class Clients(enum.Enum):
    Qbittorrent = 1
    Rutorrent = 2
    Deluge = 3
    Transmission = 4


class TorrentClientFactory:
    @staticmethod
    def create(client_type):
        return TorrentClient(globals()[client_type.name.capitalize()]())


class TorrentClient:
    client = None

    def __init__(self, client):
        """
        Class will contain a torrent client that is created based on the `client_type` provided by the user.
        TorrentClients are created via the TorrentClientFactory.
        """
        self.client = client

    def hello(self):
        self.client.hello()

    def list_torrents(self):
        return self.client.list_torrents()

    def upload_torrent(
        self,
        torrent,
        save_path,
        use_auto_torrent_management,
        is_skip_checking,
        category=None,
    ):
        self.client.upload_torrent(
            torrent,
            save_path,
            use_auto_torrent_management,
            is_skip_checking,
            category,
        )

    def update_torrent_category(
        self, info_hash, category_name: Union[str, None] = None
    ):
        self.client.update_torrent_category(info_hash, category_name)

    def get_dynamic_trackers(self, torrent):
        return self.client.get_dynamic_trackers(torrent)
