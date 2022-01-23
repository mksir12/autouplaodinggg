import os
# from pwd import getpwuid
from rich.console import Console
import sys
from pprint import pprint
from pprint import pformat


# def find_owner(filename):
#     return os.stat(filename)


# def assert_readable(path):
#     os_supports_effective_ids = os.access in os.supports_effective_ids
#     print("os_supports_effective_ids: " + str(os_supports_effective_ids))
#     print("os.supports_effective_ids: " + str(os.supports_effective_ids))
#     print("os.access: " + str(os.access))
#     print("Effective group id: ", os.getegid())
#     print("Effective user id: ", os.geteuid())
#     print("Real group id: ", os.getgid())
#     print("Real user id: ", os.getuid())
#     print("List of supplemental group ids: ", os.getgroups())
#     print(os.access(path, os.R_OK, effective_ids=os_supports_effective_ids))
#     print(os.access(path, os.R_OK))

#     if not os.access(path, os.R_OK, effective_ids=os_supports_effective_ids):
#         print("Error")
#     else:
#         print("Success")


# assert_readable("/data/downloads/TVSeries/Money Heist.S03E01.The End of the Road.Netflix.WEBDL.1080p.WhiteHat.mkv")
# print(find_owner("/data/downloads/TVSeries/Money Heist.S03E01.The End of the Road.Netflix.WEBDL.1080p.WhiteHat.mkv"))


"""
Testing for multiline inputs from console
"""
console = Console()

# console.print("start")
# inputData = console.input("provide an input??")
# console.print("end")
# console.print(inputData)


# console.print("Provide inputs: ")
# msg = sys.stdin.readlines()
# print(msg)
# for item in msg:
#     print(item)
"""
Testing for multiline inputs from console
"""


"""
Screenshot Table
"""

import os
import base64
import asyncio
import logging
import pyimgbox
import requests
from ffmpy import FFmpeg
from datetime import datetime
from dotenv import load_dotenv
from rich.progress import track
from rich.console import Console
from rich.table import Table
from rich import box

console.line(count=2)
# console.rule(f"Screenshots", style='red', align='center')
console.line(count=1)

screenshot_config = Table(show_header=True, header_style="bold cyan", box=box.HEAVY, border_style="dim")
screenshot_config.add_column("# of Screenshots", justify="center")
screenshot_config.add_column("Thumbnail Size", justify="center")
screenshot_config.add_column("Avoid Spoilers", justify="center")
screenshot_config.add_column("Screenshot Timestamps", justify="center")
screenshot_config.add_column("Image Hosts Order", justify="center")

timestamps = [10,20,30,40,50]
hosts=["freeimage","imgbb","imgbox", "ptpimg"]

screenshot_config.add_row(str(10), str(350), str(True), "\n".join(map(str, timestamps)), "\n".join(hosts))


# tmdb_search_results.add_row(
# f"[chartreuse1][bold]{str(result_num)}[/bold][/chartreuse1]",
# title_match_result,
# f"themoviedb.org/{content_type}/{str(possible_match['id'])}",
# str(year),
# possible_match["original_language"],
# overview,
# end_section=True
# )

# console.print(screenshot_config, justify="center")


