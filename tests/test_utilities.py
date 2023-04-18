from pathlib import Path


class TestUtils:
    @classmethod
    def clean_up(cls, pth):
        pth = Path(pth)
        for child in pth.iterdir():
            if child.is_file():
                child.unlink()
            else:
                cls.clean_up(child)
        pth.rmdir()
