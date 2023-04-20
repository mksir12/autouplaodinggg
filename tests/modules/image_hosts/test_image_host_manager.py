from unittest import mock

import pytest

from modules.image_hosts.image_host_manager import GGBotImageHostManager
from modules.image_hosts.image_upload_status import GGBotImageUploadStatus


def _image_host_env_side_effects(param, default=None):
    if param == "thumb_size":
        return "350"
    if param == "img_host_1" or param == "ptpimg_api_key":
        return "ptpimg"
    if param == "img_host_2" or param == "imgbox_api_key":
        return "imgbox"
    if param == "img_host_3" or param == "freeimage_api_key":
        return "freeimage"
    if param == "img_host_4":
        return "imgbb"
    return default


class TestGGBotImageHostManager:
    @pytest.fixture(scope="class")
    def torrent_title(self):
        yield "Torrent.Title.2023.2160p.GGBOT.WEB-DL.DDP.5.1.H.265-GGBOT"

    @pytest.fixture
    def image_host_manager(self, torrent_title, mocker):
        mocker.patch("os.getenv", side_effect=_image_host_env_side_effects)
        yield GGBotImageHostManager(torrent_title)

    @pytest.fixture
    def no_host_image_host_manager(self, torrent_title):
        yield GGBotImageHostManager(torrent_title)

    def test_no_host_image_host_manager(
        self, no_host_image_host_manager, torrent_title
    ):
        assert no_host_image_host_manager.no_of_image_hosts == 0
        assert no_host_image_host_manager.thumb_size == "350"  # default value
        assert no_host_image_host_manager.torrent_title == torrent_title

    def test_proper_image_host_identification(
        self, image_host_manager, torrent_title
    ):
        assert image_host_manager.thumb_size == "350"
        assert image_host_manager.no_of_image_hosts == 3
        assert image_host_manager.image_hosts == [
            "ptpimg",
            "imgbox",
            "freeimage",
        ]
        assert image_host_manager.torrent_title == torrent_title

    @mock.patch("modules.image_hosts.vendor.ptpimg.PTPImgImageHost.upload")
    @mock.patch("modules.image_hosts.vendor.ptpimg.PTPImgImageHost.status")
    def test_upload_screenshots(self, mock_status, _, image_host_manager):
        mock_status.return_value = GGBotImageUploadStatus(status=True)
        status: GGBotImageUploadStatus = image_host_manager.upload_screenshots(
            ""
        )
        assert status.status

    @mock.patch("modules.image_hosts.vendor.imgbox.ImgboxImageHost.status")
    @mock.patch("modules.image_hosts.vendor.imgbox.ImgboxImageHost.upload")
    @mock.patch("modules.image_hosts.vendor.ptpimg.PTPImgImageHost.upload")
    def test_multiple_hosts_on_failure(
        self, _, __, mock_imgbox_status, image_host_manager
    ):
        mock_imgbox_status.return_value = GGBotImageUploadStatus(status=True)
        status: GGBotImageUploadStatus = image_host_manager.upload_screenshots(
            ""
        )
        assert status.status
