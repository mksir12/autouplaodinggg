# GG Bot Upload Assistant
# Copyright (C) 2023  Noob Master669
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import logging
import operator
import os
import re
import shutil
import subprocess
from typing import Dict, List, Tuple, Any

from rich import box
from rich.console import Console
from rich.prompt import Prompt
from rich.table import Table

from modules.config import UploadAssistantConfig
from modules.exceptions.exception import GGBotFatalException
from utilities.utils import write_file_contents_to_log_as_debug


class BDInfoProcessor:
    def __init__(self, *, bdinfo_script, upload_media, auto_mode):
        self.bdinfo_script = bdinfo_script
        self.upload_media = upload_media
        self.auto_mode = auto_mode
        self.console = Console()
        self._validate_bdinfo_path()
        self._validate_presence_of_bdmv_stream()
        self.bdinfo: Dict[str, Any] = {}

    def get_largest_playlist(self) -> Tuple[str, str]:
        bd_max_size, bd_max_file = self._get_largest_file_from_stream()

        bdinfo_output = str(
            " ".join(
                str(
                    subprocess.check_output(
                        [self.bdinfo_script, self.upload_media, "-l"]
                    )
                ).split()
            )
        ).split(" ")
        logging.debug(
            f"[BDInfoUtils] BDInfo output split from of list command: ---{bdinfo_output}--- "
        )
        mpls_playlists = re.findall(r"\d\d\d\d\d\.MPLS", str(bdinfo_output))

        playlist_info, playlist_length_size = self._identify_playlist_details(
            bdinfo_output=bdinfo_output, mpls_playlists=mpls_playlists
        )

        return bd_max_file, self._get_largest_playlist_for_user(
            playlist_info=playlist_info,
            playlist_length_size=playlist_length_size,
        )

    def generate_bdinfo(self, *, torrent_info: Dict) -> None:
        """
        Method generates the BDInfo for the full disk and writes to the mediainfo.txt file.
        Once it has been generated the generated BDInfo is parsed using the `parse_bdinfo` method
        and result is saved in `torrent_info` as `bdinfo`

        It also sets the `mediainfo` key in torrent_info
        """
        self._generate_bdinfo(torrent_info=torrent_info)
        self._log_bdinfo(torrent_info=torrent_info)
        self.bdinfo = self.parse_bdinfo(torrent_info["mediainfo"])

    def _generate_bdinfo(self, torrent_info: Dict) -> None:
        # if largest_playlist is already in torrent_info, then why this computation again??? Get the BDInfo,
        # parse & save it all into a file called mediainfo.txt (filename doesn't really matter, it gets uploaded to
        # the same place anyway)
        logging.debug(
            f"[BDInfoUtils] `largest_playlist` and `upload_media` from "
            f"torrent_info :: {torrent_info['largest_playlist']} --- {torrent_info['upload_media']}"
        )
        subprocess.run(
            [
                self.bdinfo_script,
                torrent_info["upload_media"],
                "--mpls=" + torrent_info["largest_playlist"],
            ]
        )
        shutil.move(
            f'{torrent_info["upload_media"]}BDINFO.{torrent_info["raw_file_name"]}.txt',
            torrent_info["mediainfo"],
        )

    @staticmethod
    def _log_bdinfo(torrent_info: Dict) -> None:
        logging.debug(
            "[BDInfoUtils] ::::::::::::::::::::::::::::: Dumping the BDInfo Quick Summary :::::::::::::::::::::::::::::"
        )
        write_file_contents_to_log_as_debug(torrent_info["mediainfo"])

    def _validate_bdinfo_path(self):
        if not UploadAssistantConfig().CONTAINERIZED and not os.path.isfile(
            self.bdinfo_script
        ):
            logging.critical(
                "[BDInfoProcessor] You've specified the '-disc' arg but have not supplied a valid bdinfo script path "
                "in config.env "
            )
            logging.info(
                "[BDInfoProcessor] Can not upload a raw disc without bdinfo output, update the 'bdinfo_script' path "
                "in config.env "
            )
            raise GGBotFatalException(
                f"The bdinfo script you specified: ({self.bdinfo_script}) does not exist"
            )

    def _validate_presence_of_bdmv_stream(self):
        if not os.path.exists(f"{self.upload_media}BDMV/STREAM/"):
            logging.critical(
                "[BDInfoProcessor] BD folder not recognized. We can only upload if we detect a '/BDMV/STREAM/' folder"
            )
            raise GGBotFatalException(
                "Currently unable to upload .iso files or disc/folders that does not contain a '/BDMV/STREAM/' folder"
            )

    def _get_largest_file_from_stream(self):
        bd_max_size = 0
        bd_max_file = ""  # file with the largest size inside the STREAM folder
        for folder, _, files in os.walk(f"{self.upload_media}BDMV/STREAM/"):
            # checking the size of each file
            for bd_file in files:
                size = os.stat(os.path.join(folder, bd_file)).st_size
                # updating maximum size
                if size > bd_max_size:
                    bd_max_size = size
                    bd_max_file = os.path.join(folder, bd_file)
        return bd_max_size, bd_max_file

    @staticmethod
    def _identify_playlist_details(
        *, bdinfo_output, mpls_playlists
    ) -> Tuple[List, Dict]:
        playlist_info = [
            {
                "no": bdinfo_output[index - 2].replace("\\n", ""),
                "group": bdinfo_output[index - 1],
                "file": bdinfo_output[index],
                "length": bdinfo_output[index + 1],
                "est_bytes": bdinfo_output[index + 2],
                "msr_bytes": bdinfo_output[index + 3],
                "size": int(str(bdinfo_output[index + 2]).replace(",", "")),
            }
            for index, mpls_playlist in enumerate(bdinfo_output)
            if mpls_playlist in mpls_playlists
        ]
        playlist_length_size = {
            playlist["file"]: playlist["size"] for playlist in playlist_info
        }
        playlist_info = sorted(
            playlist_info, key=operator.itemgetter("size"), reverse=True
        )
        return playlist_info, playlist_length_size

    def _get_largest_playlist_for_user(
        self, *, playlist_info, playlist_length_size
    ):
        if self.auto_mode:
            return self._extract_largest_playlist_by_size(
                playlist_length_size=playlist_length_size
            )
        else:
            self._display_playlist_table(playlist_info=playlist_info)
            return self._get_user_selected_playlist(playlist_info=playlist_info)

    @staticmethod
    def _get_user_selected_playlist(playlist_info):
        choices = [str(i) for i in range(1, len(playlist_info) + 1)]
        user_input_playlist_id_num = Prompt.ask(
            "Choose which `Playlist #` to analyze:",
            choices=choices,
            default="1",
        )
        selected_playlist = playlist_info[int(user_input_playlist_id_num) - 1][
            "file"
        ]
        logging.debug(
            f"[BDInfoUtils] User selected playlist: [{selected_playlist}] "
            f"with Playlist # [{user_input_playlist_id_num}]"
        )
        logging.info(
            f"[BDInfoUtils] The Largest playlist obtained from bluray disc: {selected_playlist}"
        )
        return selected_playlist

    def _display_playlist_table(self, playlist_info):
        # here we display the playlists identified ordered in descending order by size
        # the default choice will be the largest playlist file
        # user will be given the option to choose any different playlist file
        bdinfo_list_table = Table(
            box=box.SQUARE, title="BDInfo Playlists", title_style="bold #be58bf"
        )
        bdinfo_list_table.add_column(
            "Playlist #", justify="center", style="#38ACEC"
        )
        bdinfo_list_table.add_column("Group", justify="center", style="#38ACEC")
        bdinfo_list_table.add_column(
            "Playlist File", justify="center", style="#38ACEC"
        )
        bdinfo_list_table.add_column(
            "Duration", justify="center", style="#38ACEC"
        )
        bdinfo_list_table.add_column(
            "Estimated Bytes", justify="center", style="#38ACEC"
        )
        # bdinfo_list_table.add_column("Measured Bytes", justify="center", style='#38ACEC') # always `-` in the
        # tested BDs

        for playlist_details in playlist_info:
            bdinfo_list_table.add_row(
                str(playlist_details["no"]),
                playlist_details["group"],
                f"[chartreuse1][bold]{str(playlist_details['file'])}[/bold][/chartreuse1]",
                playlist_details["length"],
                playlist_details["est_bytes"],
                end_section=True,
            )

        self.console.print(
            "For BluRay disk you need to select which playlist need to be analyzed, by default the largest playlist "
            "will be selected\n",
            style="bold blue",
        )
        self.console.print("")
        self.console.print(bdinfo_list_table)

    @staticmethod
    def _extract_largest_playlist_by_size(playlist_length_size):
        largest_playlist = max(
            playlist_length_size, key=playlist_length_size.get
        )
        logging.info(
            f"[BDInfoUtils] The Largest playlist obtained from bluray disc: {largest_playlist}"
        )
        return largest_playlist

    @staticmethod
    def _get_largest_playlist(playlist_length_size):
        largest_playlist_value = max(playlist_length_size.values())
        largest_playlist = list(playlist_length_size.keys())[
            list(playlist_length_size.values()).index(largest_playlist_value)
        ]
        logging.info(
            f"[BDInfoUtils] Largest playlist obtained from bluray disc: {largest_playlist}"
        )
        return largest_playlist

    @staticmethod
    def parse_bdinfo(bdinfo_location: str) -> Dict[str, Any]:
        # TODO add support for .iso extraction
        # TODO add support for 3D bluray disks
        """
        Attributes in returned bdinfo
        -----KEY------------DESCRIPTION-----------------------------EXAMPLE VALUE----------
            playlist: playlist being parsed                     : 00001.MPL
            size    : size of the disk                          : 54.597935752011836
            length  : duration of playback                      : 1:37:17
            title   : title of the disk                         : Venom: Let There Be Carnage - 4K Ultra HD
            label   : label of the disk                         : Venom.Let.There.Be.Carnage.2021.UHD.
                                                                    BluRay.2160p.HEVC.Atmos.TrueHD7.1-MTeam
            video   : {
                "codec"         : video codec                   : MPEG-H HEVC Video
                "bitrate"       : the video bitrate             : 55873 kbps
                "resolution"    : the resolution of the video   : 2160p
                "fps"           : the fps                       : 23.976 fps
                "aspect_ratio"  : the aspect ratio              : 16:9
                "profile"       : the video profile             : Main 10 @ Level 5.1 @ High
                "bit_depth"     : the bit depth                 : 10 bits
                "dv_hdr"        : DV or HDR (if present)        : HDR10
                "color"         : the color parameter           : BT.2020
            }
            audio   : {
                "language"      : the audio language            : English
                "codec"         : the audio codec               : Dolby TrueHD
                "channels"      : the audo channels             : 7.1
                "sample_rate"   : the sample rate               : 48 kHz
                "bitrate"       : the average bit rate          : 4291 kbps
                "bit_depth"     : the bit depth of the audio    : 24-bit
                "atmos"         : whether atmos is present      : Atmos Audio
            }
        """
        bdinfo = dict()
        bdinfo["video"] = list()
        bdinfo["audio"] = list()
        with open(bdinfo_location) as file_contents:
            lines = file_contents.readlines()
            for line in lines:
                line = line.strip()
                line = (
                    line.replace("*", "").strip()
                    if line.startswith("*")
                    else line
                )
                # Playlist: 00001.MPLS              ==> 00001.MPLS
                if line.startswith("Playlist:"):
                    bdinfo["playlist"] = line.split(":", 1)[1].strip()
                # Disc Size: 58,624,087,121 bytes   ==> 54.597935752011836
                elif line.startswith("Disc Size:"):
                    size = (
                        line.split(":", 1)[1]
                        .replace("bytes", "")
                        .replace(",", "")
                    )
                    size = float(size) / float(1 << 30)
                    bdinfo["size"] = size
                # Length: 1:37:17.831               ==> 1:37:17
                elif line.startswith("Length:"):
                    bdinfo["length"] = (
                        line.split(":", 1)[1].split(".", 1)[0].strip()
                    )
                elif line.startswith("Video:"):
                    """
                    video_components: [video_components_dict is the mapping of these components and their indexes]
                    MPEG-H HEVC Video / 55873 kbps / 2160p / 23.976 fps / 16:9 /
                        Main 10 @ Level 5.1 @ High / 10 bits / HDR10 / BT.2020
                    MPEG-H HEVC Video / 2104 kbps / 1080p / 23.976 fps / 16:9 /
                        Main 10 @ Level 5.1 @ High / 10 bits / Dolby Vision / BT.2020
                    MPEG-H HEVC Video / 35033 kbps / 2160p / 23.976 fps / 16:9 /
                        Main 10 @ Level 5.1 @ High / 10 bits / HDR10 / BT.2020
                    MPEG-4 AVC Video / 34754 kbps / 1080p / 23.976 fps / 16:9 / High Profile 4.1
                    """
                    video_components_dict = {
                        0: "codec",
                        1: "bitrate",
                        2: "resolution",
                        3: "fps",
                        4: "aspect_ratio",
                        5: "profile",
                        6: "bit_depth",
                        7: "dv_hdr",
                        8: "color",
                    }
                    video_components = line.split(":", 1)[1].split("/")
                    video_metadata = {}
                    for index, component in enumerate(video_components):
                        video_metadata[
                            video_components_dict[index]
                        ] = component.strip()
                    if "HEVC" in video_metadata["codec"]:
                        video_metadata["codec"] = "HEVC"
                    elif "AVC" in video_metadata["codec"]:
                        video_metadata["codec"] = "AVC"

                    bdinfo["video"].append(video_metadata)
                elif line.startswith("Audio:"):
                    """
                    audio_components: examples
                    English / Dolby TrueHD/Atmos Audio / 7.1 / 48 kHz /
                                    4291 kbps / 24-bit (AC3 Embedded: 5.1 / 48 kHz /   640 kbps / DN -31dB)
                    English / DTS-HD Master Audio / 7.1 / 48 kHz /
                                    5002 kbps / 24-bit (DTS Core: 5.1 / 48 kHz /  1509 kbps / 24-bit)
                    English / Dolby Digital Audio / 5.1 / 48 kHz /   448 kbps / DN -31dB
                    English / DTS Audio / 5.1 / 48 kHz /   768 kbps / 24-bit
                    """
                    audio_components_dict = {
                        0: "language",
                        1: "codec",  # atmos => added if present optionally
                        2: "channels",
                        3: "sample_rate",
                        4: "bitrate",
                        5: "bit_depth",
                    }
                    if "(" in line:
                        # removing the contents inside bracket
                        line = line.split("(")[0]
                    audio_components = line.split(":", 1)[1].split(
                        "/ "
                    )  # not so sure about this /{space}
                    audio_metadata = {}
                    for index, component in enumerate(audio_components):
                        # identifying and tagging atmos audio
                        if "Atmos" in component:
                            codec_split = component.split("/")
                            audio_metadata["atmos"] = codec_split[1].strip()
                            component = codec_split[0].strip()

                        audio_metadata[
                            audio_components_dict[index]
                        ] = component.strip()

                    bdinfo["audio"].append(audio_metadata)
                # Disc Title: Venom: Let There Be Carnage - 4K Ultra HD
                elif line.startswith("Disc Title:"):
                    bdinfo["title"] = line.split(":", 1)[1].strip()
                # Disc Label: Venom.Let.There.Be.Carnage.2021.UHD.BluRay.2160p.HEVC.Atmos.TrueHD7.1-MTeam
                elif line.startswith("Disc Label:"):
                    bdinfo["label"] = line.split(":", 1)[1].strip()
        return bdinfo

    def get_video_codec(self):
        """
        Method to get the video_codec information from the bdinfo.
        The method also checks for the presence of DV layer and any HDR formats.
        The return value is (DV, HDR, VIDEO_CODEC)
        """
        dv = None
        hdr = None
        video_tracks = self.bdinfo["video"]
        first_video_track = video_tracks[0]
        video_codec = first_video_track["codec"]

        for index, video_track in enumerate(video_tracks):
            dv_hdr = video_track.get("dv_hdr", "").strip()
            if dv_hdr:
                logging.debug(
                    f"[BDInfoUtils] Detected {dv_hdr} from bdinfo in track {index}"
                )
                if (
                    "DOLBY" in dv_hdr.upper()
                    or "DOLBY VISION" in dv_hdr.upper()
                ):
                    dv = "DV"
                else:
                    hdr = dv_hdr
                    if "HDR10+" in hdr:
                        hdr = "HDR10+"
                    elif "HDR10" in hdr:
                        hdr = "HDR"
                    logging.debug(
                        f"[BDInfoUtils] Adding proper HDR Format `{hdr}` to torrent info"
                    )
                break

        logging.info(
            f"[BDInfoUtils] `video_codec` identified from bdinfo as {video_codec}"
        )
        return dv, hdr, video_codec

    def get_audio_code(self, *, audio_codec_dict: Dict):
        """
        Method to get the audio_codec information from the bdinfo.
        The method also checks for the presence of atmos in the audio
        The return value is (ATMOS, AUDIO_CODEC)
        """
        atmos = None
        codec = self.bdinfo["audio"][0]["codec"].strip()
        for audio_track in self.bdinfo["audio"]:
            if "atmos" in audio_track:
                logging.info(
                    f"[BDInfoUtils] `atmos` identified from bdinfo as {audio_track['atmos']}"
                )
                atmos = "Atmos"
                break

        if codec in audio_codec_dict:
            logging.info(
                f"[BDInfoUtils] Used audio_codec_dict + BDInfo to identify the audio codec: {audio_codec_dict[codec]}"
            )
            return atmos, audio_codec_dict[codec]

        logging.error(
            f"[BDInfoUtils] Failed to get audio_codec from audio_codec_dict + BDInfo. Audio Codec from BDInfo: {codec}"
        )
        return None, None

    def get_audio_channels(self):
        # Here we iterate over all the audio track identified and returns the largest channel.
        # 7.1 > 5.1 > 2.0
        # presently the subwoofer channel is not considered
        # if 2.1 and 2.0 tracks are present and we encounter 2.0 first followed by 2.1,
        # we return 2.0 only.
        # # TODO check whether subwoofer or even atmos channels needs to be considered
        audio_channel = ""
        if self.bdinfo["audio"]:
            audio_channel = max(
                self.bdinfo["audio"], key=lambda track: track["channels"]
            )["channels"]
        logging.info(
            f"[BDInfoUtils] `audio_channels` identified from bdinfo as {audio_channel}"
        )
        return audio_channel
