import json
import logging
import sys
from abc import ABC, abstractmethod
from typing import Type, TypeVar, Dict, List, Optional

import pyfiglet
from rich import box
from rich.console import Console
from rich.prompt import Confirm
from rich.table import Table
from rich.traceback import install

import utilities.utils as utils
from modules.cache import CacheFactory, Cache, CacheVendor
from modules.cli.arguments.arg_parser import GGBotArgumentParser
from modules.config import UploaderConfig
from modules.constants import (
    TAG_GROUPINGS,
    COOKIES_DUMP_DIR,
    TEMPLATE_SCHEMA_LOCATION,
    SITE_TEMPLATES_DIR,
    VALIDATED_SITE_TEMPLATES_DIR,
    TRACKER_ACRONYMS,
)
from modules.exceptions.exception import GGBotFatalException
from modules.template_schema_validator import TemplateSchemaValidator
from modules.torrent_client import TorrentClientFactory, Clients

install()

T = TypeVar("T", bound=GGBotArgumentParser)
root_logger = logging.getLogger(__name__)


def suppress_exceptions_and_log(logger):
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except GGBotFatalException as e:
                logger.fatal(
                    f"Exception in {func.__name__}: {str(e)}", exc_info=e
                )
                sys.exit(1)
            except Exception as e:
                logger.fatal(
                    f"Exception in {func.__name__}: {str(e)}", exc_info=e
                )

        return wrapper

    return decorator


