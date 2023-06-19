import logging
import shutil
from pathlib import Path

import pytest
import requests
from rich.console import Console

from modules.config import UploadAssistantConfig
from modules.uploader import GGBotTrackerUploader
from tests.test_utilities import TestUtils

working_folder = Path(__file__).resolve().parent.parent.parent
test_working_folder = "/tests/modules/working_folder"


class TestGGBotTrackerUploader:
    @pytest.fixture(scope="class")
    def console(self):
        yield Console()

    @pytest.fixture(scope="class")
    def site_templates_path(self):
        yield f"{working_folder}{test_working_folder}/site_templates_path/"

    @pytest.fixture(scope="class")
    def api_keys_dict(self):
        yield {
            "tsp_api_key": "TSP_API_KEY_PLACEHOLDER",
            "ptp_api_key": "PTP_API_KEY_PLACEHOLDER",
            "blu_api_key": "BLU_API_KEY_PLACEHOLDER",
            "spd_api_key": "SPD_API_KEY_PLACEHOLDER",
            "nbl_api_key": "NBL_API_KEY_PLACEHOLDER",
            "bhdtv_api_key": "BHDTV_API_KEY_PLACEHOLDER",
        }

    @pytest.fixture(scope="class")
    def acronym_to_tracker(self):
        yield {
            "tsp": "thesceneplace",
            "blu": "blutopia",
            "ptp": "passthepopcorn",
            "nbl": "nebulance",
            "bhdtv": "bit-hdtv",
            "spd": "speedapp",
        }

    @pytest.fixture(scope="class", autouse=True)
    def setup(self):
        temp_working_folder = f"{working_folder}{test_working_folder}"
        if Path(temp_working_folder).is_dir():
            TestUtils.clean_up(temp_working_folder)

        Path(f"{temp_working_folder}/site_templates_path").mkdir(
            parents=True, exist_ok=True
        )

        shutil.copy(
            f"{working_folder}/site_templates/blutopia.json",
            f"{temp_working_folder}/site_templates_path/blutopia.json",
        )
        shutil.copy(
            f"{working_folder}/site_templates/passthepopcorn.json",
            f"{temp_working_folder}/site_templates_path/passthepopcorn.json",
        )
        shutil.copy(
            f"{working_folder}/site_templates/nebulance.json",
            f"{temp_working_folder}/site_templates_path/nebulance.json",
        )
        shutil.copy(
            f"{working_folder}/site_templates/thesceneplace.json",
            f"{temp_working_folder}/site_templates_path/thesceneplace.json",
        )
        shutil.copy(
            f"{working_folder}/site_templates/speedapp.json",
            f"{temp_working_folder}/site_templates_path/speedapp.json",
        )
        shutil.copy(
            f"{working_folder}/site_templates/bit-hdtv.json",
            f"{temp_working_folder}/site_templates_path/bit-hdtv.json",
        )
        yield
        TestUtils.clean_up(temp_working_folder)

    @pytest.fixture()
    def gg_bot_tracker_uploader_dict(
        self, api_keys_dict, console, site_templates_path, acronym_to_tracker
    ):
        yield {
            tracker.upper(): GGBotTrackerUploader(
                logger=logging.getLogger(),
                tracker=tracker.upper(),
                uploader_config=UploadAssistantConfig(),
                tracker_settings={},
                torrent_info={},
                api_keys_dict=api_keys_dict,
                site_templates_path=site_templates_path,
                auto_mode=True,
                console=console,
                dry_run=False,
                acronym_to_tracker=acronym_to_tracker,
            )
            for tracker in acronym_to_tracker.keys()
        }

    @pytest.mark.parametrize(
        ("tracker", "expected"),
        [
            pytest.param("TSP", None, id="tsp_header"),
            pytest.param(
                "SPD",
                {"Authorization": "Bearer SPD_API_KEY_PLACEHOLDER"},
                id="spd_header",
            ),
        ],
    )
    def test_get_headers_for_tracker(
        self, gg_bot_tracker_uploader_dict, tracker, expected
    ):
        gg_bot_tracker_uploader = gg_bot_tracker_uploader_dict[tracker]
        headers = gg_bot_tracker_uploader._get_headers_for_tracker()
        assert headers == expected

    @pytest.mark.parametrize(
        ("tracker", "expected"),
        [
            pytest.param("TSP", {}, id="tsp_init_payload"),
            pytest.param(
                "BHDTV",
                {"api_key": "BHDTV_API_KEY_PLACEHOLDER"},
                id="bhdtv_init_payload",
            ),
        ],
    )
    def test_initialize_tracker_payload(
        self, gg_bot_tracker_uploader_dict, tracker, expected
    ):
        gg_bot_tracker_uploader = gg_bot_tracker_uploader_dict[tracker]
        payload = gg_bot_tracker_uploader._initialize_tracker_payload()
        assert payload == expected
