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
from pytest_mock import mocker
from pymediainfo import MediaInfo
from utilities.utils_miscellaneous import *


working_folder = Path(__file__).resolve().parent.parent.parent
mediainfo_xml = "/tests/resources/mediainfo/xml/"


class APIResponse:
    ok = None
    data = None
    text = None

    def __init__(self, data, text=None):
        self.ok = "True"
        self.data = data
        self.text = text

    def json(self):
        return self.data


def _get_file_contents(raw_file_name):
    return open(raw_file_name, encoding="utf-8").read()


def _get_media_info(raw_file_name):
    return MediaInfo(_get_file_contents(raw_file_name))


def _get_media_info_audio_tracks(raw_file_name):
    return _get_media_info(raw_file_name).audio_tracks


@pytest.mark.parametrize(
    ("torrent_info", "expected"),
    (
        pytest.param({"release_group":"0mnidvd"}, ("true", "0MNiDVD"), id="scene_group_from_json"),
        pytest.param({"release_group":"kogi"}, ("true", "KOGi"), id="scene_group_from_json"),
        pytest.param({"release_group":"ocular"}, ("true", "OCULAR"), id="scene_group_from_json")
    )
)
def test_miscellaneous_perform_scene_group_capitalization(torrent_info, expected):
    assert miscellaneous_perform_scene_group_capitalization(f'{working_folder}/parameters/scene_groups.json', torrent_info) == expected


def test_scene_group_capitalization_for_p2p_group_folder(monkeypatch):
    torrent_info = {
        "release_group":"decibeL",
        "raw_file_name":"Mr.And.Mrs.Smith.2005.1080p.BluRay.DTS.HD-MA.h264.Remux-decibeL",
        "raw_video_file" : "Mr.And.Mrs.Smith.2005.1080p.BluRay.DTS.HD-MA.h264.Remux-decibeL.mkv"
    }
    expected = ("false", "decibeL")

    pre_corrupt_db = APIResponse(None, open(f"{working_folder}/tests/resources/scene_db/pre_corrupt_db.txt", "r").read())
    srr_db = APIResponse(json.load(open(f"{working_folder}/tests/resources/scene_db/srr_db.json", "r")))
    scene_api_responses = iter([pre_corrupt_db, srr_db])
    monkeypatch.setattr('requests.get', lambda url, headers=None, verify=True: next(scene_api_responses))

    assert miscellaneous_perform_scene_group_capitalization(f'{working_folder}/parameters/scene_groups.json', torrent_info) == expected


def test_scene_group_capitalization_for_p2p_group_file(monkeypatch):
    torrent_info = {
        "release_group":"decibeL",
        "raw_file_name":"Mr.And.Mrs.Smith.2005.1080p.BluRay.DTS.HD-MA.h264.Remux-decibeL.mkv",
    }
    expected = ("false", "decibeL")

    pre_corrupt_db = APIResponse(None, open(f"{working_folder}/tests/resources/scene_db/pre_corrupt_db.txt", "r").read())
    srr_db = APIResponse(json.load(open(f"{working_folder}/tests/resources/scene_db/srr_db.json", "r")))
    scene_api_responses = iter([pre_corrupt_db, srr_db])
    monkeypatch.setattr('requests.get', lambda url, headers=None, verify=True: next(scene_api_responses))

    assert miscellaneous_perform_scene_group_capitalization(f'{working_folder}/parameters/scene_groups.json', torrent_info) == expected


def test_scene_group_capitalization_pre_corrupt_db_match(monkeypatch):
    torrent_info = {
        "release_group":"SPARKS",
        "raw_file_name":"Get.Out.2017.1080p.BluRay.x264-SPARKS.mkv",
    }
    expected = ("true", "SPARKS")

    pre_corrupt_db = APIResponse(None, open(f"{working_folder}/tests/resources/scene_db/pre_corrupt_db_success.txt", "r").read())
    scene_api_responses = iter([pre_corrupt_db])
    monkeypatch.setattr('requests.get', lambda url, headers=None, verify=True: next(scene_api_responses))

    assert miscellaneous_perform_scene_group_capitalization(f'{working_folder}/tests/resources/scene_db/empty.json', torrent_info) == expected


