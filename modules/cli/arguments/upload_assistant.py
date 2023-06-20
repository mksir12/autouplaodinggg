from modules.cli.arguments.arg_parser import GGBotArgumentParser


class UploadAssistantArgumentParser(GGBotArgumentParser):
    def __init__(self):
        super().__init__(description="GG-BOT Auto Uploader CLI Arguments")
        self.add_argument(
            "-p",
            "--path",
            nargs="*",
            required=True,
            help="Use this to provide path(s) to file/folder",
        )
        self.add_argument(
            "-tmdb", nargs=1, help="Use this to manually provide the TMDB ID"
        )
        self.add_argument(
            "-imdb", nargs=1, help="Use this to manually provide the IMDB ID"
        )
        self.add_argument(
            "-tvmaze",
            nargs=1,
            help="Use this to manually provide the TVMaze ID",
        )
        self.add_argument(
            "-tvdb", nargs=1, help="Use this to manually provide the TVDB ID"
        )
        self.add_argument(
            "-mal",
            nargs=1,
            help="Use this to manually provide the MAL ID. If uploader detects any MAL id during search, this will be "
            "ignored.",
        )
        self.add_argument(
            "-title", nargs=1, help="Custom title provided by the user"
        )
        self.add_argument(
            "-type", nargs=1, help="Use to manually specify 'movie' or 'tv'"
        )
        self.add_argument(
            "-reupload",
            nargs="*",
            help="This is used in conjunction with autodl to automatically re-upload any filter matches",
        )
        self.add_argument(
            "-batch",
            action="store_true",
            help="Pass this arg if you want to upload all the files/folder within the folder you specify with the "
            "'-p' arg",
        )
        self.add_argument(
            "-disc",
            action="store_true",
            help="If you are uploading a raw dvd/bluray disc you need to pass this arg",
        )
        self.add_argument(
            "-e",
            "--edition",
            nargs="*",
            help="Manually provide an 'edition' (e.g. Criterion Collection, Extended, Remastered, etc)",
        )
        self.add_argument(
            "-nfo",
            nargs=1,
            help="Use this to provide the path to an nfo file you want to upload",
        )
        self.add_argument(
            "-dry",
            "--dry_run",
            action="store_true",
            help="Used for debugging. Writes debug lines to log and will also skip the upload",
        )
        self.add_argument(
            "-r",
            "--resume",
            action="store_true",
            help="Resume previously unfinished upload.",
        )
        self.add_argument(
            "-3d", action="store_true", help="Mark the upload as 3D content"
        )
        self.add_argument(
            "-foreign",
            action="store_true",
            help="Mark the upload as foreign content [Non-English]",
        )
        self.add_argument(
            "-amf",
            "--allow_multiple_files",
            action="store_true",
            help="Override the default behavior and allow multiple files to be added in one torrent",
        )
