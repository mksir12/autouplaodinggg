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

import json
import pytest
import shutil

from pathlib import Path
from pytest_mock import mocker

import utilities.utils as utils

from modules.template_schema_validator import TemplateSchemaValidator
from modules.constants import SITE_TEMPLATES_DIR, VALIDATED_SITE_TEMPLATES_DIR


working_folder = Path(__file__).resolve().parent.parent.parent.parent
temp_working_dir = "/tests/working_folder"


@pytest.fixture(scope="function", autouse=True)
def run_around_tests():
    """
        Folder struture that will be created for each tests
        ----------------------------------------------------------------------
        tests/
            - working_folder/
                - empty_dir/
                - external/site_templates/
                    - sample.json
                    - sample1.json
                - resources/
                - rar/
                - torrent/
                    - test1.torrent
                    - test2.torrent
                - media/
                    - file.mkv
                    - Movie.Name.2017.1080p.BluRay.Remux.AVC.DTS.5.1-RELEASE_GROUP
                        - Movie.Name.2017.1080p.BluRay.Remux.AVC.DTS.5.1-RELEASE_GROUP.mkv
                - move/
                    - torrent/
                    - media/
                - sample/
                    - config.env.sample
                - temp_upload/
                    - test_working_folder/
                        - TRACKER-Some Title different from torrent_title.torrent
                        - TRACKER2-Some Title different from torrent_title.torrent
                    - test_working_folder_2/
                        - torrent1.torrent
                        - torrent2.torrent
                        - screenshots/
                            - image1.png
                            - image2.png
        ----------------------------------------------------------------------
    """
    # temp working folder inside tests
    folder = f"{working_folder}{temp_working_dir}"

    if Path(folder).is_dir():
        clean_up(folder)

    Path(f"{folder}/temp_upload/{utils.get_hash('some_name')}/screenshots").mkdir(parents=True, exist_ok=True)  # temp_upload folder
    Path(f"{folder}/nothing").mkdir(parents=True, exist_ok=True)  # temp_upload folder
    Path(f"{folder}/external/site_templates/").mkdir(parents=True, exist_ok=True)  # external site templates folder
    Path(f"{folder}/external/tracker/").mkdir(parents=True, exist_ok=True)  # external site acronym mapping location
    Path(f"{folder}/empty_dir/").mkdir(parents=True, exist_ok=True)  # empty dir for any tests that needs it

    # creating external dupe templates
    shutil.copy(f"{working_folder}/site_templates/blutopia.json", f"{folder}/external/site_templates/sample.json")
    shutil.copy(f"{working_folder}/site_templates/aither.json", f"{folder}/external/site_templates/sample1.json")
    shutil.copy(f"{working_folder}/site_templates/aither.json", f"{folder}/external/site_templates/sample2.json")
    # removing a mandatory field from sample2.json
    sample2_json = json.load(open(f"{folder}/external/site_templates/sample2.json","r"))
    sample2_json.pop("name", None)
    json.dump(sample2_json, open(f"{folder}/external/site_templates/sample2.json","w"))
    json.dump({"sample":"smpl", "sample1": "smpl1"}, open(f"{folder}/external/tracker/tracker_to_acronym.json","w"))

    # creating some random files inside `/tests/working_folder/temp_upload`
    touch(f'{folder}/temp_upload/{utils.get_hash("some_name")}/torrent1.torrent')
    touch(f'{folder}/temp_upload/torrent1.torrent')
    touch(f'{folder}/temp_upload/{utils.get_hash("some_name")}/torrent2.torrent')
    touch(f'{folder}/temp_upload/{utils.get_hash("some_name")}/screenshots/image1.png')
    touch(f'{folder}/temp_upload/{utils.get_hash("some_name")}/screenshots/image2.png')

    yield
    clean_up(folder)


def touch(file_path):
    fp = open(file_path, 'x')
    fp.close()


def clean_up(pth):
    pth = Path(pth)
    for child in pth.iterdir():
        if child.is_file():
            child.unlink()
        else:
            clean_up(child)
    pth.rmdir()


def test_delete_leftover_humanreadable_files(mocker):
    mocker.patch("os.getenv", return_value=True)
    # here we'll be working with /tests/working_folder/temp_upload/
    # this will be the folder that the actual code will be dealing with
    computed_working_folder = utils.delete_leftover_files(
        working_folder=f"{working_folder}{temp_working_dir}",
        file="/somepath/some more/This is: some ra'ndom.files.thing-WHO",
        resume=False
    )
    human_readable_folder = "This.is..some.random.files.thing-WHO"
    old_hash = utils.get_hash("some_name")
    # check whether the hash folder has been created or not
    assert computed_working_folder == f"{human_readable_folder}/"
    assert Path(f"{working_folder}{temp_working_dir}/temp_upload/{human_readable_folder}").is_dir() == True
    assert Path(f"{working_folder}{temp_working_dir}/temp_upload/{old_hash}").is_dir() == False
    assert Path(f"{working_folder}{temp_working_dir}/temp_upload/{human_readable_folder}/screenshots/").is_dir() == True


