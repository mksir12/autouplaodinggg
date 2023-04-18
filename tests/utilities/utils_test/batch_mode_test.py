import os
from pathlib import Path

import pytest

from tests.test_utilities import TestUtils
from utilities.utils import files_for_batch_processing

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
