from modules.image_hosts.image_host_base import GGBotImageHostBase
from modules.image_hosts.image_upload_status import GGBotImageUploadStatus


class DummyImageHost(GGBotImageHostBase):
    def __init__(self, image_path: str):
        super().__init__(image_path)

    def upload(self):
        self.upload_status = GGBotImageUploadStatus(
            status=True,
            bb_code_thumb=f'[url=http://ggbot/img1][img]{"t.".join("http://ggbot/img1".rsplit(".", 1))}[/img][/url]',
            bb_code_medium=f'[url=http://ggbot/img1][img]{"m.".join("http://ggbot/img1".rsplit(".", 1))}[/img][/url]',
            bb_code_medium_thumb=f"[url=http://ggbot/img1][img={self.thumb_size}]"
            f'{"m.".join("http://ggbot/img1".rsplit(".", 1))}[/img][/url]',
            image_url="http://ggbot/img1",
        )

    @property
    def img_host(self) -> str:
        return "DUMMY"
