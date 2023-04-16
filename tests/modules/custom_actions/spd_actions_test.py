import glob
import os
import shutil
from pathlib import Path

import pytest

import utilities.utils as utils
from modules.custom_actions.spd_actions import update_torrent_info_hash
from modules.torrent_generator.torf_generator import GGBOTTorrent
from tests.conftest import TestUtils

working_folder = Path(__file__).resolve().parent.parent.parent.parent
temp_working_dir = "/tests/working_folder"


@pytest.fixture(autouse=True)
def run_around_test():
    """
    Folder structure that will be created for each tests
    ----------------------------------------------------------------------
    tests/
        - working_folder/
            - temp_upload/
                - some_hash_value/
                    - SPD-some_torrent.torrent
    """
    # temp working folder inside tests
    folder = f"{working_folder}{temp_working_dir}"
    if Path(folder).is_dir():
        TestUtils.clean_up(folder)

    Path(f"{folder}/temp_upload/{utils.get_hash('some_name')}").mkdir(
        parents=True, exist_ok=True
    )
    shutil.copy(
        f"{working_folder}/tests/resources/torrent/SPD-atorrent.torrent",
        f"{folder}/temp_upload/{utils.get_hash('some_name')}/SPD-atorrent.torrent",
    )
    yield
    TestUtils.clean_up(folder)


def test_update_torrent_info_hash_no_torrent_file():
    os.remove(
        f"{working_folder}{temp_working_dir}/temp_upload/{utils.get_hash('some_name')}/SPD-atorrent.torrent"
    )
    update_torrent_info_hash(
        {"working_folder": utils.get_hash("some_name")},
        {},
        {},
        f"{working_folder}{temp_working_dir}",
    )

    spd_present = bkp_spd_present = False
    spd_file = bkp_spd_file = None
    for file in glob.glob(
        f"{working_folder}{temp_working_dir}/temp_upload/{utils.get_hash('some_name')}"
        + r"/*.torrent"
    ):
        if "/SPD-atorrent.torrent" in file:
            spd_present = True
            spd_file = file
        elif "/BKP_SPD-atorrent.torrent" in file:
            bkp_spd_present = True
            bkp_spd_file = file
    assert spd_present is False and bkp_spd_present is False
    assert spd_file is None and bkp_spd_file is None


def test_update_torrent_info_hash():
    update_torrent_info_hash(
        {"working_folder": utils.get_hash("some_name")},
        {},
        {},
        f"{working_folder}{temp_working_dir}",
    )

    spd_present = bkp_spd_present = False
    spd_file = bkp_spd_file = None
    for file in glob.glob(
        f"{working_folder}{temp_working_dir}/temp_upload/{utils.get_hash('some_name')}"
        + r"/*.torrent"
    ):
        if "/SPD-atorrent.torrent" in file:
            spd_present = True
            spd_file = file
        elif "/BKP_SPD-atorrent.torrent" in file:
            bkp_spd_present = True
            bkp_spd_file = file

    # assert that there is one SPD-atorrent.torrent
    assert spd_present is True
    # assert that there is one BKP_SPD-atorrent.torrent
    assert bkp_spd_present is True
    assert spd_file is not None and bkp_spd_file is not None
    spd_torrent = GGBOTTorrent.read(spd_file)
    bkp_torrent = GGBOTTorrent.read(bkp_spd_file)

    # assert that the info-hash of BKP_SPD-atorrent.torrent is added to source of SPD-atorrent.torrent
    assert (
        spd_torrent.metainfo["info"]["source"]
        == f'{bkp_torrent.metainfo["info"]["source"]}-{bkp_torrent.infohash}'
    )
    # assert that everything else is kept intact
    assert spd_torrent.comment == bkp_torrent.comment
    assert spd_torrent.created_by == bkp_torrent.created_by
    assert spd_torrent.creation_date == bkp_torrent.creation_date
    assert spd_torrent.files == bkp_torrent.files
    assert spd_torrent.hashes == bkp_torrent.hashes
    assert spd_torrent.filetree == bkp_torrent.filetree
    assert spd_torrent.mode == bkp_torrent.mode
    assert spd_torrent.name == bkp_torrent.name
    assert spd_torrent.piece_size_min == bkp_torrent.piece_size_min
    assert spd_torrent.piece_size_max == bkp_torrent.piece_size_max
    assert spd_torrent.piece_size == bkp_torrent.piece_size
    assert spd_torrent.pieces == bkp_torrent.pieces
    assert spd_torrent.private == bkp_torrent.private
    assert spd_torrent.size == bkp_torrent.size
    assert spd_torrent.trackers == bkp_torrent.trackers
    assert spd_torrent.infohash != bkp_torrent.infohash
