import logging


class GGBotLogManager:
    def __init__(
        self, *, enable_verbose: bool = False, log_file: str = "gg_bot.log"
    ):
        self.log_level = "DEBUG" if enable_verbose else "INFO"
        self.log_file = log_file
        self.log_format = logging.Formatter(
            "%(asctime)s | %(name)s | %(levelname)s | %(message)s"
        )
        self.file_handler = logging.FileHandler(self.log_file)
        self.file_handler.setFormatter(self.log_format)
        self._initialize_default_loggers(enable_verbose)

    def get_logger(self, logger_name):
        logger = logging.getLogger(logger_name)
        logger.setLevel(self.log_level)
        logger.addHandler(self.file_handler)
        return logger

    @staticmethod
    def _initialize_default_loggers(enable_verbose):
        if enable_verbose:
            logging.getLogger("torf").setLevel(logging.INFO)
            logging.getLogger("rebulk.rules").setLevel(logging.INFO)
            logging.getLogger("rebulk.rebulk").setLevel(logging.INFO)
            logging.getLogger("rebulk.processors").setLevel(logging.INFO)
            logging.getLogger("urllib3.connectionpool").setLevel(logging.INFO)
        else:
            # Disabling the logs from cinemagoer
            logging.getLogger("imdbpy").disabled = True
            logging.getLogger("imdbpy.parser").disabled = True
            logging.getLogger("imdbpy.parser.http").disabled = True
            logging.getLogger("imdbpy.parser.http.piculet").disabled = True
            logging.getLogger("imdbpy.parser.http.build_person").disabled = True
