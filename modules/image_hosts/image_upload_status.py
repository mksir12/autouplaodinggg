class GGBotImageUploadStatus:
    def __init__(
        self,
        *,
        status: bool,
        bb_code_medium_thumb: str = None,
        bb_code_medium: str = None,
        bb_code_thumb: str = None,
        image_url: str = None,
    ):
        self.status = status
        self.image_url = image_url
        self.bb_code_thumb = bb_code_thumb
        self.bb_code_medium = bb_code_medium
        self.bb_code_medium_thumb = bb_code_medium_thumb