def test_scene_group_capitalization_srr_db_match(monkeypatch):
    torrent_info = {
        "release_group":"SPARKS",
        "raw_file_name":"Get.Out.2017.1080p.BluRay.x264-SPARKS.mkv",
    }
    expected = ("true", "SPARKS")

    pre_corrupt_db = APIResponse(None, open(f"{working_folder}/tests/resources/scene_db/pre_corrupt_db_sparks.txt", "r").read())
    srr_db = APIResponse(json.load(open(f"{working_folder}/tests/resources/scene_db/srr_db_success.json", "r")))
    scene_api_responses = iter([pre_corrupt_db, srr_db])
    monkeypatch.setattr('requests.get', lambda url, headers=None, verify=True: next(scene_api_responses))

    assert miscellaneous_perform_scene_group_capitalization(f'{working_folder}/tests/resources/scene_db/empty.json', torrent_info) == expected


@pytest.mark.parametrize(
    ('input', 'expected'),
    [
        pytest.param('Crank.Extended.Version.2006.MULTi.COMPLETE.BLURAY.iNTERNAL-LiEFERDiENST',
                     'Extended Version', id="extended_version"),
        pytest.param('Halloween.Kills.2021.EXTENDED.2160p.BluRay.HEVC.TrueHD.7.1.Atmos-MT',
                     None, id="extended_all_caps_failure"),
        pytest.param('Perfect Blue 1997 Ultimate Edition 1080p GBR Blu-ray AVC DTS-HD MA 5.1',
                     'Ultimate Edition', id="ultimate_edition"),
        pytest.param('The Breaking Point 1950 1080p Criterion Blu-ray AVC LPCM 1.0',
                     'Criterion', id="criterion"),
        pytest.param('Phenomena 1985 International Cut 1080p GER Blu-ray AVC DTS-HD MA 5.1-UNTOUCHED',
                     'International Cut', id="international_1"),
        pytest.param('The.NeverEnding.Story.1984.International.Cut.1080p.Blu-ray.AVC.DTS-HD.MA.5.1-BeyondHD',
                     'International Cut', id="international_2"),
        pytest.param('The.Admiral.Roaring.Currents.2014.Theatrical.Cut.MULTi.COMPLETE.GER.BLURAY-Psaro',
                     'Theatrical Cut', id="theatrical"),
        pytest.param('Ismael’s Ghosts 2017 Director\'s Cut 1080p GBR Blu-ray AVC DTS-HD MA 5.1-UNRELiABLE',
                     "Director's Cut", id="directors_1"),
        pytest.param(' The Outpost (2020) US Director\'s Cut UHD BD66 Blu-ray WiLDCAT',
                     "Director's Cut", id="directors_2"),
        pytest.param('Ismaels.Ghosts.2017.DC.COMPLETE.BLURAY-UNRELiABLE',
                     None, id="directors_failure_1"),
        pytest.param('The.Last.of.the.Mohicans.DiRECTORS.DEFiNiTiVE.CUT.1992.MULTi.COMPLETE.BLURAY-OLDHAM',
                     None, id="directors_failure_2"),
        pytest.param(
            'The.Wicker.Man.1973.Final.Cut.MULTi.COMPLETE.BLURAY-SAVASTANOS', "Final Cut", id="final"),
    ]
)
def test_miscellaneous_identify_bluray_edition(input, expected):
    assert miscellaneous_identify_bluray_edition(input) == expected


