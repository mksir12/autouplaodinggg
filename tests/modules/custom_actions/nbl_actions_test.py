import pytest

from modules.custom_actions.nbl_actions import season_pack_dupe


class TestNBLCustomActions:
    @pytest.mark.parametrize(
        ("torrent_info", "expected"),
        [
            pytest.param(
                {"episode_number": "1"}, {}, id="single_episode_release"
            ),
            pytest.param(
                {"episode_number": 1}, {}, id="single_episode_release_2"
            ),
            pytest.param(
                {"episode_number": "0"}, {"ignoredupes": "1"}, id="season_pack"
            ),
            pytest.param(
                {"episode_number": 0}, {"ignoredupes": "1"}, id="season_pack_2"
            ),
            pytest.param({}, {"ignoredupes": "1"}, id="season_pack_3"),
        ],
    )
    def test_season_pack_dupe(self, torrent_info, expected):
        tracker_settings = {}
        season_pack_dupe(torrent_info, tracker_settings, None)
        assert tracker_settings == expected
