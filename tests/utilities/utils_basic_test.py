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
import datetime

from pathlib import Path
from pymediainfo import MediaInfo
from utilities.utils_basic import *


working_folder = Path(__file__).resolve().parent.parent.parent
mediainfo_xml = "/tests/resources/mediainfo/xml/"
mediainfo_summary = "/tests/resources/mediainfo/summary/"


@pytest.mark.parametrize(
    ("input", "expected"),
    # expected values format [ s00e00, season_number, episode_number, complete_season, individual_episodes, daily_episodes ]
    (
        pytest.param(
            {
                "season": 1,
                "episode": 1
            },
            ("S01E01", "1", "1", "0", "1", "0"), id="single_episode"),
        pytest.param(
            {
                "season": 1
            },
            ("S01", "1", "0", "1", "0", "0"), id="season_pack"),
        pytest.param(
            {
                "season": 1,
                "episode": [9, 10]
            },
            ("S01E09E10", "1", "9", "0", "1", "0"), id="multi_episode_release"),
        pytest.param(
            {
                "date": datetime.date(2022, 4, 12)
            },
            ("2022-04-12", "0", "0", "0", "0", "1"), id="daily_episode")
    )
)
def test_basic_get_episode_basic_details(input, expected):
    assert basic_get_episode_basic_details(input) == expected


def __get_torrent_info(bdinfo, raw_file_name, source):
    torrent_info = {}
    torrent_info["bdinfo"] = bdinfo
    torrent_info["raw_file_name"] = raw_file_name
    if source is not None:  # source will either have a value, or the key itself won't be present
        torrent_info["source"] = source
    return torrent_info


def _get_media_info(raw_file_name):
    return MediaInfo(_get_file_contents(raw_file_name))

def _get_media_info_video_track(raw_file_name):
    return _get_media_info(raw_file_name).tracks[1]


def _get_media_info_data(raw_file_name):
    return _get_media_info(raw_file_name).to_data()


def _get_file_contents(raw_file_name):
    return open(raw_file_name, encoding="utf-8").read()


"""
    Mediainfo Available
        H.264
        H.265
        DV -> H.265
        DV -> HDR10+ -> H.265
        DV -> HDR10 -> HEVC
        HDR -> H.265
        PQ10 -> H.265
        HDR10+ -> H.265
        HLG -> H.265
        WCG -> HEVC
"""


