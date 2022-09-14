# GG Bot Upload Assistant
# Copyright (C) 2022  Noob Master669

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import base64
import logging
import requests
import modules.env as Environment

rutorrent_keys = ["d.get_custom1", "d.get_bytes_done", "d.get_base_path", "hash", "d.get_name", "d.get_size_bytes"]
rutorrent_keys_translation = {
    "d.get_custom1": "category",
    "d.get_bytes_done": "completed",
    "d.get_base_path": "content_path",
    "d.get_name": "name",
    "d.get_size_bytes": "size"
}


class Rutorrent:

    __connection_check_path = "/plugins/check_port/action.php?init"
    __cpu_load_path = "/plugins/cpuload/action.php"
    __disk_size_path = "/plugins/diskspace/action.php"
    __default_path = "/plugins/httprpc/action.php"
    __upload_torrent_path = "/php/addtorrent.php"

    def __call_server(self, url, data=None, files=None, header=None):
        response = requests.post(url, data=data if data is not None else {}, files=files, headers=header or self.header)
        return response.json() if 'application/json' in response.headers.get('Content-Type') else response

    def __get_torrent_info(self, item):
        key = item[0]
        data = item[1]
        return {
            'hash': key,
            'd.is_open': data[0],
            'd.is_hash_checking': data[1],
            'd.is_hash_checked': data[2],
            'd.get_state': data[3],
            'd.get_name': data[4],
            'd.get_size_bytes': data[5],
            'd.get_completed_chunks': data[6],
            'd.get_size_chunks': data[7],
            'd.get_bytes_done': data[8],
            'd.get_up_total': data[9],
            'd.get_ratio': data[10],
            'd.get_up_rate': data[11],
            'd.get_down_rate': data[12],
            'd.get_chunk_size': data[13],
            'd.get_custom1': data[14],
            'd.get_peers_accounted': data[15],
            'd.get_peers_not_connected': data[16],
            'd.get_peers_connected': data[17],
            'd.get_peers_complete': data[18],
            'd.get_left_bytes': data[19],
            'd.get_priority': data[20],
            'd.get_state_changed': data[21],
            'd.get_skip_total': data[22],
            'd.get_hashing': data[23],
            'd.get_chunks_hashed': data[24],
            'd.get_base_path': data[25],
            'd.get_creation_date': data[26],
            'd.get_tracker_focus': data[27],
            'd.is_active': data[28],
            'd.get_message': data[29],
            'd.get_custom2': data[30],
            'd.get_free_diskspace': data[31],
            'd.is_private': data[32],
            'd.is_multi_file': data[33]
        }

    def get_dynamic_trackers(self, torrent):
        # a sanity check just to be sure
        if self.dynamic_tracker_selection == True:
            # this torrent is the translated data hence category instead of d.custom1
            category = torrent["category"]
            # removing any trailing ::
            if category.endswith("::"):
                category = category[:-2]
            trackers = category.split("::")
            return trackers[1:] # first entry will always be GGBOT
        else:
            return []

    def __match_label(self, torrent):
        # we don't want to consider cross-seeded torrents uploaded by the bot
        if self.seed_label == torrent["d.get_custom1"]:
            return False
        # user wants to ignore labels, hence we'll consider all the torrents
        if self.target_label == "IGNORE_LABEL":
            return True
        # if dynamic tracker selection is enabled, then labels will follow the pattern GGBOT::TR1::TR2::TR3
        if self.dynamic_tracker_selection == True:
            return torrent["d.get_custom1"].startswith(self.target_label)
        else:
            return torrent["d.get_custom1"] == self.target_label

    def __do_key_translation(self, key):
        return rutorrent_keys_translation[key] if key in rutorrent_keys_translation else key

    def __extract_necessary_keys(self, torrent):
        torrent = {self.__do_key_translation(key): value for key, value in torrent.items() if key in rutorrent_keys}
        torrent["save_path"] = torrent["content_path"].replace(torrent["name"], "")
        torrent["category"]=torrent["category"].replace("%3A",":")
        return torrent

    def __format_bytes(self, size):
        # 2**10 = 1024
        power = 2**10
        n = 0
        power_labels = {0: '', 1: 'K', 2: 'M', 3: 'G', 4: 'T'}
        while size > power:
            size /= power
            n += 1
        return f"{int(size)} {power_labels[n]}B"

    def __init__(self):
        self.host = Environment.get_client_host()
        if self.host is None or len(self.host) == 0:
            raise Exception("Invalid RuTorrent host provided")

        self.port = Environment.get_client_port()
        self.username = Environment.get_client_username()
        self.password = Environment.get_client_password()
        self.path = Environment.get_client_path()
        self.base_url = f'{self.host}:{self.port}{self.path}'

        if self.username:
            hashed = base64.b64encode(f"{self.username}:{self.password or ''}".encode('ascii')).decode('ascii')
            self.header = {"Authorization": f"Basic {hashed}"}
        else:
            self.header = {}
        self.dynamic_tracker_selection = Environment.is_dynamic_tracker_selection_needed()
        if self.dynamic_tracker_selection == True:
            # reuploader running in dynamic tracker selection mode
            self.target_label = "GGBOT"
        else:
            # `target_label` is the label of the torrents that we are interested in
            self.target_label = Environment.get_reupload_label()
        # `seed_label` is the label which will be added to the cross-seeded torrents
        self.seed_label = Environment.get_cross_seed_label()
        # `source_label` is thelabel which will be added to the original torrent in the client
        self.source_label = f"{self.seed_label}_Source"

        try:
            logging.info("[Rutorrent] Checking connection to Rutorrent")
            self.__call_server(f'{self.base_url}{self.__connection_check_path}')
            print('Successfully established connection with Rutorrent')
        except Exception as err:
            logging.fatal("[Rutorrent] Authentication with Rutorrent instance failed")
            raise err

    def hello(self):
        response = self.__call_server(f'{self.base_url}{self.__cpu_load_path}')
        try:
            print(f"Rutorrent CPU Load: {response['load']}%")
            response = self.__call_server(f'{self.base_url}{self.__disk_size_path}')
            print(f"Rutorrent Storage: {self.__format_bytes(response['free'])} free out of {self.__format_bytes(response['total'])}")
        except Exception as err:
            logging.fatal(f"Failed to connect to rutorrent. Error:{response.text}")
            raise err

    def list_torrents(self):
        response = self.__call_server(f'{self.base_url}{self.__default_path}', data={'mode': 'list'})
        if isinstance(response["t"], list):
            return []
        return list(map(self.__extract_necessary_keys, filter(self.__match_label, map(self.__get_torrent_info, response["t"].items()))))

    def upload_torrent(self, torrent, save_path, use_auto_torrent_management, is_skip_checking, category=None):
        category = category if category is not None else self.seed_label
        logging.info(f"[Rutorrent] Uploading torrent with category {category}")
        self.__call_server(
            f'{self.base_url}{self.__upload_torrent_path}',
            data={ "fast_resume": "1" if is_skip_checking else "0", "label": category, "dir_edit": save_path},
            files={"torrent_file": open(torrent, "rb")}
        )

    def update_torrent_category(self, info_hash, category_name=None):
        category_name = category_name if category_name is not None else self.source_label
        logging.info(f"[Rutorrent] Updating category of torrent with hash {info_hash} to {category_name}")
        response = self.__call_server(f'{self.base_url}{self.__default_path}', data={"mode": "setlabel", "hash": info_hash, "v": category_name, "s": "label"})
        if response[0] == category_name:
            logging.info(f"[Rutorrent] Successfully updated category of torrent with hash {info_hash} to {category_name}")
        else:
            logging.error(f"[RuTorrent] Failed to update category of torrent with hash {info_hash} to {category_name}")