def parse_bdinfo(bdinfo_location):
    # TODO add support for .iso extraction
    # TODO add support for 3D bluray disks
    bdinfo = dict()
    bdinfo['video'] = list()
    bdinfo['audio'] = list()
    bdinfo['path'] = bdinfo_location

    with open(bdinfo_location, 'r') as file_contents:
        lines = file_contents.readlines()
        for line in lines:
            line = line.strip()
            line = line.replace("*", "").strip() if line.startswith("*") else line
            if line.startswith("Playlist:"):                        # Playlist: 00001.MPLS              ==> 00001.MPLS
                bdinfo['playlist'] = line.split(':', 1)[1].strip() 
            elif line.startswith("Disc Size:"):                     # Disc Size: 58,624,087,121 bytes   ==> 54.597935752011836
                size = line.split(':', 1)[1].replace("bytes", "").replace(",", "")
                size = float(size)/float(1<<30)
                bdinfo['size'] = size                              
            elif line.startswith("Length:"):                        # Length: 1:37:17.831               ==> 1:37:17
                bdinfo['length'] = line.split(':', 1)[1].split('.',1)[0].strip()
            elif line.startswith("Video:"):
                """
                    video_components: examples [video_components_dict is the mapping of these components and their indexes]
                    MPEG-H HEVC Video / 55873 kbps / 2160p / 23.976 fps / 16:9 / Main 10 @ Level 5.1 @ High / 10 bits / HDR10 / BT.2020
                    MPEG-H HEVC Video / 2104 kbps / 1080p / 23.976 fps / 16:9 / Main 10 @ Level 5.1 @ High / 10 bits / Dolby Vision / BT.2020
                    MPEG-H HEVC Video / 35033 kbps / 2160p / 23.976 fps / 16:9 / Main 10 @ Level 5.1 @ High / 10 bits / HDR10 / BT.2020
                    MPEG-4 AVC Video / 34754 kbps / 1080p / 23.976 fps / 16:9 / High Profile 4.1
                """
                video_components_dict = {
                    0 : "codec",
                    1 : "bitrate",
                    2 : "resolution",
                    3 : "fps",
                    4 : "aspect_ratio",
                    5 : "profile",
                    6 : "bit_depth",
                    7 : "dv_hdr",
                    8 : "color",
                }
                video_components = line.split(':', 1)[1].split('/')
                video_metadata = {}
                for loop_variable in range(0, video_components.__len__()):
                    video_metadata[video_components_dict[loop_variable]] = video_components[loop_variable]
                bdinfo["video"].append(video_metadata)
            elif line.startswith("Audio:"):
                """
                    audio_components: examples 
                    English / Dolby TrueHD/Atmos Audio / 7.1 / 48 kHz /  4291 kbps / 24-bit (AC3 Embedded: 5.1 / 48 kHz /   640 kbps / DN -31dB)
                    English / DTS-HD Master Audio / 7.1 / 48 kHz /  5002 kbps / 24-bit (DTS Core: 5.1 / 48 kHz /  1509 kbps / 24-bit)
                    English / Dolby Digital Audio / 5.1 / 48 kHz /   448 kbps / DN -31dB
                    English / DTS Audio / 5.1 / 48 kHz /   768 kbps / 24-bit
                """
                audio_components_dict = {
                    0 : "language",
                    1 : "codec", # atmos => added if present optionally
                    2 : "channels",
                    3 : "sample_rate",
                    4 : "bitrate",
                    5 : "bit_depth" 
                }
                if "(" in line:
                    line = line.split("(")[0] # removing the contents inside bracket
                audio_components = line.split(':', 1)[1].split('/ ') # not so sure about this /{space}
                audio_metadata = {}
                for loop_variable in range(0, audio_components.__len__()):
                    if "Atmos" in audio_components[loop_variable]: # identifying and tagging atmos audio
                        codec_split = audio_components[loop_variable].split("/")
                        audio_metadata["atmos"] = codec_split[1].strip()
                        audio_components[loop_variable] = codec_split[0].strip()

                    audio_metadata[audio_components_dict[loop_variable]] = audio_components[loop_variable]
                bdinfo["audio"].append(audio_metadata)
            elif line.startswith("Disc Title:"):        # Disc Title: Venom: Let There Be Carnage - 4K Ultra HD
                bdinfo['title'] = line.split(':', 1)[1].strip()
            elif line.startswith("Disc Label:"):        # Disc Label: Venom.Let.There.Be.Carnage.2021.UHD.BluRay.2160p.HEVC.Atmos.TrueHD7.1-MTeam
                bdinfo['label'] = line.split(':', 1)[1].strip()
    print(f"Parsed BDInfo :: {pformat(bdinfo)}")
    return bdinfo

# parse_bdinfo("./bdinfo_1.txt")
print()
print("**********************************************************************")
print()
# parse_bdinfo("./bdinfo_2.txt")
print()
print("**********************************************************************")
print()
# parse_bdinfo("./bdinfo_3.txt")


# {title} {year} {s00e00} {screen_size} {region} {source} {dv} {hdr} {video_codec} {audio_codec} {audio_channels} {atmos} {release_group}
import re
import json
from pprint import pprint
from pprint import pformat

streaming_sources = json.load(open('./parameters/streaming_services.json'))
source_regex = "[\.|\ ](" + "|".join(streaming_sources.values()) + ")[\.|\ ]"
raw_file_name = "Marvel Studios Legends S01 HDR 2160p WEB-DL DSNP DDPA 5.1 H.265-KOGi".upper()
match_web_source = re.search(source_regex, raw_file_name)
print(f"source_regex :: {source_regex}" )
if match_web_source is not None:
    print(pformat(match_web_source))
    print(pformat(match_web_source.group()))
    print(f"MATCH :: XXX{match_web_source.group().replace('.', '').strip()}XXX")
else:
    print("is none")