@pytest.mark.parametrize(
    ("torrent_info", "is_disc", "media_info_video_track", "expected"),
    # expected format (dv, hdr, video_codec, pymediainfo_video_codec)
    [
        # TODO: add some tests for x265 and x264 codecs
        pytest.param(
            __get_torrent_info(None, "Monsters.at.Work.S01E10.Its.Laughter.Theyre.After.2160p.WEB-DL.DDP5.1.HDR.H.265-FLUX.mkv", "Web"),
            False,  # is_disc
            _get_media_info_video_track(f"{working_folder}{mediainfo_xml}Monsters.at.Work.S01E10.Its.Laughter.Theyre.After.2160p.WEB-DL.DDP5.1.HDR.H.265-FLUX.xml"),
            (None, "PQ10", "H.265", "H.265"), id="PQ10_H.265_H.265"
        ),
        pytest.param(
            __get_torrent_info(
                None, "The.Great.S02E10.Wedding.2160p.HULU.WEB-DL.DDP5.1.DV.HEVC-NOSiViD.mkv", "Web"),
            False,  # is_disc
            _get_media_info_video_track(
                f"{working_folder}{mediainfo_xml}The.Great.S02E10.Wedding.2160p.HULU.WEB-DL.DDP5.1.DV.HEVC-NOSiViD.xml"),
            ("DV", "HDR10+", "H.265", "H.265"), id="DV_HDR10+_HEVC"
        ),
        pytest.param(
            __get_torrent_info(
                None, "Why.Women.Kill.S02E10.The.Lady.Confesses.2160p.WEB-DL.DD5.1.HDR.HEVC-TEPES.mkv", "Web"),
            False,  # is_disc
            _get_media_info_video_track(
                f"{working_folder}{mediainfo_xml}Why.Women.Kill.S02E10.The.Lady.Confesses.2160p.WEB-DL.DD5.1.HDR.HEVC-TEPES.xml"),
            (None, "HDR10+", "H.265", "H.265"), id="HDR10+_HEVC"
        ),
        pytest.param(
            __get_torrent_info(
                None, "What.If.2021.S01E01.What.If.Captain.Carter.Were.The.First.Avenger.REPACK.2160p.WEB-DL.DDP5.1.Atmos.DV.HEVC-FLUX.mkv", "Web"),
            False,  # is_disc
            _get_media_info_video_track(
                f"{working_folder}{mediainfo_xml}What.If.2021.S01E01.What.If.Captain.Carter.Were.The.First.Avenger.REPACK.2160p.WEB-DL.DDP5.1.Atmos.DV.HEVC-FLUX.xml"),
            ("DV", None, "H.265", "H.265"), id="DV_HEVC"
        ),
        pytest.param(
            __get_torrent_info(
                None, "1883.S01E01.1883.2160p.WEB-DL.DDP5.1.H.265-NTb.mkv", "Web"),
            False,  # is_disc
            _get_media_info_video_track(
                f"{working_folder}{mediainfo_xml}1883.S01E01.1883.2160p.WEB-DL.DDP5.1.H.265-NTb.xml"),
            (None, None, "H.265", "H.265"), id="H.265"
        ),
        pytest.param(
            __get_torrent_info(
                None, "Arcane.S01E01.Welcome.to.the.Playground.1080p.NF.WEB-DL.DDP5.1.HDR.HEVC-TEPES.mkv", "Web"),
            False,  # is_disc
            _get_media_info_video_track(
                f"{working_folder}{mediainfo_xml}Arcane.S01E01.Welcome.to.the.Playground.1080p.NF.WEB-DL.DDP5.1.HDR.HEVC-TEPES.xml"),
            (None, "HDR", "H.265", "H.265"), id="HDR_H.265"
        ),
        pytest.param(
            __get_torrent_info(
                None, "Dragon.Booster.S01E01.The.Choosing.Part.1.AMZN.WEB-DL.DDP2.0.H.264-DRAGONE.mkv", "Web"),
            False,  # is_disc
            _get_media_info_video_track(
                f"{working_folder}{mediainfo_xml}Dragon.Booster.S01E01.The.Choosing.Part.1.AMZN.WEB-DL.DDP2.0.H.264-DRAGONE.xml"),
            (None, None, "H.264", "H.264"), id="H.264"
        ),
        pytest.param(
            __get_torrent_info(
                None, "Peaky.Blinders.S06E01.Black.Day.2160p.iP.WEB-DL.DDP5.1.HLG.H.265-FLUX.mkv", "Web"),
            False,  # is_disc
            _get_media_info_video_track(
                f"{working_folder}{mediainfo_xml}Peaky.Blinders.S06E01.Black.Day.2160p.iP.WEB-DL.DDP5.1.HLG.H.265-FLUX.xml"),
            (None, "HLG", "H.265", "H.265"), id="HLG_H.265"
        ),
        pytest.param(
            __get_torrent_info(
                None, "Venom.Let.There.Be.Carnage.2021.2160p.UHD.BluRay.REMUX.DV.HDR.HEVC.Atmos-TRiToN.mkv", "BluRay"),
            False,  # is_disc
            _get_media_info_video_track(
                f"{working_folder}{mediainfo_xml}Venom.Let.There.Be.Carnage.2021.2160p.UHD.BluRay.REMUX.DV.HDR.HEVC.Atmos-TRiToN.xml"),
            ("DV", "HDR", "HEVC", "HEVC"), id="DV_HDR10_H.265"
        ),
        pytest.param(
            __get_torrent_info(
                None, "Ran.4K.Remastered.1985.2160p.HDR.UHD-TV.HEVC.AAC-DDR.mkv", "BluRay"),
            False,  # is_disc
            _get_media_info_video_track(
                f"{working_folder}{mediainfo_xml}Ran.4K.Remastered.1985.2160p.HDR.UHD-TV.HEVC.AAC-DDR.xml"),
            (None, "WCG", "HEVC", "HEVC"), id="WCG_HEVC"
        ),
    ]
)
def test_basic_get_missing_video_codec(torrent_info, is_disc, media_info_video_track, expected):
    assert basic_get_missing_video_codec(torrent_info, is_disc, False, media_info_video_track) == expected


