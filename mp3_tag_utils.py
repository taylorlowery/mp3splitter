import eyed3
import os
from typing import List
import platform
import subprocess

from utils import Utilities

class Mp3TagUtilities:

    @staticmethod
    def clean_metadata(filepath: str):
        audio_file = eyed3.load(filepath)
        album = audio_file.tag.album.replace("-", ":", 1)
        artist = audio_file.tag.artist.replace("/", ";")
        album_artist = audio_file.tag.album_artist
        comment = "\n".join([comment for comment in audio_file.tag.comments])
        encoded_by = audio_file.tag.encoded_by
        copyright = audio_file.tag.copyright
        genre = str(audio_file.tag.genre).replace("/", ":")
        # language = audio_file.tag.language
        publisher = audio_file.tag.publisher.replace("/", ":")
        organization = audio_file.tag.publisher.replace("/", ":")
        # subtitle = audio_file.tag.subtitle
        track = audio_file.tag.track_num[0]

        Mp3TagUtilities.set_audio_file_tag(
            filename=filepath,
            album=album,
            artist=artist,
            album_artist=album_artist,
            comment=comment,
            encoded_by=encoded_by,
            copyright=copyright,
            genre=genre,
            # language=language,
            publisher=publisher,
            organization=organization,
            # subtitle=subtitle,
            track=track
        )


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