def test_delete_leftover_humanreadable_files_disabled(mocker):
    mocker.patch("os.getenv", return_value=False)
    # here we'll be working with /tests/working_folder/temp_upload/
    # this will be the folder that the actual code will be dealing with
    computed_working_folder = utils.delete_leftover_files(
        working_folder=f"{working_folder}{temp_working_dir}",
        file="/somepath/some more/This is: some ra'ndom.files.thing-WHO",
        resume=False
    )
    new_hash = utils.get_hash("/somepath/some more/This is: some ra'ndom.files.thing-WHO")
    old_hash = utils.get_hash("some_name")
    # check whether the hash folder has been created or not
    assert computed_working_folder == f"{new_hash}/"
    assert Path(f"{working_folder}{temp_working_dir}/temp_upload/{new_hash}").is_dir() == True
    assert Path(f"{working_folder}{temp_working_dir}/temp_upload/{old_hash}").is_dir() == False
    assert Path(f"{working_folder}{temp_working_dir}/temp_upload/{new_hash}/screenshots/").is_dir() == True


def test_delete_leftover_files():
    # here we'll be working with /tests/working_folder/temp_upload/
    # this will be the folder that the actual code will be dealing with
    computed_working_folder = utils.delete_leftover_files(
        working_folder=f"{working_folder}{temp_working_dir}",
        file="some_name1",
        resume=False
    )
    hash = utils.get_hash("some_name1")
    old_hash = utils.get_hash("some_name")
    # check whether the hash folder has been created or not
    assert computed_working_folder == f"{hash}/"
    assert Path(f"{working_folder}{temp_working_dir}/temp_upload/{hash}").is_dir() == True
    assert Path(f"{working_folder}{temp_working_dir}/temp_upload/{old_hash}").is_dir() == False
    assert Path(f"{working_folder}{temp_working_dir}/temp_upload/{hash}/screenshots/").is_dir() == True


def test_retain_leftover_files_for_resume():
    # here we'll be working with /tests/working_folder/temp_upload/
    # this will be the folder that the actual code will be dealing with
    computed_working_folder = utils.delete_leftover_files(
        working_folder=f"{working_folder}{temp_working_dir}",
        file="some_name1",
        resume=True
    )
    hash = utils.get_hash("some_name1")
    old_hash = utils.get_hash("some_name")
    assert computed_working_folder == f"{hash}/"
    assert Path(f"{working_folder}{temp_working_dir}/temp_upload/{hash}").is_dir() == True
    assert Path(f"{working_folder}{temp_working_dir}/temp_upload/{old_hash}").is_dir() == True
    assert Path(f"{working_folder}{temp_working_dir}/temp_upload/{hash}/screenshots/").is_dir() == True


def test_create_temp_upload_itself():
    # here we'll be working with /tests/working_folder/temp_upload/
    # this will be the folder that the actual code will be dealing with
    computed_working_folder = utils.delete_leftover_files(
        working_folder=f"{working_folder}{temp_working_dir}/nothing",
        file="some_name1",
        resume=True
    )
    hash = utils.get_hash("some_name1")
    assert computed_working_folder == f"{hash}/"
    assert Path(f"{working_folder}{temp_working_dir}/nothing/temp_upload/{hash}").is_dir() == True
    assert Path(f"{working_folder}{temp_working_dir}/nothing/temp_upload/{hash}/screenshots/").is_dir() == True


