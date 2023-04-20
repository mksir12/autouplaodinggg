from modules.exceptions.exception import GGBotException


class GGBotVisorFieldValidationError(GGBotException):
    pass


class GGBotInvalidTorrentIdException(GGBotException):
    def __init__(self, torrent_id):
        super().__init__(f"Torrent with id {torrent_id} doesn't exist")


class GGBotNonUniqueTorrentIdException(GGBotException):
    def __init__(self, torrent_id):
        super().__init__(
            f"The provided torrent id [{torrent_id}] is not enough to identify a unique torrent"
        )