@pytest.mark.parametrize(
    ("screen_size", "test_size", "expected"),
    [
        pytest.param("2160p", 10000000, "uhd_25", id="UHD_25"),
        pytest.param("2160p", 1000000000, "uhd_25", id="UHD_25"),
        pytest.param("2160p", 20000000000, "uhd_25", id="UHD_25"),
        pytest.param("2160p", 26000000000, "uhd_50", id="UHD_50"),
        pytest.param("2160p", 35000000000, "uhd_50", id="UHD_50"),
        pytest.param("2160p", 45000000000, "uhd_50", id="UHD_50"),
        pytest.param("2160p", 55000000000, "uhd_66", id="UHD_66"),
        pytest.param("2160p", 65000000000, "uhd_66", id="UHD_66"),
        pytest.param("2160p", 70000000000, "uhd_100", id="UHD_100"),
        pytest.param("2160p", 99999999990, "uhd_100", id="UHD_100"),
        pytest.param("2160p", 100000000000, None, id="invalid_bluray_size"),
        pytest.param("1080p", 10000000, "bd_25", id="BD_25"),
        pytest.param("1080p", 1000000000, "bd_25", id="BD_25"),
        pytest.param("1080p", 20000000000, "bd_25", id="BD_25"),
        pytest.param("1080p", 26000000000, "bd_50", id="BD_50"),
        pytest.param("1080p", 35000000000, "bd_50", id="BD_50"),
        pytest.param("1080p", 45000000000, "bd_50", id="BD_50"),
        pytest.param("1080p", 55000000000, "bd_66", id="BD_66"),
        pytest.param("1080p", 65000000000, "bd_66", id="BD_66"),
        pytest.param("1080p", 70000000000, "bd_100", id="BD_100"),
        pytest.param("1080p", 99999999990, "bd_100", id="BD_100"),
        pytest.param("1080p", 100000000000, None, id="invalid_bluray_size"),
    ]
)
def test_miscellaneous_identify_bluray_disc_type(screen_size, test_size, expected):
    assert miscellaneous_identify_bluray_disc_type(
        screen_size, "", test_size) == expected


@pytest.mark.parametrize(
    ("input", "expected"),
    (
        pytest.param(
            "The.Man.Who.Killed.Don.Quixote.2018.RERIP.720p.BluRay.x264.AC3-DEEP.mkv", "RERIP", id="rerip_1"),
        pytest.param("What.1972.RERiP.1080p.BluRay.x264-RRH.mkv",
                     "RERiP", id="rerip_2"),
        pytest.param("What.1972.1080p.BluRay.x264-RRH.mkv",
                     None, id="no_repack"),
        pytest.param(
            "The.Northman.2022.REPACK.2160p.MA.WEB-DL.DDP5.1.Atmos.DV.HEVC-MZABI.mk", "REPACK", id="repack"),
        pytest.param(
            "TC.2000.1993.REPACK2.1080p.BluRay.REMUX.AVC.FLAC.2.0-ATELiER.mkv", "REPACK2", id="repack2"),
        pytest.param(
            "TC.2000.1993.REPACK3.1080p.BluRay.REMUX.AVC.FLAC.2.0-ATELiER.mkv", "REPACK3", id="repack3"),
        pytest.param(
            "TC.2000.1993.REPACK4.1080p.BluRay.REMUX.AVC.FLAC.2.0-ATELiER.mkv", "REPACK4", id="repack4"),
        pytest.param(
            "TC.2000.1993.PROPER.1080p.BluRay.REMUX.AVC.FLAC.2.0-ATELiER.mk", "PROPER", id="proper"),
        pytest.param(
            "TC.2000.1993.PROPER2.1080p.BluRay.REMUX.AVC.FLAC.2.0-ATELiER.mk", "PROPER2", id="proper2"),
        pytest.param(
            "TC.2000.1993.PROPER3.1080p.BluRay.REMUX.AVC.FLAC.2.0-ATELiER.mk", "PROPER3", id="proper3"),
        pytest.param(
            "TC.2000.1993.PROPER4.1080p.BluRay.REMUX.AVC.FLAC.2.0-ATELiER.mk", "PROPER4", id="proper4"),
    )
)
def test_miscellaneous_identify_repacks(input, expected):
    assert miscellaneous_identify_repacks(input) == expected


@pytest.mark.parametrize(
    ("raw_file_name", "guess_it_result", "expected"),
    [
        pytest.param("", {"streaming_service": "HBO Max"}, ('HMAX', 'HBO Max')),
        pytest.param("", {"streaming_service": "Amazon Prime"}, ('AMZN', 'Amazon Prime')),
        pytest.param("", {"streaming_service": "AMZN"}, ('AMZN', 'Amazon Prime')),
        pytest.param("", {"streaming_service": ['Disney', 'CTV']}, ('DSNP', 'Disney+')),
        pytest.param("Conversations.with.Friends.S01E01.2160p.HULU.WEB-DL.DDP.5.1.HEVC-MiON", {"streaming_service": ""}, ('HULU', 'Hulu')),
        pytest.param("Conversations.with.Friends.S01E01.2160p.HULU.WEB-DL.DDP.5.1.HEVC-MiON", {}, ('HULU', 'Hulu')),
        pytest.param("Conversations.with.Friends.S01E01.2160p.WEB-DL.DDP.5.1.HEVC-MiON", {}, (None, None)),
        pytest.param("Conversations with Friends S01E01 2160p HULU WEB-DL DDP 5.1 HEVC-MiON", {}, ('HULU', 'Hulu')),
    ]
)
def test_miscellaneous_identify_web_streaming_source(raw_file_name, guess_it_result, expected):
    assert miscellaneous_identify_web_streaming_source(
        f'{working_folder}/parameters/streaming_services.json', f'{working_folder}/parameters/streaming_services_reverse.json', raw_file_name, guess_it_result) == expected