class GGBot(ABC):
    def __init__(
        self,
        *,
        log_file,
        argument_parser: Type[T],
        config_class: Type[UploaderConfig],
        working_folder: str,
        banner_text: str = "Uploader",
    ):
        self.console: Console = Console()
        self.config = config_class()
        self.args = argument_parser().parse_args()
        self.working_folder = working_folder
        self.meta = self._load_metadata()
        self.logger = self._initialize_logger(log_file)
        if self.args.verbose:
            self._enable_verbose_logging()

        # By default, we load the templates from site_templates/ path
        # If user has provided load_external_templates argument then we'll update this path to a different one
        self.site_templates_path = SITE_TEMPLATES_DIR.format(
            base_path=working_folder
        )
        self.display_banner(banner_text)

        # Used to correctly select json file
        # the value in this dictionary must correspond to the file name of the site template
        self.acronym_to_tracker: Dict = json.load(
            open(TRACKER_ACRONYMS.format(base_path=working_folder))
        )
        # the `prepare_tracker_api_keys_dict` prepares the api_keys_dict and also does mandatory property validations
        self.api_keys_dict: Dict = (
            utils.prepare_and_validate_tracker_api_keys_dict(
                "./parameters/tracker/api_keys.json"
            )
        )
        self.torrent_client = None
        self.cache = None
        self.upload_to_trackers = []
        self.upload_queue = []
        self.perform_prerequisites()
        self.setup()
        self.pre_process()

    def pre_process(self):
        self._display_tracker_info()

    def _display_tracker_info(self):
        # Show the user what sites we will upload to
        self.console.line(count=2)
        self.console.rule("Target Trackers", style="red", align="center")
        self.console.line(count=1)
        upload_to_trackers_overview = Table(
            box=box.SQUARE, show_header=True, header_style="bold cyan"
        )

        for upload_to_tracker in ["Acronym", "Site", "URL", "Platform"]:
            upload_to_trackers_overview.add_column(
                f"{upload_to_tracker}", justify="center", style="#38ACEC"
            )

        for tracker in self.upload_to_trackers:
            config = json.load(
                open(
                    f"{self.site_templates_path}{str(self.acronym_to_tracker.get(str(tracker).lower()))}.json",
                    encoding="utf-8",
                )
            )
            # Add tracker data to each row & show the user an overview
            upload_to_trackers_overview.add_row(
                tracker, config["name"], config["url"], config["platform"]
            )

        self.console.print(upload_to_trackers_overview)

        # If not in 'auto_mode' then verify with the user that they want to continue with the upload
        if not self.auto_mode:
            if not Confirm.ask("Continue upload to these sites?", default="y"):
                self.logger.info(
                    "[Main] User canceled upload when asked to confirm sites to upload to"
                )
                self.console.print(
                    "\nOK, quitting now..\n", style="bold red", highlight=False
                )
                raise GGBotFatalException(
                    "User canceled upload when asked to confirm sites to upload to"
                )

    def perform_prerequisites(self):
        self._load_and_validate_templates()
        self._validate_configured_trackers()
        self._validate_args()
        self._validate_env_file()
        self._set_dry_run_config()

    def initialize_torrent_client(self):
        self.torrent_client = utils.get_torrent_client_if_needed(
            config=self.config
        )

    def _set_dry_run_config(self):
        # Dry run mode, mainly intended to be used during development
        self.args.debug = (
            self.args.dry_run if self.args.dry_run is True else self.args.debug
        )

    def _validate_env_file(self):
        # Getting the keys present in the config.env.sample
        # These keys are then used to compare with the env variable keys provided during runtime.
        # Presently we just displays any missing keys, in the future do something more useful with this information
        utils.validate_env_file(
            self.config_sample_file.format(base_path=self.working_folder)
        )

    @property
    @abstractmethod
    def config_sample_file(self):
        raise NotImplementedError

    @suppress_exceptions_and_log(root_logger)
    def start(self) -> None:
        self._process()

    @abstractmethod
    def setup(self) -> None:
        """
        Abstract method which should be implemented to perform any uploader setup / validations / assertions

        Raises
        ------
        NotImplementedError
            If the method is not implemented in the child class.
        """
        raise NotImplementedError

    @abstractmethod
    def _process(self) -> None:
        """
        Abstract method that should be invoked through `start` to handle exceptions and log errors.

        Raises
        ------
        NotImplementedError
            If the method is not implemented in the child class.
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def blacklist_trackers(self) -> List[Optional[str]]:
        raise NotImplementedError

    @property
    @abstractmethod
    def auto_mode(self) -> bool:
        raise NotImplementedError

    def _validate_configured_trackers(self):
        # getting the list of trackers that the user wants to upload to.
        # If there are any configuration errors for a particular tracker, then they'll not be used
        self.upload_to_trackers = utils.get_and_validate_configured_trackers(
            self.args.trackers,
            self.args.all_trackers,
            self.api_keys_dict,
            self.acronym_to_tracker.keys(),
        )
        for tracker in self.blacklist_trackers:
            if tracker in self.upload_to_trackers:
                self.upload_to_trackers.remove(tracker)
                self.console.print(
                    f"[red bold] Uploading to [yellow]{tracker}[/yellow] not supported in current GGBOT flavour"
                )

        if len(self.upload_to_trackers) < 1:
            raise GGBotFatalException(
                "Provide at least 1 tracker we can upload to (e.g. BHD, BLU, ACM)"
            )

    def _load_and_validate_templates(self):
        # creating the schema validator for validating all the template files
        template_validator = TemplateSchemaValidator(
            TEMPLATE_SCHEMA_LOCATION.format(base_path=self.working_folder)
        )

        # we are going to validate all the built-in templates
        valid_templates = utils.validate_templates_in_path(
            self.site_templates_path, template_validator
        )

        # copy all the valid templates to workdir.
        utils.copy_template(
            valid_templates,
            self.site_templates_path,
            VALIDATED_SITE_TEMPLATES_DIR.format(base_path=self.working_folder),
        )

        # now we set the site templates path to the new temp dir
        self.site_templates_path = VALIDATED_SITE_TEMPLATES_DIR.format(
            base_path=self.working_folder
        )

        if self.args.load_external_templates:
            logging.info(
                "[GGBotAutoUploader] User wants to load external site templates. Attempting to load and validate "
                "these templates... "
            )
            # Here we validate the external templates and copy all default and external templates to a different
            # folder. The method will modify the `api_keys_dict` and `acronym_to_tracker` to include the external
            # trackers as well.
            (
                valid_ext_templates,
                ext_api_keys_dict,
                ext_acronyms,
            ) = utils.validate_and_load_external_templates(
                template_validator, self.working_folder
            )
            if len(valid_ext_templates) > 0:
                valid_templates.extend(valid_ext_templates)
                self.api_keys_dict.update(ext_api_keys_dict)
                self.acronym_to_tracker.update(ext_acronyms)

    def _validate_args(self) -> None:
        if self.args.tripleup and self.args.doubleup:
            self.logger.error(
                "[Main] User tried to pass tripleup and doubleup together. Stopping torrent upload process"
            )
            self.console.print(
                "You can not use the arg [deep_sky_blue1]-doubleup[/deep_sky_blue1] and [deep_sky_blue1]-tripleup[/deep_sky_blue1] together. Only one can be used at a time\n",
                style="bright_red",
            )
            self.console.print("Exiting...\n", style="bright_red bold")
            raise GGBotFatalException(
                "You can not use the arg -doubleup and -tripleup together."
            )

    def display_banner(self, banner_text: str) -> None:
        self.console.line(count=2)
        self._display_banner_to_console(banner_text)
        self.console.line(count=1)

    def _display_banner_to_console(self, banner_text: str) -> None:
        gg_bot = pyfiglet.figlet_format("GG-BOT", font="banner3-D")
        self.console.print(
            f"[bold green]{gg_bot}[/bold green]", justify="center"
        )

        banner_text = pyfiglet.figlet_format(
            banner_text, font="banner3-D", width=210
        )
        self.console.print(
            f"[bold blue]{banner_text}[/bold blue]",
            justify="center",
            style="#38ACEC",
        )

    @staticmethod
    def _initialize_logger(log_file):
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.INFO)
        formatter = logging.Formatter(
            f"[{__name__}] %(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        # Disabling the logs from cinemagoer
        logging.getLogger("imdbpy").disabled = True
        logging.getLogger("imdbpy.parser").disabled = True
        logging.getLogger("imdbpy.parser.http").disabled = True
        logging.getLogger("imdbpy.parser.http.piculet").disabled = True
        logging.getLogger("imdbpy.parser.http.build_person").disabled = True
        return logger

    def _enable_verbose_logging(self):
        logging.getLogger().setLevel(logging.DEBUG)
        logging.getLogger(__name__).setLevel(logging.DEBUG)
        [
            handler.setLevel(logging.DEBUG)
            for handler in logging.getLogger(__name__).handlers
        ]
        logging.getLogger("torf").setLevel(logging.INFO)
        logging.getLogger("rebulk.rules").setLevel(logging.INFO)
        logging.getLogger("rebulk.rebulk").setLevel(logging.INFO)
        logging.getLogger("rebulk.processors").setLevel(logging.INFO)
        logging.getLogger("urllib3.connectionpool").setLevel(logging.INFO)
        logging.debug(
            f"[GGBotAutoUploader] Arguments provided by user for reupload: {self.args}"
        )

    def create_torrent_client(self):
        # getting an instance of the torrent client factory
        torrent_client_factory = TorrentClientFactory()
        # creating the torrent client using the factory based on the users configuration
        torrent_client = torrent_client_factory.create(
            Clients[self.config.TORRENT_CLIENT]
        )
        # checking whether the torrent client connection has been created successfully or not
        torrent_client.hello()
        logging.info(
            f"[GGBotAutoUploader] Successfully established connection to torrent client {self.config.TORRENT_CLIENT}"
        )
        return torrent_client

    @staticmethod
    def create_cache_client(cache_type):
        logging.info(
            "[GGBotAutoUploader] Going to establish connection to the cache server configured"
        )
        # creating an instance of cache based on the users configuration
        # TODO if user hasn't provided any configuration then we need to use some other means to keep track
        # of these metadata
        # getting an instance of the torrent client factory
        cache_client_factory = CacheFactory()
        # creating the torrent client using the factory based on the users configuration
        cache: Cache = cache_client_factory.create(CacheVendor[cache_type])
        # checking whether the cache connection has been created successfully or not
        cache.hello()
        logging.info(
            "[GGBotAutoUploader] Successfully established connection to the cache server configured"
        )
        return cache

    def _load_metadata(self):
        return {
            "tag_grouping": json.load(
                open(TAG_GROUPINGS.format(base_path=self.working_folder))
            ),
            "argument_tags": utils.add_argument_tags(self.args.tags),
            "cookies_dump": COOKIES_DUMP_DIR.format(
                base_path=self.working_folder
            ),
        }
