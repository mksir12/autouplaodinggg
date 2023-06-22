# GG Bot Upload Assistant
# Copyright (C) 2022  Noob Master669
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
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

    def __str__(self):
        return f"GGBotImageUploadStatus(status={self.status}, bb_code_medium_thumb={self.bb_code_medium_thumb}, bb_code_medium={self.bb_code_medium}, bb_code_thumb={self.bb_code_thumb}, image_url={self.image_url})"
