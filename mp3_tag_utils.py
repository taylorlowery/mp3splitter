import eyed3
import os
from typing import List, Dict, Any
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
    def set_tag_from_another_file(source_filename: str, target_filename: str) -> None:
        source_tag_dict = Mp3TagUtilities.get_audio_file_tag_as_dict(source_filename)
        Mp3TagUtilities.set_audio_file_tag(filename=target_filename, clear=True, **source_tag_dict)

    @staticmethod
    def get_audio_file_tag_as_dict(filename: str) -> Dict[str, Any]:
        tag_dict = {}
        audio_file = eyed3.load(filename)
        tag_dict["album"] = audio_file.tag.album
        tag_dict["artist"] = audio_file.tag.artist
        tag_dict["album_artist"] = audio_file.tag.album_artist
        tag_dict["comment"] = "\n".join([comment.text for comment in audio_file.tag.comments])
        tag_dict["encoded_by"] = audio_file.tag.encoded_by
        tag_dict["copyright"] = audio_file.tag.copyright
        tag_dict["genre"] = str(audio_file.tag.genre)
        # language = audio_file.tag.language
        tag_dict["publisher"] = audio_file.tag.publisher
        tag_dict["organization"] = audio_file.tag.publisher
        # subtitle = audio_file.tag.subtitle
        tag_dict["title"] = audio_file.tag.title
        tag_dict["track"] = audio_file.tag.track_num[0]
        return tag_dict

    @staticmethod
    def set_audio_file_tag(filename: str, clear: bool=False, **kwargs):
        audio_file = eyed3.load(filename)
        if clear:
            audio_file.tag.clear()
        for k, v in kwargs.items():
            setattr(audio_file.tag, k, v)

        audio_file.tag.save()

    @staticmethod
    def concat_mp3s(file_names: List[str], output_file_path: str) -> str:
        directory = os.path.dirname(os.path.abspath(file_names[0]))
        if os.path.dirname(output_file_path) != directory:
            output_file_name = os.path.basename(output_file_path)
            output_file_path = os.path.join(directory, output_file_name)
        tmp_list_file_path = os.path.join(directory, "tmp_files_list.txt")
        edited_filenames = [os.path.abspath(file).replace("/", "\\").replace("'", "\'") for file in file_names]
        with open(tmp_list_file_path, "w") as f:
            # f.writelines([f"file '{os.path.abspath(file)}'\n" for file in file_names])
            f.writelines([f"file '{file}'\n" for file in edited_filenames])

        command = ["ffmpeg",
                   "-y",
                   "-f",
                   "concat",
                   "-safe",
                   "0",
                   "-i",
                   f"{tmp_list_file_path}",
                   "-c",
                   "copy",
                   f"{output_file_path}"]

        try:
            output = Utilities.execute_system_command(command=command)
            Mp3TagUtilities.set_tag_from_another_file(source_filename=file_names[0], target_filename=output_file_path)
            os.remove(tmp_list_file_path)
            for file in file_names:
                if file != output_file_path:
                    os.remove(file)
            return output
        except Exception as e:
            raise e
