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

import logging
import sys
from typing import Dict, Callable, Union, Optional

from rich.console import Console

console = Console()


class GGBotHybridMapper:
    def __init__(self, *, hybrid_mappings, torrent_info, exit_program: bool):
        self.hybrid_mappings = hybrid_mappings
        self.torrent_info = torrent_info
        self.exit_program = exit_program

    def __log_all_prerequisites(self, *, translation_value, tracker_settings):
        logging.info(
            "[GGBotHybridMapper::perform_hybrid_mapping] Performing hybrid mapping now..."
        )
        logging.debug(
            "------------------ Hybrid mapping started ------------------"
        )
        for prerequisite in self.hybrid_mappings[translation_value][
            "prerequisite"
        ]:
            logging.info(
                f"[GGBotHybridMapper::perform_hybrid_mapping] Prerequisite :: '{prerequisite}' "
                f"Value :: '{tracker_settings[prerequisite]}' "
            )

    def perform_hybrid_mapping(
        self, *, translation_value, tracker_settings
    ) -> str:
        # logging all the Prerequisite data
        # if any of the Prerequisite data is not available, then this method will not be invoked
        self.__log_all_prerequisites(
            translation_value=translation_value,
            tracker_settings=tracker_settings,
        )

        hybrid_mapping_result: str = self._perform_hybrid_mapping(
            translation_value=translation_value,
            tracker_settings=tracker_settings,
        )
        if hybrid_mapping_result is not None:
            return hybrid_mapping_result

        if self.__is_optional_mapping(translation_value):
            self.__log_optional_mapping_completed_messages()
            return ""

        self.__log_hybrid_mapping_failed_messages(translation_value)

        if self.exit_program:
            sys.exit("Invalid hybrid mapping configuration provided.")
        return "HYBRID_MAPPING_INVALID_CONFIGURATION"

    def _perform_hybrid_mapping(
        self, *, translation_value, tracker_settings
    ) -> Optional[str]:
        for key in self.hybrid_mappings[translation_value]["mapping"]:
            logging.debug(
                f"[GGBotHybridMapper::perform_hybrid_mapping] Matching '{translation_value}' to hybrid key '{key}'..."
            )
            is_valid = None
            for sub_key, sub_val in self.hybrid_mappings[translation_value][
                "mapping"
            ][key].items():
                is_valid = self._is_valid_match(
                    key=key,
                    sub_key=sub_key,
                    sub_val=sub_val,
                    tracker_settings=tracker_settings,
                    is_valid=is_valid,
                )

            if is_valid:
                # is_valid is true all the categories match
                self.__log_mapping_completed_messages(key)
                return key
        return None

    def _is_valid_match(
        self, *, key, sub_key, sub_val, tracker_settings, is_valid
    ):
        # skipping comments provided in the mapping data
        if sub_key == "_comment":
            return is_valid

        selected_value = self.__select_value_from_proper_source(
            sub_key=sub_key, sub_val=sub_val, tracker_settings=tracker_settings
        )

        if selected_value is None:
            # currently hybrid mapping doesn't allow for null / None
            logging.fatal(
                f"[GGBotHybridMapper::perform_hybrid_mapping] Invalid configuration provided for "
                f"hybrid key mapping. Key :: '{key}', sub key :: '{sub_key}', sub value :: '{sub_val}'"
            )
            return False

        if len(sub_val["values"]) == 0:
            return self.__user_has_configured_no_values_for_mapping(
                sub_key, sub_val, is_valid
            )

        evaluator = self._get_evaluator(sub_key, sub_val)
        if evaluator(
            key=key,
            sub_key=sub_key,
            selected_value=selected_value,
            sub_val=sub_val,
        ):
            return True if is_valid is None else is_valid

        selected_value_is_present = self._is_selected_val_present(
            selected_value
        )
        sub_val_is_not_none_or_is_present = (
            self._is_sub_val_is_not_none_or_is_present(sub_val)
        )
        if sub_val_is_not_none_or_is_present and selected_value_is_present:
            logging.debug(
                f"[HybridMapping] The subkey '{sub_key}' '{selected_value}' is present in "
                f"'{sub_val['data_source']}' for '{sub_key}' and '{key}'"
            )
            return True if is_valid is None else is_valid

        logging.debug(
            f"[HybridMapping] The subkey '{sub_key}' '{selected_value}' is NOT present in "
            f"'{sub_val['values']}' for '{sub_key}' and '{key}'"
        )
        return False

    @staticmethod
    def _is_sub_val_is_not_none_or_is_present(sub_val: Dict) -> bool:
        return sub_val["values"][0] == "IS_NOT_NONE_OR_IS_PRESENT"

    @staticmethod
    def _is_selected_val_present(
        selected_value: Union[str, int, float]
    ) -> bool:
        return selected_value is not None and len(str(selected_value)) > 0

    def _get_evaluator(self, sub_key: str, sub_val: Dict) -> Callable:
        return (
            self.__not_in_evaluator
            if self.__negate_mapping(sub_key, sub_val)
            else self.__in_evaluator
        )

    @staticmethod
    def __not_in_evaluator(
        *,
        key: str,
        sub_key: str,
        selected_value: Union[str, int, float],
        sub_val: Dict,
    ) -> bool:
        result = str(selected_value) not in sub_val["values"]
        if result:
            logging.debug(
                f"[HybridMapping] The subkey '{sub_key}' '{selected_value}' is 'NOT PRESENT' in '{sub_val['values']}' "
                f"for '{sub_key}' and '{key}' "
            )
        return result

    @staticmethod
    def __in_evaluator(
        *,
        key: str,
        sub_key: str,
        selected_value: Union[str, int, float],
        sub_val: Dict,
    ) -> bool:
        result = str(selected_value) in sub_val["values"]
        if result:
            logging.debug(
                f"[HybridMapping] The subkey '{sub_key}' '{selected_value}' is 'PRESENT' in '{sub_val['values']}' for "
                f"'{sub_key}' and '{key}'"
            )
        return result

    @staticmethod
    def __user_has_configured_no_values_for_mapping(
        sub_key: str, sub_val: Dict, is_valid: bool
    ) -> bool:
        logging.info(
            f"[GGBotHybridMapper::perform_hybrid_mapping] For the subkey '{sub_key}' the values configured "
            f"'{sub_val['values']}' is empty. Assuming by default as valid and continuing."
        )
        return True if is_valid is None else is_valid

    def __select_value_from_proper_source(
        self, *, sub_key, sub_val, tracker_settings
    ):
        datasource = self.__get_datasource(sub_val, tracker_settings)
        return datasource[sub_key] if sub_key in datasource else None

    def __get_datasource(self, sub_val, tracker_settings):
        return (
            tracker_settings
            if sub_val["data_source"] == "tracker"
            else self.torrent_info
        )

    @staticmethod
    def __negate_mapping(sub_key, sub_val):
        negate_mapping = "not" in sub_val and sub_val["not"]
        if negate_mapping:
            logging.debug(
                f"[HybridMapping] The subkey '{sub_key}' from '{sub_val['data_source']}' "
                f"must NOT be one of {sub_val['values']} for the mapping to be accepted."
            )
        else:
            logging.debug(
                f"[HybridMapping] The subkey '{sub_key}' from '{sub_val['data_source']}' "
                f"need to be one of {sub_val['values']} for the mapping to be accepted."
            )
        return negate_mapping

    @staticmethod
    def __log_mapping_completed_messages(key):
        logging.info(
            f"[HybridMapping] The hybrid key was identified to be '{key}'"
        )
        logging.debug(
            "------------------ Hybrid mapping Completed ------------------"
        )

    @staticmethod
    def __log_optional_mapping_completed_messages():
        # this hybrid mapping is optional. we can log this and return ""
        logging.info(
            "[HybridMapping] Returning '' since this is an optional mapping."
        )
        logging.debug(
            "------------------ Hybrid mapping Completed ------------------"
        )

    def __is_optional_mapping(self, translation_value):
        return self.hybrid_mappings[translation_value]["required"] is False

    @staticmethod
    def __log_hybrid_mapping_failed_messages(translation_value):
        logging.debug(
            "------------------ Hybrid mapping Completed With ERRORS ------------------"
        )
        # this means we either have 2 potential matches or no matches at all (this happens if the media does not fit
        # any of the allowed parameters)
        logging.critical(
            '[HybridMapping] Unable to find a suitable "hybrid mapping" match for this file'
        )
        logging.error(
            "[HybridMapping] Its possible that the media you are trying to upload is not allowed on site (e.g. DVDRip "
            "to BLU is not allowed) "
        )
        console.print(
            f"Failed to perform Hybrid Mapping for '{translation_value}'. This type of upload might not be allowed on "
            f"this tracker.",
            style="Red underline",
        )

    @staticmethod
    def should_delay_mapping(
        *, translation_value, prerequisites, tracker_settings
    ):
        # TODO: check whether this method can be instance method
        logging.info(
            f"[GGBotHybridMapper::should_delay_mapping] Performing 'prerequisite' validation for '{translation_value}'"
        )
        for prerequisite in prerequisites:
            if prerequisite in tracker_settings:
                continue
            logging.info(
                f"[GGBotHybridMapper::should_delay_mapping] The prerequisite '{prerequisite}' for '{translation_value}'"
                f" is not available currently. Skipping hybrid mapping for now and proceeding with remaining "
                f"translations... "
            )
            return True
        return False

    def perform_delayed_hybrid_mapping(self, *, tracker_settings):
        """
        I think this does mapping for all hybrid mappings configured
        """
        no_of_hybrid_mappings = len(self.hybrid_mappings.keys())
        logging.info(
            f"[HybridMapping] Performing hybrid mapping after all translations have completed. No of hybrid mappings "
            f":: '{no_of_hybrid_mappings}' "
        )
        for _ in range(0, no_of_hybrid_mappings):
            for translation_value in self.hybrid_mappings.keys():
                # check whether the particular field can be undergoing hybrid mapping
                delay_mapping = self.should_delay_mapping(
                    translation_value=translation_value,
                    prerequisites=self.hybrid_mappings[translation_value][
                        "prerequisite"
                    ],
                    tracker_settings=tracker_settings,
                )
                if (
                    translation_value not in tracker_settings
                    and not delay_mapping
                ):
                    tracker_settings[
                        translation_value
                    ] = self.perform_hybrid_mapping(
                        translation_value=translation_value,
                        tracker_settings=tracker_settings,
                    )
