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

import base64
import hashlib
import hmac
import struct
import time


# Source: https://github.com/TheDanniCraft/2FA-Generator
def get_hotp_token(secret, intervals_no):
    key = base64.b32decode(secret, True)
    # decoding our key
    msg = struct.pack(">Q", intervals_no)
    # conversions between Python values and C structs represent
    h = hmac.new(key, msg, hashlib.sha1).digest()
    o = o = h[19] & 15
    # Generate a hash using both of these. Hashing algorithm is HMAC
    h = (struct.unpack(">I", h[o : o + 4])[0] & 0x7FFFFFFF) % 1000000
    # unpacking
    return h


def get_totp_token(secret):
    # ensuring to give the same otp for 30 seconds
    x = str(get_hotp_token(secret, intervals_no=int(time.time()) // 30))
    # adding 0 in the beginning till OTP has 6 digits
    while len(x) != 6:
        x = x + "0"
    return x
