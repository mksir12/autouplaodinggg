def season_pack_dupe(torrent_info, tracker_settings, _):
    if (
        "episode_number" in torrent_info
        and torrent_info["episode_number"] != "0"
    ):
        return
    tracker_settings["ignoredupes"] = 1
