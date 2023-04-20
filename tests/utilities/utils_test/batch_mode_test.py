import os
from pathlib import Path
from unittest.mock import patch

import pytest

from tests.test_utilities import TestUtils
from utilities.utils import files_for_batch_processing, validate_batch_mode

working_folder = Path(__file__).resolve().parent.parent.parent.parent
temp_working_dir = "/tests/working_folder"
folder = f"{working_folder}{temp_working_dir}"
batch_folder = f"{folder}/batch"


@pytest.fixture(autouse=True)
def setup_and_teardown_files():
    if Path(folder).is_dir():
        TestUtils.clean_up(folder)

    Path(f"{batch_folder}/subdir1").mkdir(
        parents=True, exist_ok=True
    )  # batch/subdir1 folder
    Path(f"{batch_folder}/subdir2").mkdir(
        parents=True, exist_ok=True
    )  # batch/subdir2 folder
    Path(f"{batch_folder}/subdir3").mkdir(
        parents=True, exist_ok=True
    )  # batch/subdir3 folder
    open(os.path.join(batch_folder, "file1.mkv"), "a").close()
    open(os.path.join(batch_folder, "file2.mp4"), "a").close()
    open(os.path.join(batch_folder, "subdir1", "file3.avi"), "a").close()
    open(os.path.join(batch_folder, "subdir1", "file4.mkv"), "a").close()
    open(os.path.join(batch_folder, "subdir2", "file5.mpg"), "a").close()
    open(os.path.join(batch_folder, "subdir2", "file6.mp4"), "a").close()
    open(os.path.join(batch_folder, "subdir3", "file7.mpeg"), "a").close()
    open(os.path.join(batch_folder, "subdir3", "file8.avi"), "a").close()
    yield
    TestUtils.clean_up(folder)


def test_files_for_batch_processing():
    expected_output = [
        os.path.join(batch_folder, "file1.mkv"),
        os.path.join(batch_folder, "file2.mp4"),
        os.path.join(batch_folder, "subdir1", "file4.mkv"),
        os.path.join(batch_folder, "subdir2", "file6.mp4"),
    ]
    obtained_list = files_for_batch_processing([batch_folder])
    assert len(obtained_list) == len(expected_output)
    assert set(obtained_list) == set(expected_output)


def test_files_for_batch_processing_empty_path():
    input_path = []
    expected_output = []
    assert files_for_batch_processing(input_path) == expected_output


def test_files_for_batch_processing_nonexistent_path():
    input_path = [f"{batch_folder}/nonexistent/path"]
    expected_output = []
    assert files_for_batch_processing(input_path) == expected_output


def test_files_for_batch_processing_invalid_extension():
    input_path = [f"{batch_folder}/subdir3"]
    expected_output = []
    assert files_for_batch_processing(input_path) == expected_output


@pytest.fixture
def metadata_ids():
    return {"id_1": "", "id_2": ""}


def test_validate_batch_mode_returns_true_if_batch_mode_is_false(metadata_ids):
    assert (
        validate_batch_mode(
            batch_mode=False, path=["/some/path"], metadata_ids=metadata_ids
        )
        is True
    )


def test_validate_batch_mode_returns_false_if_batch_mode_is_true_and_metadata_ids_is_not_empty():
    metadata_ids = {"id_1": "123", "id_2": "456"}
    assert (
        validate_batch_mode(
            batch_mode=True, path=["/some/path"], metadata_ids=metadata_ids
        )
        is False
    )


def test_validate_batch_mode_returns_false_if_batch_mode_is_true_and_path_has_multiple_directories(
    metadata_ids,
):
    with patch(
        "utilities.utils._log_error_and_exit_batch_and_multiple_path"
    ) as mock_error_func:
        assert (
            validate_batch_mode(
                batch_mode=True,
                path=["/path1", "/path2"],
                metadata_ids=metadata_ids,
            )
            is False
        )
        mock_error_func.assert_called_once()


def test_validate_batch_mode_returns_false_if_batch_mode_is_true_and_path_is_not_a_directory(
    metadata_ids,
):
    with patch("os.path.isdir") as mock_isdir, patch(
        "utilities.utils._log_error_and_exit_batch_and_file_path"
    ) as mock_error_func:
        mock_isdir.return_value = False
        assert (
            validate_batch_mode(
                batch_mode=True,
                path=["/path/to/file"],
                metadata_ids=metadata_ids,
            )
            is False
        )
        mock_error_func.assert_called_once()


def test_validate_batch_mode_returns_true_if_batch_mode_is_true_and_path_has_one_directory(
    metadata_ids,
):
    with patch("os.path.isdir") as mock_isdir:
        mock_isdir.return_value = True
        assert (
            validate_batch_mode(
                batch_mode=True,
                path=["/path/to/directory"],
                metadata_ids=metadata_ids,
            )
            is True
        )
