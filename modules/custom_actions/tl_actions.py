from modules.config import TrackerConfig
import logging


def add_announce_pid_to_payload(torrent_info, tracker_settings, tracker_config):
    logging.info("[CustomActions][TL] Adding announcekey to tracker payload")
    tracker_settings["announcekey"] = TrackerConfig("TL").API_KEY


def check_successful_upload(response):
    response_text = response.text

    if response_text.isnumeric():
        logging.info("[CustomActions][TL] Upload to tracker 'SUCCESSFUL'")
        return True, "Successfully Uploaded to TL"
    else:
        logging.info("[CustomActions][TL] Upload to tracker 'FAILED'")
        return False, response_text
