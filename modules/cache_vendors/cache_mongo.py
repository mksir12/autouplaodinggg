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

import functools
import logging

from pymongo import MongoClient

from modules.config import CacheConfig
from modules.exceptions.exception import (
    GGBotCacheClientException,
    GGBotCacheNotInitializedException,
)


def map_cursor_to_list(function):
    @functools.wraps(function)
    def decorator(*args, **kwargs):
        return list(map(lambda d: d, function(*args, **kwargs)))

    return decorator


class Mongo:
    mongo_client = None
    is_mongo_initialized = False
    database = None

    def __init__(self):
        """Method to initialize the connection to a redis database."""
        self.config: CacheConfig = CacheConfig()
        if not self.is_mongo_initialized:
            try:
                self.mongo_client = self._get_mongo_client()
                self.mongo_client.admin.command("ping")
                # self.database = self.mongo_client[
                #     self.config.CACHE_DATABASE
                # ]
                self.database = self.mongo_client["gg-bot-auto-uploader"]
                self.is_mongo_initialized = True
            except Exception as ex:
                logging.fatal(
                    f"[Cache] Failed to connect to Mongo DB. Error: {ex}"
                )
                raise GGBotCacheClientException(
                    f"Failed to connect to Mongo DB. Error: {ex}"
                )

    def _get_mongo_client(self):
        # Provide the mongodb atlas url to connect python to mongodb using pymongo
        if (
            self.config.CACHE_USERNAME is not None
            and len(self.config.CACHE_USERNAME) > 0
        ):
            MONGO_URL = (
                f"mongodb://{self.config.CACHE_USERNAME}:{self.config.CACHE_PASSWORD}"
                f"@{self.config.CACHE_HOST}:{self.config.CACHE_PORT}/{self.config.CACHE_DATABASE} "
            )
        else:
            MONGO_URL = f"mongodb://{self.config.CACHE_HOST}:{self.config.CACHE_PORT}/{self.config.CACHE_DATABASE}"
        MONGO_URL = "mongodb://100.119.76.65:27017/gg-bot-auto-uploader"
        # MONGO_URL = "mongodb://192.168.0.127:27017/gg-bot-auto-uploader"
        return MongoClient(MONGO_URL)

    def hello(self):
        if self.is_mongo_initialized:
            self.mongo_client.admin.command("ping")
            print("Mongo Server Connection Established Successfully")
            return True
        else:
            print("Failed to initialize connection to Mongo server")
            return False

    def __get_collection(self, key):
        if not self.is_mongo_initialized:
            raise GGBotCacheNotInitializedException()
        key = key.split("::")
        return self.database[key[0] + "_" + key[1]]

    def save(self, key, data):
        collection = self.__get_collection(key)
        if "_id" not in data:
            collection.insert_one(data)
        else:
            collection.replace_one({"_id": data["_id"]}, data, upsert=True)

    def delete(self, key, query=None):
        """Method to delete data from the cache stored against a key."""
        collection = self.__get_collection(key)
        if len(key.split("::")) <= 2:
            # no hash provided in key. hence we need to use the user provided query
            # if user has not provided any query then we'll raise an exception
            if query is None:
                raise Exception(
                    "No hash or query provided. Cannot delete document"
                )
            # returns the number of documents deleted
            return collection.delete_many(query)
        else:
            collection.delete_one({"hash": key.split("::")[2]})
            return 1

    @map_cursor_to_list
    def get(self, key, filter=None):
        collection = self.__get_collection(key)
        # <=2 because keys are in the form of GROUP::COLLECTION::KEY
        filter = (
            ({} if filter is None else filter)
            if len(key.split("::")) <= 2
            else {"hash": key.split("::")[2]}
        )
        return collection.find(filter)

    @map_cursor_to_list
    def advanced_get(self, key, limit, page_number, sort_field, filter=None):
        collection = self.__get_collection(key)
        return (
            collection.find(filter if filter is not None else {})
            .skip((page_number - 1) * limit)
            .limit(limit)
            .sort(sort_field, -1)
        )

    def count(self, key, filter=None):
        collection = self.__get_collection(key)
        return collection.count_documents(filter if filter is not None else {})

    def close(self):
        """
        Method to close the connection to the redis server
        This is a wrapper around the redis `hgetall` operation
        """
        if not self.is_mongo_initialized:
            raise GGBotCacheNotInitializedException()
        self.mongo_client.close()
