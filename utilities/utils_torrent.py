import glob
import logging
from typing import List

from modules.constants import WORKING_DIR
from modules.torrent_generator.generator_base import GGBotTorrentGeneratorBase
from modules.torrent_generator.mktorrent_generator import (
    GGBotMkTorrentGenerator,
)
from modules.torrent_generator.torf_generator import GGBotTorfTorrentGenerator
from modules.torrent_generator.torrent_editor import GGBotTorrentEditor

from .utils import normalize_for_system_path


def _callback_progress(torrent, filepath, pieces_done, pieces_total):
    _print_progress_bar(
        iteration=100 * float(pieces_done) / float(pieces_total),
        total=100,
        prefix="Creating .torrent file:",
        suffix="Complete",
        length=30,
    )


def _print_progress_bar(
    *,
    iteration,
    total,
    prefix="",
    suffix="",
    decimals=1,
    length=100,
    fill="█",
    print_end="\r",
):
    percent = ("{0:." + str(decimals) + "f}").format(
        100 * (iteration / float(total))
    )
    filled_length = int(length * iteration // total)
    bar = fill * filled_length + "-" * (length - filled_length)
    print(f"\r{prefix} |{bar}| {percent}% {suffix}", end=print_end)
    # Print New Line on Complete
    if iteration == total:
        print()


class GGBotTorrentCreator:
    def __init__(
        self,
        *,
        media: str,
        tracker: str,
        working_folder: str,
        hash_prefix: str,
        torrent_title: str,
        announce_urls: List,
        source: str,
        use_mktorrent: bool,
    ):
        self.working_dir = WORKING_DIR.format(base_path=working_folder)
        self.hash_prefix = hash_prefix
        self.media = media
        self.torrent_title = normalize_for_system_path(torrent_title)
        self.announce = announce_urls
        self.source = source
        self.tracker = tracker
        self.use_mktorrent = use_mktorrent

    def generate_dot_torrent(self):
        logging.info("[DotTorrentGeneration] Creating the .torrent file now")
        logging.info(
            f"[DotTorrentGeneration] Primary announce url: {self.announce[0]}"
        )
        logging.info(
            f"[DotTorrentGeneration] Source field in info `{self.source}`"
        )

        if self.torrent_file_exist:
            self._edit_existing_torrent()
        else:
            self._generate_new_torrent()

    def _generate_new_torrent(self):
        # we need to actually generate a torrent file "from scratch"
        logging.info(
            "[DotTorrentGeneration] Generating new .torrent file since old ones doesn't exist"
        )
        torrent_generator: GGBotTorrentGeneratorBase = (
            self._get_torrent_generator()
        )
        torrent_generator.generate_torrent()
        torrent_generator.do_post_generation_task()

    def _edit_existing_torrent(self):
        torrent_editor = GGBotTorrentEditor(
            f"{self.working_dir}{self.hash_prefix}"
        )
        torrent_editor.edit_torrent(
            announce=self.announce,
            tracker=self.tracker,
            source=self.source,
            torrent_title=self.torrent_title,
        )

    @property
    def torrent_file_exist(self):
        return (
            len(glob.glob(f"{self.working_dir}{self.hash_prefix}*.torrent")) > 0
        )

    def _get_torrent_generator(self):
        if self.use_mktorrent:
            # TODO: use console to display this
            print("Using MkTorrent to generate the torrent")
            logging.info(
                "[DotTorrentGeneration] Using MkTorrent to generate the torrent"
            )
            return GGBotMkTorrentGenerator(
                media=self.media,
                announce=self.announce,
                source=self.source,
                torrent_title=self.torrent_title,
                torrent_path_prefix=f"{self.working_dir}{self.hash_prefix}{self.tracker}",
            )
        return GGBotTorfTorrentGenerator(
            media=self.media,
            announce=self.announce,
            source=self.source,
            torrent_title=self.torrent_title,
            torrent_path_prefix=f"{self.working_dir}{self.hash_prefix}{self.tracker}",
            progress_callback=_callback_progress,
        )
