from modules.torrent_generator.torf_generator import GGBOTTorrent
from modules.constants import WORKING_DIR
import logging
import glob
import shutil


def update_torrent_info_hash(torrent_info, _, __, working_folder):
    logging.info("[CustomAction][SPD] Updating torrent info hash")

    torrent_file = None
    for file in glob.glob(
        f"{WORKING_DIR.format(base_path=working_folder)}{torrent_info['working_folder']}"
        + r"/*.torrent"
    ):
        if "/SPD-" in file:
            torrent_file = file
            logging.info(
                f"[CustomAction][SPD] Identified .torrent file '{torrent_file}'"
            )
            break
    if torrent_file is None:
        logging.error(
            "[CustomAction][SPD] Failed to identify the torrent file for SPD. Skipping success processor actions"
        )
        return

    torrent = GGBOTTorrent.read(torrent_file)
    torrent.metainfo["info"][
        "source"
    ] = f'{torrent.metainfo["info"]["source"]}-{torrent.infohash}'
    shutil.copyfile(torrent_file, torrent_file.replace("SPD", "BKP_SPD"))

    GGBOTTorrent.copy(torrent).write(
        filepath=torrent_file,
        overwrite=True,
    )
