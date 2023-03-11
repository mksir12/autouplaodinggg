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

import binascii
import os
from abc import ABC, abstractmethod, ABCMeta
from functools import cached_property

from modules.exceptions.exception import GGBotUploaderException


def _strtobool(val):
    """Convert a string representation of truth to true (1) or false (0).

    True values are 'y', 'yes', 't', 'true', 'on', and '1'; false values
    are 'n', 'no', 'f', 'false', 'off', and '0'.  Raises GGBotUploaderException if
    'val' is anything else.
    """
    val = val.lower()
    if val in ("y", "yes", "t", "true", "on", "1"):
        return 1
    elif val in ("n", "no", "f", "false", "off", "0"):
        return 0
    else:
        raise GGBotUploaderException(f"invalid truth value {val!r}")


class GGBotConfig(ABC):
    @staticmethod
    def _get_property(key, default=None):
        return os.getenv(key, default)

    @staticmethod
    def _get_property_as_boolean(key: str, default: bool = False) -> bool:
        return bool(_strtobool(str(os.getenv(key, default))))

    def get_config(self, key, default=None):
        return self._get_property(key, default)


class UploaderConfig(GGBotConfig):
    @cached_property
    def CHECK_FOR_DUPES(self):
        return self._get_property_as_boolean("check_dupes")

    @property
    def SIGNATURE(self):
        return self._get_property("uploader_signature")

    @cached_property
    def READABLE_TEMP_DIR(self):
        return self._get_property_as_boolean("readable_temp_data")

    @property
    def DEFAULT_TRACKERS(self):
        return self._get_property("default_trackers_list", "")

    @property
    def TORRENT_CLIENT(self):
        return self._get_property("client")

    @property
    def DUPE_CHECK_SIMILARITY_THRESHOLD(self):
        return self._get_property("acceptable_similarity_percentage", 80)

    @cached_property
    def REUPLOADER(self):
        return (
            self._get_property("tmdb_result_auto_select_threshold") is not None
        )

    @property
    def TMDB_API_KEY(self):
        return self._get_property("TMDB_API_KEY")

    @property
    def IMDB_API_KEY(self):
        return self._get_property("IMDB_API_KEY")

    @cached_property
    def TRANSLATE_PATH(self):
        return self._get_property_as_boolean("translation_needed")

    @property
    def UPLOADER_PATH(self):
        return self._get_property(
            "uploader_accessible_path", "__MISCONFIGURED_PATH__"
        )

    @property
    def TORRENT_CLIENT_PATH(self):
        return self._get_property(
            "client_accessible_path", "__MISCONFIGURED_PATH__"
        )

    @property
    def NO_OF_SCREENSHOTS(self) -> int:
        return int(self._get_property("num_of_screenshots", 0))

    @property
    def BHD_LIVE(self):
        return self._get_property_as_boolean("live")


class UploadAssistantConfig(UploaderConfig):
    @cached_property
    def AUTO_MODE(self):
        return self._get_property_as_boolean("auto_mode")

    @cached_property
    def FORCE_AUTO_MODE(self):
        return self._get_property_as_boolean("force_auto_upload")

    @property
    def BD_INFO_LOCATION(self):
        return self._get_property("bdinfo_script")

    @cached_property
    def CONTAINERIZED(self):
        return self._get_property_as_boolean("IS_CONTAINERIZED")

    @cached_property
    def BD_SUPPORT(self):
        return self._get_property_as_boolean("IS_FULL_DISK_SUPPORTED")

    @property
    def TORRENT_MOVE_PATH(self):
        return self._get_property("dot_torrent_move_location")

    @property
    def MEDIA_MOVE_PATH(self):
        return self._get_property("media_move_location")

    @cached_property
    def ENABLE_TYPE_BASED_MOVE(self):
        return self._get_property_as_boolean("enable_type_base_move")

    @cached_property
    def ENABLE_POST_PROCESSING(self):
        return self._get_property_as_boolean("enable_post_processing")

    @property
    def POST_PROCESSING_MODE(self):
        return self._get_property("post_processing_mode")


