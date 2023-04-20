from marshmallow import Schema, fields, post_load
from marshmallow.validate import OneOf

from modules.cache_vendors.constants import available_actions, TorrentActions
from modules.visor.exceptions import GGBotVisorFieldValidationError


class GGBotReUploaderSchema(Schema):
    pass


class UpdateTmdbSchema(GGBotReUploaderSchema):
    tmdb = fields.Str(missing=None)
    imdb = fields.Str(missing=None)

    @post_load
    def validate(self, data):
        if data["tmdb"] is None and data["imdb"] is None:
            raise GGBotVisorFieldValidationError(
                "One of TMDb or IMDb id is required"
            )


class ActionItems(GGBotReUploaderSchema):
    action = fields.Str(required=True, validate=OneOf(available_actions))
    action_options = fields.Dict(required=True, default={})

    @post_load
    def parse_action_object(self, data):
        if data["action"] == TorrentActions.UPDATE_TMDB:
            data["action_options"] = UpdateTmdbSchema().dump(
                data["action_options"]
            )
        return data


class GGBotTorrentSchema(GGBotReUploaderSchema):
    id = fields.Str(required=True)
    action_items = fields.Nested(ActionItems, required=True)
