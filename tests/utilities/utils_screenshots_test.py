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

import pytest

from pathlib import Path

from utilities.utils_screenshots import GGBotScreenshotManager

working_folder = Path(__file__).resolve().parent.parent.parent
media_path = "tests/resources/media"
temp_working_dir = f"/{media_path}/temp_upload"
hash_prefix = "HASH_PREFIX/"


def clean_up(pth):
    pth = Path(pth)
    for child in pth.iterdir():
        if child.is_file():
            child.unlink()
        else:
            clean_up(child)
    pth.rmdir()


@pytest.fixture(scope="function", autouse=True)
def run_around_tests():
    folder = f"{working_folder}{temp_working_dir}"

    if Path(folder).is_dir():
        clean_up(folder)

    Path(f"{folder}/{hash_prefix}screenshots").mkdir(
        parents=True, exist_ok=True
    )

    yield
    clean_up(folder)


def test_take_upload_screens_0_num_screenshots():
    response = GGBotScreenshotManager(
        duration="1:10",
        torrent_title="GGBotUploadAssistant",
        upload_media=f"{working_folder}/{media_path}/logo.mp4",
        skip_screenshots=False,
        base_path=f"{working_folder}/{media_path}",
        hash_prefix="HASH_PREFIX/",
    ).generate_screenshots()
    assert not response
    with open(
        f"{working_folder}/{media_path}/temp_upload/{hash_prefix}bbcode_images.txt",
    ) as bbcode_images, open(
        f"{working_folder}/{media_path}/temp_upload/{hash_prefix}url_images.txt",
    ) as url_images:
        assert (
            bbcode_images.readline()
            == "[b][color=#FF0000][size=22]No Screenshots Available[/size][/color][/b]"
        )
        assert url_images.readline() == "No Screenshots Available"
        url_images.close()
        bbcode_images.close()


def screenshot_side_effect_1(key, default=None):
    if key == "num_of_screenshots":
        return "1"
    if key == "img_host_1":
        return "DUMMY"
    if key == "DUMMY_api_key":
        return "DUMMY_API_KEY"
    return default


def test_take_upload_screens_1_screenshots(mocker):
    mocker.patch("os.getenv", side_effect=screenshot_side_effect_1)
    response = GGBotScreenshotManager(
        duration="10",
        torrent_title="GGBotUploadAssistant",
        upload_media=f"{working_folder}/{media_path}/logo.mp4",
        skip_screenshots=False,
        base_path=f"{working_folder}/{media_path}",
        hash_prefix="HASH_PREFIX/",
    ).generate_screenshots()
    assert response is True
    screenshot_found = False
    for file in Path(
        f"{working_folder}/{media_path}/temp_upload/{hash_prefix}screenshots"
    ).iterdir():
        print(file.name)
        if file.name.endswith(".png") and file.name.startswith(
            "GGBotUploadAssistant".lower()
        ):
            screenshot_found = True
    assert screenshot_found
    assert (
        Path(
            f"{working_folder}/{media_path}/temp_upload/{hash_prefix}screenshots/screenshots_data.json"
        ).is_file()
        is True
    )
    assert (
        Path(
            f"{working_folder}/{media_path}/temp_upload/{hash_prefix}screenshots/uploads_complete.mark"
        ).is_file()
        is True
    )
    with open(
        f"{working_folder}/{media_path}/temp_upload/{hash_prefix}screenshots/uploads_complete.mark",
    ) as completed_mark:
        assert (
            completed_mark.readline() == "ALL_SCREENSHOT_UPLOADED_SUCCESSFULLY"
        )
        completed_mark.close()


def screenshot_side_effect_pixhost(key, default=None):
    if key == "num_of_screenshots":
        return "1"
    if key == "img_host_1":
        return "pixhost"
    if key == "pixhost_api_key":
        return "leave_blank"
    return default
