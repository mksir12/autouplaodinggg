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

import os
import json
import fastjsonschema

from pathlib import Path
from fastjsonschema import JsonSchemaException


# the schemas can also be validated at https://www.jsonschemavalidator.net/
# Note: ignore the uri validation error for `upload_form` and `torrents_search` key injsonschemavalidator
working_folder = Path(__file__).resolve().parent.parent
validate = fastjsonschema.compile(json.load(open(f"{working_folder}/schema/site_template_schema.json", "r")))

try:
    path = f"{working_folder}/site_templates/"
    dir_list = os.listdir(path)
    for template in dir_list:
        if template == "default_template.json":
            continue
        print(" * Validating: '" + template + "'")
        schema = validate(json.load(open(f"{path}{template}", "r")))
except JsonSchemaException as json_exception:
    print(json_exception)
    print(f"Validation failed data: {json_exception.value}")
    print(f"Validation failed rule: {json_exception.rule}")
    print(f"Validation failed rule_definition: {json_exception.rule_definition}")