@pytest.mark.parametrize(
    ("torrent_info", "is_disc", "media_info_video_track", "expected"),
    # TODO add test for 480p, 1080i etc
    [
        pytest.param(
            __get_torrent_info(
                None, "Venom.Let.There.Be.Carnage.2021.2160p.UHD.BluRay.REMUX.DV.HDR.HEVC.Atmos-TRiToN.mkv", None),
            False,  # is_disc
            _get_media_info_video_track(
                f"{working_folder}{mediainfo_xml}Venom.Let.There.Be.Carnage.2021.2160p.UHD.BluRay.REMUX.DV.HDR.HEVC.Atmos-TRiToN.xml"),
            "2160p", id="resolution_2160p"
        ),
        pytest.param(
            __get_torrent_info(
                None, "Arcane.S01E01.Welcome.to.the.Playground.1080p.NF.WEB-DL.DDP5.1.HDR.HEVC-TEPES.mkv", None),
            False,  # is_disc
            _get_media_info_video_track(
                f"{working_folder}{mediainfo_xml}Arcane.S01E01.Welcome.to.the.Playground.1080p.NF.WEB-DL.DDP5.1.HDR.HEVC-TEPES.xml"),
            "1080p", id="resolution_1080p"
        ),
        pytest.param(
            __get_torrent_info(
                None, "Dragon.Booster.S01E01.The.Choosing.Part.1.AMZN.WEB-DL.DDP2.0.H.264-DRAGONE.mkv", None),
            False,  # is_disc
            _get_media_info_video_track(
                f"{working_folder}{mediainfo_xml}Dragon.Booster.S01E01.The.Choosing.Part.1.AMZN.WEB-DL.DDP2.0.H.264-DRAGONE.xml"),
            "576p", id="resolution_576p"
        ),
    ]
)
def test_basic_get_missing_screen_size(torrent_info, is_disc, media_info_video_track, expected):
    assert basic_get_missing_screen_size(torrent_info, is_disc, media_info_video_track, False, "screen_size") == expected


