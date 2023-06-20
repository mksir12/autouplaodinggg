from modules.cli.arguments.arg_parser import GGBotArgumentParser


class AutoUploaderArgumentParser(GGBotArgumentParser):
    def __init__(self):
        super().__init__(description="GG-BOT Auto Uploader CLI Arguments")
        self.add_argument(
            "-c",
            "--continuous",
            action="store_true",
            help="Run the auto uploader in continuous mode",
        )
        self.add_argument(
            "-p",
            "--path",
            nargs=1,
            required=True,
            help="Use this to provide path to folder to watch",
        )
