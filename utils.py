import os
from typing import List
import platform
import subprocess
import pathlib

class Utilities:

    @staticmethod
    def convert_time(time_secs: int) -> str:
        """Convert a number of seconds into a human-readable string representing total hours, minutes, and seconds
            Args:
                time_secs (int): count of seconds
            Returns:
                str: human readable string representing hours, minutes, and seconds
        """
        fraction = int((time_secs % 1) * 1000)
        seconds = int(time_secs)
        min, sec = divmod(seconds, 60)
        hour, min = divmod(min, 60)
        return f"{hour:02}:{min:02}:{sec:02}.{fraction:03}"

    @staticmethod
    def get_mp3_files_in_directory(directory: str, exclude_split_file: bool=True) -> List[str]:
        mp3_paths = []
        dir_path = pathlib.Path(directory)
        files = dir_path.iterdir()
        for file in files:
            if file.suffix == ".mp3" and ((not exclude_split_file) or (not str(file).endswith("--split.mp3"))):
                mp3_paths.append(str(file.resolve()))
            else:
                if pathlib.Path.is_dir(file):
                    mp3_paths.extend(get_mp3_files_in_directory(fullpath))
        return mp3_paths

    @staticmethod
    def clean_filename(filename: str) -> str:
        invalid_chars = '\\/*?"\'<>|'
        return ''.join(c for c in filename if c not in invalid_chars).replace(':', '_')

    @staticmethod
    def execute_system_command(command: List[str]) -> str:
        is_win = 'Win' in platform.system()
        # ffmpeg requires an output file and so it errors when it does not
        # get one so we need to capture stderr, not stdout.
        output = subprocess.check_output(command, stderr=subprocess.STDOUT,
                                         universal_newlines=True,
                                         shell=is_win)
        return output