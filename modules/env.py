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

import os
from distutils import util

# This class will be used by the application to get all the environment variables
# This also allows to return defaults consistently across the whole application.
# Why is this full of method instead of variables??? ------ Backwards compatibility ------

# any method starting with is will be boolean and returns False by default
# TODO: should all these method be replaced with a single `is_enabled` method ??
def is_auto_mode():
    return bool(util.strtobool(str(os.getenv('auto_mode', False))))

def is_force_auto_upload():
    return bool(util.strtobool(str(os.getenv('force_auto_upload', False))))

def is_check_dupes():
    return bool(util.strtobool(str(os.getenv('check_dupes', False))))

def is_containerized():
    return bool(util.strtobool(str(os.getenv("IS_CONTAINERIZED", False))))

def is_full_disk_supported():
    return bool(util.strtobool(str(os.getenv("IS_FULL_DISK_SUPPORTED", False))))

def is_live():
    return bool(util.strtobool(str(os.getenv('live', False))))

def is_readble_temp_data_needed():
    return bool(util.strtobool(str(os.getenv("readable_temp_data", False))))

def get_image_host_by_priority(priority, default=None):
    return os.getenv(f'img_host_{priority}', default)

def get_image_host_api_key(image_host, default=None):
    return os.getenv(f'{image_host}_api_key', default)

def get_acceptable_similarity_percentage():
    return int(os.getenv('acceptable_similarity_percentage', 80))

def get_bdinfo_script_location(default=None):
    return os.getenv('bdinfo_script', default)

def get_tmdb_api_key(default=None):
    return os.getenv('TMDB_API_KEY', default)

def get_imdb_api_key(default=None):
    return os.getenv("IMDB_API_KEY", default)

def get_tmdb_result_auto_select_threshold(default=None):
    return os.getenv("tmdb_result_auto_select_threshold", default)

def get_uploader_signature(default=None):
    return os.getenv("uploader_signature", default)

def get_default_trackers_list(default=None):
    return os.getenv("default_trackers_list", default)

def get_tracker_announce_url(acryonym, default=None):
    return os.getenv(f"{acryonym.upper()}_ANNOUNCE_URL", default)

def get_property_or_default(env_key, default=None):
    return os.getenv(env_key, default)

# Translation properties
def is_translation_needed():
    return bool(util.strtobool(str(os.getenv('translation_needed', False))))

def get_uploader_accessible_path(default=''):
    return os.getenv('uploader_accessible_path', default)

def get_client_accessible_path(default=''):
    return os.getenv('client_accessible_path', default)
# Translation properties


# Screenshots properties
def is_no_spoiler_screenshot():
    return bool(util.strtobool(str(os.getenv("no_spoilers", False))))

def get_imgur_client_id(default=None):
    return os.getenv('imgur_client_id', default)

def get_imgur_api_key(default=None):
    return os.getenv('imgur_api_key', default)

def get_ptpimg_api_key(default=None):
    return os.getenv('ptpimg_api_key', default)

def get_num_of_screenshots():
    return os.getenv('num_of_screenshots', "0")

def get_thumb_size():
    return os.getenv('thumb_size', "350")
# Screenshots properties


# Post Processing properties
def is_post_processing_needed():
    return bool(util.strtobool(str(os.getenv('enable_post_processing', False))))

def is_type_based_move_enabled():
    return bool(util.strtobool(str(os.getenv('enable_type_base_move', False))))

def get_post_processing_mode(default=''):
    return os.getenv('post_processing_mode', default)

def get_media_move_location(default=None):
    return os.getenv('media_move_location', default)

def get_dot_torrent_move_location(default=None):
    return os.getenv('dot_torrent_move_location', default)
# Post Processing properties


# Client properties
def get_client_type():
    return os.getenv('client')

def get_client_host():
    return os.getenv("client_host")

def get_client_port():
    return os.getenv("client_port", "80")

def get_client_username():
    return os.getenv("client_username")

def get_client_password():
    return os.getenv("client_password")

def get_client_path():
    return os.getenv("client_path", "/")

def is_dynamic_tracker_selection_needed():
    return bool(util.strtobool(str(os.getenv("dynamic_tracker_selection", False))))

def get_reupload_label():
    return os.getenv('reupload_label', '')

def get_cross_seed_label():
    return os.getenv('cross_seed_label', 'GGBotCrossSeed')

def get_source_label():
    return os.getenv('source_seed_label', 'GGBotCrossSeed_Source')
# Client properties


# Cache properties
def get_cache_type():
    return os.getenv('cache_type')

def get_cache_username():
    return os.getenv('cache_username', None)

def get_cache_password():
    return os.getenv('cache_password')

def get_cache_host():
    return os.getenv('cache_host')

def get_cache_port():
    return os.getenv('cache_port')

def get_cache_database():
    return os.getenv('cache_database')
# Cache properties


# GGBOT Metadata Aggregator
def is_aggregator_enabled():
    return False

def gg_bot_metadata_aggregator():
    return None

def can_share_with_community():
    return False
# GGBOT Metadata Aggregator
