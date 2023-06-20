import argparse
from abc import ABC


class GGBotArgumentParser(ABC):
    def __init__(self, description):
        self.parser = argparse.ArgumentParser(description=description)
        self._define_common_args()
        self._define_uncommon_args()
        self._define_internal_args()

    def _define_internal_args(self):
        # args for Internal uploads
        internal_args = self.parser.add_argument_group(
            "Internal Upload Arguments"
        )
        internal_args.add_argument(
            "-internal",
            action="store_true",
            help="(Internal) Used to mark an upload as 'Internal'",
        )
        internal_args.add_argument(
            "-freeleech",
            action="store_true",
            help="(Internal) Used to give a new upload freeleech",
        )
        internal_args.add_argument(
            "-featured",
            action="store_true",
            help="(Internal) feature a new upload",
        )
        internal_args.add_argument(
            "-doubleup",
            action="store_true",
            help="(Internal) Give a new upload 'double up' status",
        )
        internal_args.add_argument(
            "-tripleup",
            action="store_true",
            help="(Internal) Give a new upload 'triple up' status [XBTIT Exclusive]",
        )
        internal_args.add_argument(
            "-sticky", action="store_true", help="(Internal) Pin the new upload"
        )
        internal_args.add_argument(
            "-exclusive",
            nargs=1,
            help="(Internal) Set torrent as exclusive for <X> days",
        )

    def _define_common_args(self):
        common_args = self.parser.add_argument_group("Commonly Used Arguments")
        common_args.add_argument(
            "-t",
            "--trackers",
            nargs="*",
            help="Tracker(s) to upload to. Space-separates if multiple (no commas)",
        )
        common_args.add_argument(
            "-a",
            "--all_trackers",
            action="store_true",
            help="Select all trackers that can be uploaded to",
        )
        common_args.add_argument(
            "-anon",
            action="store_true",
            help="Tf you want your upload to be anonymous (no other info needed, just input '-anon'",
        )
        common_args.add_argument(
            "--verbose",
            "-v",
            action="store_true",
            help="Enable verbose logging",
        )

    def _define_uncommon_args(self):
        uncommon_args = self.parser.add_argument_group("Less Common Arguments")
        uncommon_args.add_argument(
            "-d",
            "--debug",
            action="store_true",
            help="Used for debugging. Writes debug lines to log file",
        )
        uncommon_args.add_argument(
            "-mkt",
            "--use_mktorrent",
            action="store_true",
            help="Use mktorrent instead of torf (Latest git version only)",
        )
        uncommon_args.add_argument(
            "-fpm",
            "--force_pymediainfo",
            action="store_true",
            help="Force use PyMediaInfo to extract video codec over regex extraction from file name",
        )
        uncommon_args.add_argument(
            "-ss",
            "--skip_screenshots",
            action="store_true",
            help="Skip screenshot generation and upload for a run (overrides config.env)",
        )
        uncommon_args.add_argument(
            "-let",
            "--load_external_templates",
            action="store_true",
            help="When enabled uploader will load external site templates from ./external/site_templates location",
        )
        uncommon_args.add_argument(
            "-tag", "--tags", nargs="*", help="Send custom tags to all trackers"
        )

    def add_argument(self, *args, **kwargs):
        self.parser.add_argument(*args, **kwargs)

    def parse_args(self):
        return self.parser.parse_args()
