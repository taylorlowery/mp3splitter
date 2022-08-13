import eyed3
import os
from typing import List
import platform
import subprocess

from utils import Utilities

class Mp3TagUtilities:

    @staticmethod
    def set_audio_file_tag(filename: str, **kwargs):
        audio_file = eyed3.load(filename)
        for k, v in kwargs.items():
            setattr(audio_file.tag, k, v)

        audio_file.tag.save()

    @staticmethod
    def concat_mp3s(file_names: List[str], output_file_name: str, title: str) -> str:
        directory = os.path.dirname(os.path.abspath(file_names[0]))
        if os.path.dirname(output_file_name) != directory:
            output_file_name = os.path.join(directory, output_file_name)
        tmp_list_file_path = os.path.join(directory, "tmp_files_list.txt")
        with open(tmp_list_file_path, "w") as f:
            f.writelines([f"file '{os.path.abspath(file)}'\n" for file in file_names])

        command = ["ffmpeg",
                   "-f",
                   "concat",
                   "-safe",
                   "0",
                   "-i",
                   f"{tmp_list_file_path}",
                   "-c",
                   "copy",
                   f"{output_file_name}"]

        try:
            output = Utilities.execute_system_command(command=command)
            Mp3TagUtilities.set_audio_file_tag(output_file_name, title=title)
        except Exception as e:
            pass
        os.remove(tmp_list_file_path)
        return output