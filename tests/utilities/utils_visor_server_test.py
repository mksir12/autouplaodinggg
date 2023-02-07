from unittest import mock

import mongomock as mongomock
import pytest

import modules.env as Environment
from modules.cache import CacheVendor, CacheFactory
from utilities.utils_visor_server import VisorServerManager


def _convert_oid_to_object_id(item):
    return {"_id": {"$oid": str(item.pop("_id"))}, **item}


class TestVisorServerManager:
    @pytest.fixture(scope="session")
    def mock_mongo_client(self):
        yield mongomock.MongoClient()

    @pytest.fixture()
    @mock.patch("modules.cache_vendors.cache_mongo.Mongo._get_mongo_client")
    @mock.patch("os.getenv", return_value="Mongo")
    def cache(self, mock_env, mock_get_mongo_client, mock_mongo_client):
        mock_get_mongo_client.return_value = mock_mongo_client
        return CacheFactory().create(CacheVendor[Environment.get_cache_type()])

    @pytest.fixture
    def visor_server_manager(self, cache):
        yield VisorServerManager(cache)

    @pytest.fixture(scope="class")
    def mongo_database(self, mock_mongo_client):
        yield mock_mongo_client.get_database("Mongo")

    @pytest.fixture(scope="class")
    def torrents_collection(self, mongo_database):
        yield mongo_database.get_collection("ReUpload_Torrent")

    @pytest.fixture(autouse=True, scope="class")
    def inject_mock_data(self, torrents_collection):
        _id = "_id"
        hash = "hash"
        id = "id"
        name = "name"
        status = "status"
        torrent = "torrent"
        upload_attempt = "upload_attempt"
        date_created = "date_created"
        movie_db = "movie_db"
        possible_matches = "possible_matches"
        torrents_collection.insert_one(
            {
                id: "75857983-8b91-4219-ae02-2121ac3b461e",
                hash: "770B348021268E2EAAF6F3204A3784A7303928F3",
                name: "Highway.Thru.Hell.S06E01.720p.HDTV.x264-aAF",
                status: "SUCCESS",
                torrent: '{"hash": "770B348021268E2EAAF6F3204A3784A7303928F3", "name": '
                '"Highway.Thru.Hell.S06E01.720p.HDTV.x264-aAF", "size": "1812734658", "completed": "1812734658", '
                '"category": "", "content_path": "/downloads/Highway.Thru.Hell.S06E01.720p.HDTV.x264-aAF", '
                '"save_path": "/downloads/"}',
                upload_attempt: 1,
                movie_db: '{"tmdb": "59097", "imdb": "tt2390276", "tvmaze": "3185", "tvdb": "0", "mal": "0", "title": '
                '"Highway Thru Hell", "year": "", "type": "episode"}',
                date_created: "2023-02-05T06:28:15.223019",
                possible_matches: "None",
            }
        )
        torrents_collection.insert_one(
            {
                id: "3c2ce6b8-afc8-4885-8a1b-d19ff33de678",
                hash: "A30CF3E5490C3FDA48B7497ACFE17AFB77162654",
                name: "Plane.2023.1080p.WEB.H264-NAISU",
                status: "DUPE_CHECK_FAILED",
                torrent: '{"hash": "A30CF3E5490C3FDA48B7497ACFE17AFB77162654", "name": "Plane.2023.1080p.WEB.H264-NAISU", '
                '"size": "5715555965", "completed": "5715555965", "category": "", "content_path": '
                '"/downloads/Plane.2023.1080p.WEB.H264-NAISU", "save_path": "/downloads/"}',
                upload_attempt: 1,
                movie_db: '{"tmdb": "646389", "imdb": "tt5884796", "tvmaze": "0", "tvdb": "0", "mal": "0", "title": '
                '"plane", "year": "2023", "type": "movie"}',
                date_created: "2023-02-05T06:45:24.790647",
                possible_matches: "None",
            }
        )
        torrents_collection.insert_one(
            {
                id: "1ac46d54-9276-4f06-a7d1-a101b5a7a17e",
                hash: "B1E36416D3598C91FAC2EE71FA5FF721BA2C7571",
                name: "Highway.Thru.Hell.S06E01.480p.x264-mSD",
                status: "UNKNOWN_FAILURE",
                torrent: '{"hash": "B1E36416D3598C91FAC2EE71FA5FF721BA2C7571", "name": '
                '"Highway.Thru.Hell.S06E01.480p.x264-mSD", "size": "478735146", "completed": "478735146", '
                '"category": "", "content_path": "/downloads/Highway.Thru.Hell.S06E01.480p.x264-mSD", '
                '"save_path": "/downloads/"}',
                upload_attempt: 4,
                movie_db: "None",
                date_created: "2023-02-05T06:36:16.265176",
                possible_matches: "None",
            }
        )
        torrents_collection.insert_one(
            {
                id: "5374c84f-631c-4faa-8241-da1e6980062b",
                hash: "4B302A920B4411CF9D5449ED65525E220C129CED",
                name: "M3GAN.2022.1080p.WEBRip.x264.AAC-AOC",
                status: "SUCCESS",
                torrent: '{"hash": "4B302A920B4411CF9D5449ED65525E220C129CED", "name": '
                '"M3GAN.2022.1080p.WEBRip.x264.AAC-AOC", "size": "2373845821", "completed": "2373845821", '
                '"category": "", "content_path": "/downloads/M3GAN.2022.1080p.WEBRip.x264.AAC-AOC", "save_path": '
                '"/downloads/"}',
                upload_attempt: 1,
                movie_db: '{"tmdb": "536554", "imdb": "tt8760708", "tvmaze": "0", "tvdb": "0", "mal": "0", "title": '
                '"M3GAN", "year": "2022", "type": "movie"}',
                date_created: "2023-02-05T06:55:32.260971",
                possible_matches: "None",
            }
        )

    def test_get_torrent_statistics(self, visor_server_manager):
        assert visor_server_manager.get_torrent_statistics() == {
            "all": 4,
            "failed": 2,
            "partial": 0,
            "successful": 2,
        }

    def test_failed_torrents_statistics(self, visor_server_manager):
        assert visor_server_manager.failed_torrents_statistics() == {
            "all": 4,
            "dupe_check_failure": 1,
            "unknown_failure": 1,
            "upload_failure": 0,
            "partial_failure": 0,
            "tmdb_failure": 0,
        }

    def test_all_torrents(self, visor_server_manager, torrents_collection):
        items = torrents_collection.find({}).limit(20).sort("id", -1)
        expected = {
            "page": {
                "page_number": 1,
                "total_pages": 1,
                "total_torrents": 4,
            },
            "torrents": [_convert_oid_to_object_id(it) for it in items],
        }
        assert visor_server_manager.all_torrents(sort="id") == expected

    def test_torrent_details(self, visor_server_manager, torrents_collection):
        expected = [
            _convert_oid_to_object_id(
                torrents_collection.find_one(
                    {"id": "5374c84f-631c-4faa-8241-da1e6980062b"}
                )
            )
        ]
        assert (
            visor_server_manager.torrent_details(
                torrent_id="5374c84f-631c-4faa-8241-da1e6980062b"
            )
            == expected
        )

    def test_get_torrent_details_object(
        self, visor_server_manager, torrents_collection
    ):
        expected = [
            _convert_oid_to_object_id(
                torrents_collection.find_one(
                    {"id": "5374c84f-631c-4faa-8241-da1e6980062b"}
                )
            )
        ]
        assert (
            visor_server_manager.get_torrent_details_object(
                torrent_id="5374c84f-631c-4faa-8241-da1e6980062b"
            )
            == expected
        )

    def test_update_torrent_object(
        self, visor_server_manager, torrents_collection
    ):
        existing_item = torrents_collection.find_one(
            {"id": "5374c84f-631c-4faa-8241-da1e6980062b"}
        )
        visor_server_manager.update_torrent_object(
            {"_id": existing_item["_id"], "key": "value"}
        )
        updated_item = torrents_collection.find_one(
            {"_id": existing_item["_id"]}
        )
        assert updated_item == {"_id": existing_item["_id"], "key": "value"}
