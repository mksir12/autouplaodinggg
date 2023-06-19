# General constants
COOKIES_DUMP_DIR = "{base_path}/cookies/"
SITE_TEMPLATES_DIR = "{base_path}/site_templates/"
VALIDATED_SITE_TEMPLATES_DIR = "{base_path}/validated/site_templates/"
EXTERNAL_SITE_TEMPLATES_DIR = "{base_path}/external/site_templates/"
EXTERNAL_TRACKER_ACRONYM_MAPPING = (
    "{base_path}/external/tracker/tracker_to_acronym.json"
)

TRACKER_ACRONYMS = "{base_path}/parameters/tracker/acronyms.json"
TRACKER_API_KEYS = "{base_path}/parameters/tracker/api_keys.json"
TEMPLATE_SCHEMA_LOCATION = "{base_path}/schema/site_template_schema.json"

# Working dir paths
# Note: The `sub_folder` is expected to end with a '/'
WORKING_DIR = "{base_path}/temp_upload/"

__MEDIAINFO_FILE = "{sub_folder}mediainfo.txt"
__URL_IMAGES_FILE = "{sub_folder}url_images.txt"
__SCREENSHOTS_DIR = "{sub_folder}screenshots/"
__DESCRIPTION_FILE = "{sub_folder}description.txt"
__BBCODE_IMAGES_FILE = "{sub_folder}bbcode_images.txt"
__SCREENSHOTS_RESULT_FILE = "{sub_folder}screenshots/screenshots_data.json"
__UPLOADS_COMPLETE_MARKER_FILE = "{sub_folder}screenshots/uploads_complete.mark"

URL_IMAGES_PATH = f"{WORKING_DIR}{__URL_IMAGES_FILE}"
SCREENSHOTS_PATH = f"{WORKING_DIR}{__SCREENSHOTS_DIR}"
MEDIAINFO_FILE_PATH = f"{WORKING_DIR}{__MEDIAINFO_FILE}"
BB_CODE_IMAGES_PATH = f"{WORKING_DIR}{__BBCODE_IMAGES_FILE}"
DESCRIPTION_FILE_PATH = f"{WORKING_DIR}{__DESCRIPTION_FILE}"
SCREENSHOTS_RESULT_FILE_PATH = f"{WORKING_DIR}{__SCREENSHOTS_RESULT_FILE}"
UPLOADS_COMPLETE_MARKER_PATH = f"{WORKING_DIR}{__UPLOADS_COMPLETE_MARKER_FILE}"

# Upload Assistant Specific
ASSISTANT_LOG = "{base_path}/assistant.log"
ASSISTANT_CONFIG = "{base_path}/config.env"
ASSISTANT_SAMPLE_CONFIG = "{base_path}/samples/assistant/config.env"

# ReUploader Specific
REUPLOADER_LOG = "{base_path}/reuploader.log"
REUPLOADER_CONFIG = "{base_path}/reupload.config.env"
REUPLOADER_SAMPLE_CONFIG = "{base_path}/samples/reuploader/reupload.config.env"

# Auto Uploader Specific
AUTO_UPLOADER_LOG = "{base_path}/auto_uploader.log"
AUTO_UPLOADER_CONFIG = "{base_path}/auto_uploader.config.env"
AUTO_UPLOADER_SAMPLE_CONFIG = (
    "{base_path}/samples/auto_uploader/auto_uploader.config.env"
)

# Reference Data
TAG_GROUPINGS = "{base_path}/parameters/tag_grouping.json"
AUDIO_CODECS_MAP = "{base_path}/parameters/audio_codecs.json"
SCENE_GROUPS_MAP = "{base_path}/parameters/scene_groups.json"
BLURAY_REGIONS_MAP = "{base_path}/parameters/bluray_regions.json"
STREAMING_SERVICES_MAP = "{base_path}/parameters/streaming_services.json"
CUSTOM_TEXT_COMPONENTS = "{base_path}/parameters/custom_text_components.json"
STREAMING_SERVICES_REVERSE_MAP = (
    "{base_path}/parameters/streaming_services_reverse.json"
)
