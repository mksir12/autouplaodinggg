from modules.config import TrackerConfig
import logging

from utilities.utils import write_cutsom_user_inputs_to_description


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


def rewrite_description(torrent_info, tracker_settings, tracker_config):
    logging.info(
        "[CustomActions][TL] Preparing description in template needed for TL"
    )
    tl_description_file = torrent_info["description"].replace(
        "description.txt", "tl_description.txt"
    )

    # writing custom_descriptions
    if (
        "custom_user_inputs" in torrent_info
        and torrent_info["custom_user_inputs"] is not None
    ):
        write_cutsom_user_inputs_to_description(
            torrent_info=torrent_info,
            description_file_path=tl_description_file,
            config=tracker_config,
            tracker="TL",
            bbcode_line_break=tracker_config["bbcode_line_break"],
            debug=True,
        )

    with open(tl_description_file, "a", encoding="utf-8") as tl_description:
        # writing mediainfo to description
        mediainfo = open(torrent_info["mediainfo"]).read()
        tl_description.write(f"[mediainfo]{mediainfo}[/mediainfo]\n")
        # writing screenshots to description
        tl_description.write("[align=center]..:: Screenshots ::..\n")
        for screenshot in torrent_info["url_images"].split("\n"):
            tl_description.write(f"[img]{screenshot}[/img]\n")
        if torrent_info["release_group"] == "DrDooFenShMiRtZ":
            tl_description.write(
                "Uploaded with [color=#ff0000]❤[/color] using GG-BOT Upload Assistantinator[/align]"
            )
        else:
            tl_description.write(
                "Uploaded with [color=#ff0000]❤[/color] using GG-BOT Upload Assistant[/align]"
            )

    tracker_settings["description"] = tl_description_file
    logging.info("[CustomActions][TL] Finished creating description for TL")