@pytest.mark.parametrize(
    ("raw_file_name", "expected"),
    [
        pytest.param(
            "Step.Up.All.In.2014.BluRay.1080p.TrueHD.Atmos.7.1.AVC.REMUX-FraMeSToR.mkv", "bluray_remux"),
        pytest.param(
            "Ford.v.Ferrari.2019.UHD.BluRay.2160p.TrueHD.Atmos.7.1.DV.HEVC.HYBRID.REMUX-FraMeSToR.mkv", "bluray_remux"),
        pytest.param(
            "ZERV - Zeit der Abrechnung AKA Divided We Stand S01 1080p Bluray REMUX AVC DTS-HD MA 2.0-KKdL", "bluray_remux"),
        pytest.param(
            "Bran.Nue.Dae.2009.1080p.BluRay.REMUX.AVC.TrueHD.5.1-BLURANiUM.mkv", "bluray_remux"),
        pytest.param(
            "The Warriors 1979 Theatrical Cut 1080p AUS Blu-ray AVC DTS-HD MA 5.1-CultFilms™", "bluray_disc"),
        pytest.param(
            "Flirting in the Air 2014 BluRay 1080p AVC TrueHD 5.1-ADC", "bluray_disc"),
        pytest.param(
            "Legendary Weapons of China AKA Shi ba ban wu yi 1982 1080p GBR Blu-ray AVC LPCM 2.0-HGN", "bluray_disc"),
        pytest.param(
            "Flossie 1974 / Keep It Up, Jack! 1974 1080p Blu-ray AVC DTS-HD MA 2.0-GSeye", "bluray_disc"),
        pytest.param(
            "My.Little.Chickadee.1940.Mae.West.1982.COMPLETE.BLURAY-INCUBO", "bluray_disc"),
        pytest.param(
            "Ozark.S04E01.2160p.NF.WEBRip.HDR.x265.DDP.5.1-N0TTZ.mkv", "webrip"),
        pytest.param(
            "Ozark S04 2160p NF WEBRip DD+ 5.1 HDR x265-N0TTZ", "webrip"),
        pytest.param(
            "Velvet.Coleccion.S01E01.1080p.WEBRiP.X264-FiNESSE.mkv", "webrip"),
        pytest.param(
            "Vanity Fair (2018) S01E01 2160p HDR Amazon WEBRip DD+ 5.1 x265-TrollUHD.mkv", "webrip"),
        pytest.param(
            "Our.Planet.2019.S01E01.One.Planet.1080p.NF.WEBRip.DDP5.1.x264-NTb.mkv", "webrip"),
        pytest.param(
            "House of Cards US S05 2160p NF WEBRip DD5 1 x264-NTb", "webrip"),
        pytest.param(
            "Dancing.with.the.Birds.2019.2160p.NF.WEBRip.DDP5.1.x265-TOMMY.mkv", "webrip"),
        pytest.param(
            "American.Driver.2017.1080p.AMZN.WEB-DL.DDP2.0.H.264-SiGLA.mkv", "webdl"),
        pytest.param(
            "Tehran.S02E02.Change.of.Plan.2160p.ATVP.WEB-DL.DDP5.1.HDR.H.265-NTb.mkv", "webdl"),
        pytest.param(
            "Conversations with Friends S01 1080p HULU WEB-DL DD+ 5.1 H.264-MiON", "webdl"),
        pytest.param(
            "Kajillionaire.2020.2160p.AMZN.WEB-DL.DDP.5.1.HDR10Plus.HEVC-MiON.mkv", "webdl"),
        pytest.param(
            "5 Centimeters Per Second [2007] 1080p ITA BDRip x265 DTS-HD MA 5.1 Kira [SEV].mkv", "bluray_encode"),
        pytest.param(
            "L'événement 2021 1080p BluRay DD+5.1 x264-EA.mkv", "bluray_encode"),
        pytest.param(
            "Birthday.Wonderland.2019.1080p.BluRay.x264.DTS.mkv", "bluray_encode"),
        pytest.param(
            "Gruppo.di.famiglia.in.un.interno.VOSTFR.1974.1080p.Bluray.Flac.2.0.x264-KINeMA.mkv", "bluray_encode"),
        pytest.param(
            "They Call Me Trinity AKA Lo chiamavano Trinita... 1970 PAL DVD9 DD 2.0", "dvd"),
        pytest.param(
            "Only.Fools.And.Horses.S01E01.Big.Brother.PAL.DVD.MPEG-2.DD2.0.REMUX.mkv", "dvd"),
        pytest.param(
            "20000.Leagues.Under.the.Sea.2004.NTSC.DVD.REMUX.DD.2.0-NEMO.mkv", "dvd"),
        pytest.param(
            "G.I.Joe.S03E01.Operation.Dragonfire.Day.1.480i.NTSC.DVD.REMUX.DD.2.0-ATELiER.mkv", "dvd"),
        pytest.param("The Prototype 2022 NTSC DVD5 DD 5.1-CONSORTiUM", "dvd"),
        pytest.param(
            "The.Most.Courageous.Raid.of.World.War.II.2019.1080p.HDTV.H264-UNDERBELLY.mkv", "hdtv"),
        pytest.param(
            "Jara.Cimrman.lezici.spici.1983.1080p.HDTV.x264.CZ.EN.mkv", "hdtv"),
        pytest.param(
            "The.94th.Annual.Academy.Awards.2022.1080p.HDTV.x264-DARKFLiX.mkv", "hdtv"),
        pytest.param("Jeopardy.2017.12.01.720p.HDTV.x264-NTb.mkv", "hdtv"),
        pytest.param(
            "The.Piano.Tuner.Of.Earthquakes.2005.720p.HDTV.x264-CBFM.mkv", "hdtv"),
    ]
)
def test_miscellaneous_identify_source_type(raw_file_name, expected):
    assert miscellaneous_identify_source_type(
        raw_file_name, True, None) == expected


