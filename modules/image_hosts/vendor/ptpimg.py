import logging

import ptpimg_uploader
from rich.console import Console

from ..image_host_base import GGBotImageHostBase
import modules.env as Environment
from ..image_upload_status import GGBotImageUploadStatus

# For more control over rich terminal content, import and construct a Console object.
console = Console()


class PTPImgImageHost(GGBotImageHostBase):
    def __init__(self, image_path: str):
        super().__init__(image_path)
        self.api_key = Environment.get_ptpimg_api_key()

    @property
    def img_host(self) -> str:
        return "ptpimg"

    def upload(self):
        try:
            ptp_img_upload = ptpimg_uploader.upload(
                api_key=self.api_key,
                files_or_urls=[self.image_path],
                timeout=15,
            )
            # Make sure the response we get from ptpimg is a list
            assert isinstance(ptp_img_upload, list)
            logging.debug(
                f"[PTPImgImageHost::upload] Ptpimg image upload response: {ptp_img_upload}"
            )
            # TODO need to see the response and decide on the thumbnail image and size
            # Pretty sure ptpimg doesn't compress/host multiple 'versions' of the same image
            # so we use the direct image link for both parts of the bbcode (url & img)
            self.upload_status = GGBotImageUploadStatus(
                status=True,
                bb_code_medium_thumb=f"[url={ptp_img_upload[0]}][img={self.thumb_size}]{ptp_img_upload[0]}[/img][/url]",
                bb_code_medium=f"[url={ptp_img_upload[0]}][img]{ptp_img_upload[0]}[/img][/url]",
                bb_code_thumb=f"[url={ptp_img_upload[0]}][img]{ptp_img_upload[0]}[/img][/url]",
                image_url=ptp_img_upload[0],
            )
        except AssertionError:
            logging.exception(
                "[PTPImgImageHost::upload] ptpimg uploaded an image but returned something unexpected "
                "(should be a list)"
            )
            console.print(
                "\nUnexpected response from ptpimg upload (should be a list). No image link found\n",
                style="Red",
                highlight=False,
            )
        except Exception:
            logging.exception(
                "[PTPImgImageHost::upload] ptpimg upload failed, double check the ptpimg API Key & try again."
            )
            console.print(
                "\nptpimg upload failed. double check the [bold]ptpimg_api_key[/bold] in [bold]config.env[/bold]\n",
                style="Red",
                highlight=False,
            )