@pytest.mark.parametrize(
    ("torrent_info", "expected"),
    [
        pytest.param(
            { "release_group" : "RELEASE_GROUP", "upload_media" : "/data/Movies/Name of the Movie 2022 STREAM WEB-DL DD+ 5.1 Atmos DV HDR HEVC-RELEASE_GROUP.mkv" },
            "RELEASE_GROUP",
            id="proper_release_group_from_guessit"
        ),
        pytest.param(
            { "upload_media" : "/data/Movies/Name of the Movie 2022 STREAM WEB-DL DD+ 5.1 Atmos DV HDR HEVC.mkv" },
            "NOGROUP",
            id="no_release_group_from_guessit"
        ),
        pytest.param(
            { "release_group" : "", "upload_media" : "/data/Movies/Name of the Movie 2022 STREAM WEB-DL DD+ 5.1 Atmos DV HDR HEVC.mkv" },
            "NOGROUP",
            id="empty_group_from_guessit"
        ),
        pytest.param(
            { "release_group" : "X-RELEASE_GROUP", "upload_media" : "/data/Movies/Name of the Movie 2022 STREAM WEB-DL 7.1 Atmos DV HDR HEV DTS-X-RELEASE_GROUP.mkv" },
            "RELEASE_GROUP",
            id="dts-x-wrong_group_from_guessit"
        ),
        pytest.param(
            { "release_group" : "DV", "upload_media" : "/data/Movies/Name of the Movie 2022 STREAM WEB-DL DD+ 5.1 Atmos DV HDR HEVC.mkv" },
            "NOGROUP",
            id="group_from_guessit_when_no_group"
        ),
        pytest.param(
            { "release_group" : "RELEASE_GROUP", "upload_media" : "/data/Movies/Miss Sadie Thompson 1953 1080p Blu-ray Remux AVC FLAC 2.0 - RELEASE_GROUP.mkv" },
            "RELEASE_GROUP",
            id="group_from_guessit_with_space_in_title"
        ),
    ]
)
def test_sanitize_release_group_from_guessit(torrent_info, expected):
    assert utils.sanitize_release_group_from_guessit(torrent_info) == expected


def test_validate_builtin_templates():
    all_available_templates = len(list(filter(lambda entry: entry.is_file() and entry.suffix == ".json",Path(f"{working_folder}/site_templates/").glob('**/*'))))
    template_validator = TemplateSchemaValidator(f"{working_folder}/schema/site_template_schema.json")
    valid_templates = utils.validate_templates_in_path(f"{working_folder}/site_templates/", template_validator)
    assert len(valid_templates) == all_available_templates


def test_copy_template():
    valid_templates = ["blutopia", "passthepopcorn", "nebulance"]
    source_dir = SITE_TEMPLATES_DIR.format(base_path=working_folder)
    target_dir = f"{working_folder}{temp_working_dir}/validated_site_templates/".format(base_path=working_folder)

    utils.copy_template(valid_templates, source_dir, target_dir)
    for template in valid_templates:
        assert Path(f"{target_dir}{template}.json").is_file()


def test_copy_template_with_already_existing_data():
    valid_templates = ["blutopia", "passthepopcorn", "nebulance"]
    source_dir = SITE_TEMPLATES_DIR.format(base_path=working_folder)
    target_dir = f"{working_folder}{temp_working_dir}/validated_site_templates/".format(base_path=working_folder)

    # making target dir and copying the templates (with modifications)
    Path(target_dir).mkdir(parents=True, exist_ok=True)
    for template in valid_templates:
        shutil.copy(str(Path(f"{source_dir}{template}.json")), str(Path(f"{target_dir}{template}.json")))

        template_json_file = json.load(open(str(Path(f"{target_dir}{template}.json")), "r"))
        template_json_file["name"] = "FAKE_NAME"
        json.dump(template_json_file, open(str(Path(f"{target_dir}{template}.json")), "w"))

    utils.copy_template(valid_templates, source_dir, target_dir)
    for template in valid_templates:
        assert Path(f"{target_dir}{template}.json").is_file()
        assert json.load(open(str(Path(f"{target_dir}{template}.json"))))["name"] != "FAKE_NAME"


def __external_tracker_api_keys(key, default=None):
    if key == "SMPL_API_KEY":
        return "smpl_api_key_value"
    elif key == "SMPL1_API_KEY":
        return "smpl1_api_key_value"
    return default


def test_validate_and_load_external_templates(mocker):
    mocker.patch("os.getenv", side_effect=__external_tracker_api_keys)
    template_validator = TemplateSchemaValidator(f"{working_folder}/schema/site_template_schema.json")
    api_key_dict_expected = {
        "smpl_api_key": "smpl_api_key_value",
        "smpl1_api_key": "smpl1_api_key_value"
    }
    acronyms = {v:k for k,v in {"sample":"smpl", "sample1": "smpl1"}.items()}

    assert utils.validate_and_load_external_templates(template_validator, f"{working_folder}{temp_working_dir}") == (["sample", "sample1"], api_key_dict_expected, acronyms)
    total_number_templates = len(list(filter(lambda entry: entry.is_file() and entry.suffix == ".json", Path(f"{working_folder}{temp_working_dir}/validated/site_templates/").glob('**/*'))))
    assert total_number_templates == 2


def test_validate_and_load_external_templates_no_dir():
    template_validator = TemplateSchemaValidator(f"{working_folder}/schema/site_template_schema.json")
    assert utils.validate_and_load_external_templates(template_validator, f"{working_folder}{temp_working_dir}/fake_dir") == ([], {}, {})