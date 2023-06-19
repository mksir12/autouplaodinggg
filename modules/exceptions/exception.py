class GGBotException(Exception):
    def __init__(self, message):
        super().__init__(message)


class GGBotUploaderException(GGBotException):
    pass


class GGBotFatalException(GGBotException):
    pass


class GGBotCacheClientException(GGBotUploaderException):
    pass


class GGBotCacheNotInitializedException(GGBotCacheClientException):
    def __init__(self):
        super().__init__("Connection to cache not established")
