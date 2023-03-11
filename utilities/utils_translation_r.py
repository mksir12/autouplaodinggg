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

from rich.console import Console

from modules.translations.hybrid_mapper import GGBotHybridMapper

console = Console()


class GGBotTranslationManager:
    def __init__(self, *, torrent_info):
        self.ggbot_hybrid_mapper: GGBotHybridMapper = None
        self.source_type: str = torrent_info.get("source_type")
        self.screen_size: str = torrent_info.get("screen_size")
        self.bluray_disc_type: str = torrent_info.get("bluray_disc_type")
        self.type = torrent_info["type"]
        self.imdb = torrent_info["imdb"]
        self.imdb_with_tt = torrent_info["imdb_with_tt"]
        self.tmdb = torrent_info["tmdb"]
        self.tvdb = torrent_info["tvdb"]
        self.mal = torrent_info["mal"]
        self.tvmaze = torrent_info["tvmaze"]
        logging.debug(
            f"The relevant torrent info values for resolution / source identification are: "
            f"[Source Type: {self.source_type}, [Screen Size: {self.screen_size}], [Bluray: {self.bluray_disc_type}]"
        )

    def _get_url_type_data(self, key):
        url = ""
        if key == "imdb":
            url = f"https://www.imdb.com/title/{self.imdb_with_tt}"
        elif key == "tmdb":
            url = f"https://www.themoviedb.org/{'movie' if self.type == 'movie' else 'tv'}/{self.tmdb}"
        elif key == "tvdb" and self.type == "episode":
            url = f"https://www.thetvdb.com/?tab=series&id={self.tvdb}"
        elif key == "mal":
            url = f"https://myanimelist.net/anime/{self.mal}"
        elif key == "tvmaze" and self.type == "episode":
            url = f"https://www.tvmaze.com/shows/{self.tvmaze}"
        else:
            logging.error(
                f"[GGBotTranslationManager] Invalid key for url translation provided -- Key {key}"
            )
        logging.debug(
            f"[GGBotTranslationManager] Created url type data for {key} as {url}"
        )
        return url

    @staticmethod
    def _get_bluray_region(optional_value, expected_region):
        for region in optional_value:
            if str(region).upper() == str(expected_region).upper():
                return region
        return None