def test():
    audio_codec_dict = {"AC3": "DD", "AC3+": "DD+", "Dolby Digital Plus": "DD+", "Dolby Digital": "DD",
                                "AAC": "AAC", "AC-3": "DD", "FLAC": "FLAC", "DTS": "DTS", "Opus": "Opus", "OPUS": "Opus", "E-AC-3": "DD+", "A_EAC3": "DD+", "A_AC3": "DD"}
    torrent_info = dict()
    torrent_info["audio_codec"] = "AC3"
    print(str(torrent_info["audio_codec"]) )
    print(audio_codec_dict.keys())
    if str(torrent_info["audio_codec"]) == audio_codec_dict.keys():
        print("YES")
    else:
        print("NO")

    for key in audio_codec_dict.keys(): return key if str(torrent_info["audio_codec"]) == key else print(f"NO :: {key}")


print("START")
print("TEST :: " +  test())
print("STOP")


mylist = []
mydict1 = {
    "key" : "value2",
    "no" : 100
}
mydict2 = {
    "key" : "value1",
    "no" : 300
}
mydict3 = {
    "key" : "value3",
    "no" : 200
}

mylist.append(mydict1)
mylist.append(mydict2)
mylist.append(mydict3)

keys = ["no"]

mylist1 = sorted(mylist, key=lambda d: [d["no"]], reverse=True)
print(mylist)
print(mylist1)


channel = "7.1"
print(channel[0:1])

from ffmpy import FFmpeg
from datetime import datetime

upload_media_import = "/data/downloads/FullDisk/Venom.Let.There.Be.Carnage.2021.UHD.BluRay.2160p.HEVC.Atmos.TrueHD7.1-MTeam/BDMV/STREAM/00001.m2ts"

def get_ss_range(duration, num_of_screenshots):
    first_time_stamp = int(int(duration) / 2 ) / int(int(num_of_screenshots) + 1)

    list_of_ss_timestamps = []
    for num_screen in range(1, int(num_of_screenshots) + 1):
        millis = round(first_time_stamp) * num_screen
        list_of_ss_timestamps.append(str(datetime.strptime("%d:%d:%d" % (int((millis / (1000 * 60 * 60)) % 24), 
                int((millis / (1000 * 60)) % 60), int((millis / 1000) % 60)), '%H:%M:%S').time()))
    return list_of_ss_timestamps

# for ss_timestamp in get_ss_range(duration=120, num_of_screenshots=5):
#     FFmpeg(inputs={upload_media_import: f'-loglevel panic -ss {ss_timestamp} '}, 
#             outputs={f'./images/screenshots/test - ({ss_timestamp.replace(":", ".")}).png': '-frames:v 1 -q:v 10'},
#             global_options=[""]).run()

# import shutil
# torrent_info = {'type':'movie'}
# move_locations = {'torrent': '/projects/Python Projects/gg-bot-upload-assistant/watch', 'media': ''}
# for move_location_key, move_location_value in move_locations.items():
#     if len(move_location_value) == 0:
#         continue
    
#     if os.path.exists(move_location_value):
#         print(f"The move path {move_location_value} exists")
#         if move_location_key == 'torrent':
#             sub_folder = "/"
#             sub_folder = sub_folder + torrent_info["type"] + "/"
#             try:
#                 os.makedirs(os.path.dirname(move_locations["torrent"] + sub_folder), exist_ok=True)
#                 shutil.copy("./requirements.txt", move_locations["torrent"] + sub_folder)
#             except Exception as e:
#                 print(e)

torrent_title = "The Book of Boba Fett S01E03 2160p WEB-DL DD+ 5 1 Atmos PQ10 H 265-NOSiViD"
torrent_title_split = torrent_title.replace("-", " ").lower().split(' ')
print(torrent_title_split)

print()
print()
print()
print()



speedapp_json = json.load(open("./site_templates/speedapp.json"))
if speedapp_json["dupes"]["parse_json"]["is_needed"]:
    print("true")
else:
    print("false")

print(speedapp_json["dupes"]["parse_json"]["is_needed"])



import requests


title = "Rucker-12.2022.1080p.WEB.DL.DD5.1.H.264-EVO Rucker-12.2022.1080p.WEB.DL.DD5.1.H.264-EVO"
title_split = title.replace("-", " ").lower().split(' ')

print(title_split)

def replace_item(lst, to_replace, replace_with):
    print(f"replacing {to_replace}")
    result = []
    for i in lst:
        if i == to_replace:
            result.extend(replace_with)
        else:
            result.append(i)
    return result

for tit in title_split:
    if "." in tit:
        title_split = replace_item(title_split, tit, tit.split("."))

print(title_split)