class ReUploaderConfig(UploaderConfig):
    @property
    def CACHE(self):
        return self._get_property("cache_type")

    @cached_property
    def ENABLE_VISOR_SERVER(self):
        return self._get_property_as_boolean("ENABLE_VISOR_SERVER")

    @property
    def TMDB_AUTO_SELECT_THRESHOLD(self):
        return int(self._get_property("tmdb_result_auto_select_threshold", 1))

    @cached_property
    def DYNAMIC_TRACKER_SELECTION(self):
        return self._get_property_as_boolean("dynamic_tracker_selection")

    @property
    def REUPLOAD_LABEL(self):
        return self._get_property("reupload_label", "")

    @property
    def CROSS_SEED_LABEL(self):
        return self._get_property("cross_seed_label", "GGBotCrossSeed")

    @property
    def SOURCE_LABEL(self):
        return self._get_property("source_seed_label", "GGBotCrossSeed_Source")


class ClientConfig(GGBotConfig):
    @property
    def CLIENT_HOST(self):
        return self._get_property("client_host")

    @property
    def CLIENT_PORT(self):
        return self._get_property("client_port", "80")

    @property
    def CLIENT_USERNAME(self):
        return self._get_property("client_username")

    @property
    def CLIENT_PASSWORD(self):
        return self._get_property("client_password")

    @property
    def CLIENT_PATH(self):
        return self._get_property("client_path", "/")


class CacheConfig(GGBotConfig):
    @property
    def CACHE_TYPE(self):
        return self._get_property("cache_type")

    @property
    def CACHE_HOST(self):
        return self._get_property("cache_host")

    @property
    def CACHE_PORT(self):
        return self._get_property("cache_port")

    @property
    def CACHE_DATABASE(self):
        return self._get_property("cache_database")

    @property
    def CACHE_USERNAME(self):
        return self._get_property("cache_username")

    @property
    def CACHE_PASSWORD(self):
        return self._get_property("cache_username")


class APIKeyConfig(GGBotConfig, ABC):
    @property
    @abstractmethod
    def API_KEY(self):
        raise NotImplementedError


class ImageHostApiConfig(APIKeyConfig, metaclass=ABCMeta):
    pass


class ImageHostConfig(GGBotConfig, metaclass=ABCMeta):
    @property
    def THUMB_SIZE(self):
        return self._get_property("thumb_size", "350")

    @classmethod
    def IMAGE_HOST_BY_PRIORITY(cls, priority):
        return cls._get_property(f"img_host_{priority}")

    @classmethod
    def IMAGE_HOST_BY_API_KEY(cls, image_host):
        return cls._get_property(f"{image_host}_api_key")


class PTPImgConfig(ImageHostApiConfig):
    @property
    def API_KEY(self):
        return self._get_property("ptpimg_api_key")


class ImgurConfig(ImageHostApiConfig):
    @property
    def API_KEY(self):
        return self._get_property("imgur_api_key")

    @property
    def CLIENT_ID(self):
        return self._get_property("imgur_client_id")


class TrackerConfig(APIKeyConfig):
    def __init__(self, tracker):
        self.tracker = tracker.upper()

    @property
    def API_KEY(self):
        return self._get_property(f"{self.tracker}_API_KEY", "")

    @property
    def ANNOUNCE_URL(self):
        return self._get_property(f"{self.tracker}_ANNOUNCE_URL", None)


# caching the generated api key in memory to prevent key generation
# every time the `get_visor_api_key` method is invoked
generated_api_key = None


class VisorConfig(APIKeyConfig, GGBotConfig):
    def __init__(self):
        self.api_key = self._get_property("VISOR_API_KEY", None)
        # if user has not configured visor_api_key, we'll generate one.
        if self.api_key is None:
            global generated_api_key
            if generated_api_key is None:
                generated_api_key = str(
                    binascii.hexlify(os.urandom(16)), "UTF-8"
                )
                print(f"Generated visor server api key: {generated_api_key}")
            self.api_key = generated_api_key

    @cached_property
    def API_KEY(self):
        return self.api_key

    @property
    def PORT(self):
        return int(self._get_property("VISOR_SERVER_PORT", 30035))
