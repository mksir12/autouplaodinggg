# GG Bot Upload Assistant
# Copyright (C) 2022  Noob Master669

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import json
import logging

import fastjsonschema
from fastjsonschema import JsonSchemaException


class TemplateSchemaValidator:
    def __init__(self, schema_location):
        logging.info(
            f"[TemplateSchemaValidator] Loading template schema: {schema_location}"
        )
        self.schema = fastjsonschema.compile(json.load(open(schema_location)))

    def is_valid(self, json_file):
        try:
            self.schema(json.load(open(json_file)))
            return True
        except JsonSchemaException as json_exception:
            logging.error(
                f"[TemplateSchemaValidator] Failed to validate template: {json_file}"
            )
            logging.error(f"[TemplateSchemaValidator] Error: {json_exception}")
            logging.error(
                f"[TemplateSchemaValidator] Validation failed data: {json_exception.value}"
            )
            logging.error(
                f"[TemplateSchemaValidator] Validation failed rule: {json_exception.rule}"
            )
            logging.error(
                f"[TemplateSchemaValidator] Validation failed rule definition: {json_exception.rule_definition}"
            )
            return False
