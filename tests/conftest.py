from pathlib import Path


class TestUtils:
    @classmethod
    def clean_up(self, pth):
        pth = Path(pth)
        for child in pth.iterdir():
            if child.is_file():
                child.unlink()
            else:
                self.clean_up(child)
        pth.rmdir()