@pytest.mark.parametrize(
    ("original_language", "audio_tracks", "expected"),
    [
        pytest.param(
            "ko",
            _get_media_info_audio_tracks(f"{working_folder}{mediainfo_xml}Squid.Game.S01E01.Red.Light.Green.Light.2160p.NF.WEB-DL.DV.HDR.DDP5.1.Atmos.H.265-RG.xml"),
            { "dual" : "Dual-Audio", "multi" : "", "commentary" : False },
            id="dual_audio_only"
        ),
        pytest.param(
            "te",
            _get_media_info_audio_tracks(f"{working_folder}{mediainfo_xml}Sita.Ramam.2022.1080p.AMZN.WEB-DL.Multi.DDP5.1.H.264-RG.xml"),
            { "dual" : "", "multi" : "Multi", "commentary" : False },
            id="multi_audio_only"
        ),
        pytest.param(
            "en",
            _get_media_info_audio_tracks(f"{working_folder}{mediainfo_xml}2001.A.Space.Odyssey.1968.Hybrid.2160p.UHD.BluRay.REMUX.DV.HDR10Plus.HEVC.DTS-HD.MA.5.1-RG.xml"),
            { "dual" : "", "multi" : "", "commentary" : True },
            id="commentary_only"
        ),
        pytest.param(
            "ml",
            _get_media_info_audio_tracks(f"{working_folder}{mediainfo_xml}In.Harihar.Nagar.1990.1080p.DSNP.WEB-DL.AAC2.0.x264-DRG.xml"),
            { "dual" : "", "multi" : "", "commentary" : False },
            id="nothing"
        )
    ]
)
def test_fill_dual_multi_and_commentary(original_language, audio_tracks, expected):
    dual, multi, commentary = fill_dual_multi_and_commentary(original_language, audio_tracks)

    assert dual == expected["dual"]
    assert multi == expected["multi"]
    assert commentary == expected["commentary"]