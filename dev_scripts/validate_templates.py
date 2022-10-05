import os
import json
import fastjsonschema

from pathlib import Path
from fastjsonschema import JsonSchemaException

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