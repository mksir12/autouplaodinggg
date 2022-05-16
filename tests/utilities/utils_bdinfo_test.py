import json
import pytest
import shutil

from pathlib import Path
from pytest_mock import mocker
from utilities.utils_bdinfo import *

"""
    HOW IS THIS TESTS SETUP?
    ----------------------------------------------

    To test the generation and parsing of BDInfo, the BDInfo summary is generated before hand for various disks.
    These generated summary are stored in the location `bdinfo_summary`. This is the output we get from BDInfoCLI.
    
    Now that we have the outputs stored, we don't have a dependency on BDInfoCLI during testing. The stored output is 
    given to the parsing code to preapre the bdinfo dictionary and it is validated.

    Components ::::::::::::::::

    1. All the resources used during bdinfo testing are saved in side `/tests/resources/bdinfo/` folder.
    2. Various components of this folder are
        2.a summary -> Ths summary contains the text files with the Quick Summary from BDInfoCLI
        2.b metadata -> The metadata folder contains additional details are information that is needed for the bdinfo parser to function.
                        The metadata contains various .json files containing the metadata.
        2.c expected -> The contents of the expected folder are the bdinfo expected to be generated by the parser. (json format)
        2.d working_folder -> The parser does some copy and move operations of certain files. 
                During testing all those movements are performed inside this folder. (See Parser Flow and Test Setup Section)
    

    Parser Flow and Test Setup ::::::::::::::::
    Parser Flow
        1. Call bdinfocli to generate the quick summary for the largest playlist
        2. Output of bdinfocli will be along with the `upload_media` location.
        3. Output file is named as `upload_media`/BDINFO.`raw_file_name`.txt
        4. Move this file to the temp_folder with the same name as the mediainfo file. (mediainfo.txt)
        5. Remove `ENDS FORUMS PASTE` from the file
        6. Give file to the actual bdinfo parser to parse data

    Test Setup
        1. We cannot cann bdinfocli, hence the output of bdinfocli is taken and stored inside the `bdinfo_summary` folder 
            (`raw_file_name` is the name of the file)
        2. Prepare the `torrent_info` that is accepted by the parser
            2.a Parser uses the following attributes inside torrent_info during bdinfo generation and parsing.
                * upload_media
                * mediainfo
                * largest_playlist
                * raw_file_name
                * raw_video_file
                All these components are directly available in the .json metadata file or can be constructed from the .json file contents
            2.b The parsed expected the bdinfo output in certain folder (See step 3 of Parser Flow).
                hence we create those folders and copy the summary file to that folder with the proper name.
        3. Read the expected bdinfo file from the `bdinfo_metadata_expected` location.
        4. Call the `bdinfo_generate_and_parse_bdinfo` with these information and verify the output
"""

bdinfo_summary = "/tests/resources/bdinfo/summary/"
bdinfo_metadata = "/tests/resources/bdinfo/metadata/"
bdinfo_metadata_expected = "/tests/resources/bdinfo/expected/"
bdinfo_working_folder = "/tests/resources/bdinfo/working_folder/"

working_folder = Path(__file__).resolve().parent.parent.parent


def __get_torrent_info(file_name):
    meta_data = json.load(open(f'{working_folder}{bdinfo_metadata}{file_name}.json'))
    
    torrent_info = {}
    torrent_info["upload_media"] = f'{working_folder}{bdinfo_working_folder}{file_name}/'
    torrent_info["mediainfo"] = f'{working_folder}{bdinfo_working_folder}{file_name}/mediainfo.txt'
    torrent_info["largest_playlist"] = meta_data["largest_playlist"]
    torrent_info["raw_file_name"] = meta_data["raw_file_name"]
    torrent_info["file_name"] = file_name
    torrent_info["raw_video_file"] = meta_data["raw_video_file"]
    
    source = f'{working_folder}{bdinfo_summary}{file_name}.txt'
    destination = f'{working_folder}{bdinfo_working_folder}{file_name}/BDINFO.{torrent_info["raw_file_name"]}.txt'
    
    p = Path(f'{working_folder}{bdinfo_working_folder}{file_name}/')
    p.mkdir(parents=True, exist_ok=True)

    shutil.copy(source, destination)
    
    return torrent_info


def __get_expected_bd_info(file_name):
    return json.load(open(f'{working_folder}{bdinfo_metadata_expected}{file_name}.json'))


@pytest.mark.parametrize(
    ("torrent_info", "expected"),
    [
        (__get_torrent_info("Company.Business.1991.COMPLETE.BLURAY-UNTOUCHED"), __get_expected_bd_info("Company.Business.1991.COMPLETE.BLURAY-UNTOUCHED")),
        (__get_torrent_info("Dont.Breathe.2.2021.MULTi.COMPLETE.UHD.BLURAY-GLiMME"), __get_expected_bd_info("Dont.Breathe.2.2021.MULTi.COMPLETE.UHD.BLURAY-GLiMME")),
        (__get_torrent_info("Hardware 1990 1080p Blu-ray AVC DD 5.1-BaggerInc"), __get_expected_bd_info("Hardware 1990 1080p Blu-ray AVC DD 5.1-BaggerInc")),
        (__get_torrent_info("PIRATES_1_CURSE_OF_BLACK_PEARL"), __get_expected_bd_info("PIRATES_1_CURSE_OF_BLACK_PEARL")),
        (__get_torrent_info("Robot 2010 1080p Blu-ray AVC DTS-HD MA 5.1-DRs"), __get_expected_bd_info("Robot 2010 1080p Blu-ray AVC DTS-HD MA 5.1-DRs"))
    ]
)
def test_bdinfo_generate_and_parse_bdinfo(torrent_info, expected, mocker):
    mocker.patch("subprocess.run", return_value=None)
    assert bdinfo_generate_and_parse_bdinfo(None, torrent_info, False) == expected