@pytest.mark.parametrize(
    ("media_info_result", "expected"),
    [
        pytest.param(
            _get_media_info_data(
                f"{working_folder}{mediainfo_xml}Dragon.Booster.S01E01.The.Choosing.Part.1.AMZN.WEB-DL.DDP2.0.H.264-DRAGONE.xml"),
            (_get_file_contents(
                f"{working_folder}{mediainfo_summary}Dragon.Booster.S01E01.The.Choosing.Part.1.AMZN.WEB-DL.DDP2.0.H.264-DRAGONE.summary"), "0", "0", "0",
                [{'Language': 'SDH', 'Title': 'SDH', 'Forced': '', 'language_code': 'English', 'Format': 'UTF-8'}]
            ),
            id="summary_without_id"
        ),
        pytest.param(
            _get_media_info_data(
                f"{working_folder}{mediainfo_xml}Venom.Let.There.Be.Carnage.2021.2160p.UHD.BluRay.REMUX.DV.HDR.HEVC.Atmos-TRiToN.xml"),
            (_get_file_contents(
                f"{working_folder}{mediainfo_summary}Venom.Let.There.Be.Carnage.2021.2160p.UHD.BluRay.REMUX.DV.HDR.HEVC.Atmos-TRiToN.summary"), "movie/580489", "tt7097896", "0",
                [{'Language': '', 'Title': '', 'Forced': '', 'language_code': 'English', 'Format': 'PGS'}, {'Language': 'SDH', 'Title': 'SDH', 'Forced': '', 'language_code': 'English', 'Format': 'PGS'}, {'Language': '', 'Title': '', 'Forced': '', 'language_code': 'Bulgarian', 'Format': 'PGS'}, {'Language': 'Cantonese', 'Title': 'Cantonese', 'Forced': '', 'language_code': 'Chinese', 'Format': 'PGS'}, {'Language': 'Mandarin Simplified', 'Title': 'Mandarin Simplified', 'Forced': '', 'language_code': 'Chinese', 'Format': 'PGS'}, {'Language': 'Mandarin Traditional', 'Title': 'Mandarin Traditional', 'Forced': '', 'language_code': 'Chinese', 'Format': 'PGS'}, {'Language': '', 'Title': '', 'Forced': '', 'language_code': 'Croatian', 'Format': 'PGS'}, {'Language': '', 'Title': '', 'Forced': '', 'language_code': 'Czech', 'Format': 'PGS'}, {'Language': '', 'Title': '', 'Forced': '', 'language_code': 'French', 'Format': 'PGS'}, {'Language': '', 'Title': '', 'Forced': '', 'language_code': 'Greek', 'Format': 'PGS'}, {'Language': '', 'Title': '', 'Forced': '', 'language_code': 'Hungarian', 'Format': 'PGS'}, {'Language': '', 'Title': '', 'Forced': '', 'language_code': 'Icelandic', 'Format': 'PGS'}, {'Language': '', 'Title': '', 'Forced': '', 'language_code': 'Indonesian', 'Format': 'PGS'}, {'Language': '', 'Title': '', 'Forced': '', 'language_code': 'Italian', 'Format': 'PGS'}, {'Language': '', 'Title': '', 'Forced': '', 'language_code': 'Korean', 'Format': 'PGS'}, {'Language': '', 'Title': '', 'Forced': '', 'language_code': 'Malay', 'Format': 'PGS'}, {'Language': '', 'Title': '', 'Forced': '', 'language_code': 'Polish', 'Format': 'PGS'}, {'Language': 'Brazilian', 'Title': 'Brazilian', 'Forced': '', 'language_code': 'Portuguese', 'Format': 'PGS'}, {'Language': 'Iberian', 'Title': 'Iberian', 'Forced': '', 'language_code': 'Portuguese', 'Format': 'PGS'}, {'Language': '', 'Title': '', 'Forced': '', 'language_code': 'Romanian', 'Format': 'PGS'}, {'Language': '', 'Title': '', 'Forced': '', 'language_code': 'Serbian', 'Format': 'PGS'}, {'Language': '', 'Title': '', 'Forced': '', 'language_code': 'Slovak', 'Format': 'PGS'}, {'Language': '', 'Title': '', 'Forced': '', 'language_code': 'Slovenian', 'Format': 'PGS'}, {'Language': 'Latin American', 'Title': 'Latin American', 'Forced': '', 'language_code': 'Spanish', 'Format': 'PGS'}, {'Language': '', 'Title': '', 'Forced': '', 'language_code': 'Thai', 'Format': 'PGS'}]
            ),
            id="summary_with_imdb_tmdb_movie"
        ),
        pytest.param(
            _get_media_info_data(
                f"{working_folder}{mediainfo_xml}Peaky.Blinders.S06E01.Black.Day.2160p.iP.WEB-DL.DDP5.1.HLG.H.265-FLUX.xml"),
            (_get_file_contents(
                f"{working_folder}{mediainfo_summary}Peaky.Blinders.S06E01.Black.Day.2160p.iP.WEB-DL.DDP5.1.HLG.H.265-FLUX.summary"), "tv/60574", "tt2442560", "0",
                [{'Language': '', 'Title': '', 'Forced': '', 'language_code': 'English', 'Format': 'UTF-8'}, {'Language': 'SDH', 'Title': 'SDH', 'Forced': '', 'language_code': 'English', 'Format': 'UTF-8'}]
            ),
            id="summary_with_imdb_tmdb_tv"
        ),
        pytest.param(
            _get_media_info_data(
                f"{working_folder}{mediainfo_xml}The.Great.S02E10.Wedding.2160p.HULU.WEB-DL.DDP5.1.DV.HEVC-NOSiViD.xml"),
            (_get_file_contents(
                f"{working_folder}{mediainfo_summary}The.Great.S02E10.Wedding.2160p.HULU.WEB-DL.DDP5.1.DV.HEVC-NOSiViD.summary"), "tv/93812", "tt2235759", "369301",
                [{'Language': '', 'Title': '', 'Forced': '', 'language_code': 'English', 'Format': 'UTF-8'}, {'Language': 'SDH', 'Title': 'SDH', 'Forced': '', 'language_code': 'English', 'Format': 'UTF-8'}, {'Language': 'SDH', 'Title': 'SDH', 'Forced': '', 'language_code': 'Spanish', 'Format': 'UTF-8'}]
            ),
            id="summary_with_imdb_tmdb__tvdb"
        ),
    ]
)
def test_basic_get_mediainfo_summary(media_info_result, expected):
    print(basic_get_mediainfo_summary(media_info_result)[4])
    assert basic_get_mediainfo_summary(media_info_result) == expected

