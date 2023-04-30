#!/usr/bin/env python3
import os
import pathlib
import platform
import subprocess
import sys
import xml.etree.ElementTree as ET
from typing import Tuple, List, Any
from utils import Utilities
from mp3_tag_utils import Mp3TagUtilities
import re
import typer

import eyed3


def get_markers_xml(filename: str, text_frames: Any) -> str:
    xml_file = filename.replace(".mp3", ".xml")
    xml_fixed_file = filename.replace(".mp3", "_fixed.xml")

    xml_text = ""

    # check for filename_fixed.xml and use that to set markers
    if os.path.exists(xml_fixed_file):
        with open(xml_fixed_file, "r") as f_f:
            xml_text = f_f.read()
        return xml_text

    try:
        for frame in text_frames:
            xml_text = frame.text
            if "Markers" in xml_text:
                if not os.path.exists(xml_file):
                    with open(xml_file, "w") as f:
                        f.write(xml_text)
                break
    except Exception as e:
        print(f"Error retrieving marker data from mp3: {e}")

    return xml_text


def build_segments(audio_file_path: str) -> Tuple[str, List[Tuple[str, str]]]:
    """Creates a list or segments representing chapter names with start and end times
        Args:
            audio_file_path (str): Path to an mp3 file
        Returns:
            Tuple(str, List(str, str)): a tuple representing end time of the file, and a list of tuples representing chapter names and thier start times
    """
    try:
        audio = eyed3.load(audio_file_path)
        text_frames = audio.tag.user_text_frames
        end_time = Utilities.convert_time(audio.info.time_secs)
        segments = []
        xml_text = get_markers_xml(filename=audio_file_path, text_frames=text_frames)
        markers = ET.fromstring(xml_text)
        base_chapter = "invalid I hope I never have chapters like this"
        chapter_section = 0
        segments = []
        for marker in markers:
            name, start_time = parse_marker(previous_chapter=base_chapter, marker=marker)
            base_chapter = name
            segments.append((name, start_time))
        segments = combine_chapter_sections(segments=segments)
        return end_time, segments
    except Exception as e:
        print(e)


def combine_chapter_sections(segments: List[Tuple[str, str]]) -> List[Tuple[str, str]]:
    """Combine all markers for sections of the same chapter into single markers"""
    i = 0
    while i < len(segments) - 1:
        current = segments[i][0]
        next = segments[i + 1][0]
        if are_same_chapter(current, next):
            # segments[i] = (current_str, next[1])
            del segments[i + 1]
        else:
            i += 1
    return segments


def are_same_chapter(chapter_title1: str, chapter_title2: str, patterns_to_strip=[r"_\(([0-9]{2})?\:?[0-9]{2}\:[0-9]{2}\)"]) -> bool:
    """Determines whether two strings (filenames or segments from xml) refer to the same chapter.
    Assumes both strings contain a chapter title and a timestamp in the format (00:00:00)"""
    # regex pattern to match timestamp (00:00:00) or (00:00)
    for pattern in patterns_to_strip:
        chapter_title1 = re.sub(pattern, "", chapter_title1)
        chapter_title2 = re.sub(pattern, "", chapter_title2.strip())
    return chapter_title2.startswith(chapter_title1)


def parse_marker(previous_chapter: str, marker: Any) -> Tuple[str, str]:
    """Parses a chapter marker into a chapter name and start time
        Args:
            marker (Any): XML Marker
        Returns:
            Tuple (str, str): Chapter name and start time in MP3
    """
    # chapters can be split into several shorter sections and end up being
    # shown like this:
    #    Chapter 1         00:00.000
    #    Chapter 1 (03:21) 03:21.507
    #    Chapter 1 (06:27) 06:27.227
    #  Use the chapter name with a counter to create:
    #    Chapter 1-00      00:00.000
    #    Chapter 1-01      03:21.507
    #    Chapter 1-02      06:27.227
    name = marker[0].text.strip()
    if not name.startswith(previous_chapter):
        previous_chapter = name
        chapter_section = 0
    name = f"{previous_chapter}_{chapter_section:02}"
    chapter_section += 1
    start_time = marker[1].text
    # ffmpeg really doesn't like times with minute field > 60, but I've
    # found some books that have this.
    time_args = start_time.split(":")
    h = 0
    m = 0
    s = 0
    if len(time_args) == 2:
        m, s = time_args
        m = int(m)
        h = 0
    elif len(time_args) == 3:
        h, m, s = time_args
        h = int(h)
        m = int(m)
    while m > 59:
        h += 1
        m -= 60
    if h != 0:
        start_time = "{0:02}:{1:02}:{2}".format(h, m, s)

    name = name.replace(" ", "_")
    return (name, start_time)


def complete_segments(segments: List[Tuple[str, str]], final_time: str) -> List[Tuple[str, str, str]]:
    new_segments = []
    for index, segment in enumerate(segments):
        if index < len(segments) - 1:
            end_time = segments[index + 1][1]
        else:
            end_time = final_time
        new_segments.append((segment[0], segment[1], end_time))
    return new_segments


def split_file(audio_file_path: str, segments: List[Tuple[str, str, str]], output_dir: str="") -> List[str]:
    fn = pathlib.Path(audio_file_path)
    real_path = os.path.realpath(audio_file_path)
    dir_path = os.path.dirname(real_path)
    if output_dir == "":
        output_dir = dir_path
    else:
        output_dir = os.path.realpath(output_dir)
        dir_path = pathlib.Path(output_dir)
        if not pathlib.Path.is_dir(dir_path):
            pathlib.Path.mkdir(dir_path)
    segs = []
    for index, segment in enumerate(segments):
        title, start_timestamp, end_timestamp = segment
        output_file_path = f"{output_dir}\\{fn.stem}_{index:03}_{Utilities.clean_filename(title)}--split{fn.suffix}"
        already_created = os.path.exists(output_file_path)

        if not already_created:
            try:
                command = ["ffmpeg",
                           "-i",
                           audio_file_path,
                           "-acodec",
                           "copy",
                           "-ss",
                           start_timestamp,
                           "-to",
                           end_timestamp,
                           output_file_path,
                           ]

                is_win = 'Win' in platform.system()
                # ffmpeg requires an output file and so it errors when it does not
                # get one so we need to capture stderr, not stdout.
                output = subprocess.check_output(command, stderr=subprocess.STDOUT,
                                                 universal_newlines=True,
                                                 shell=is_win)

            except Exception as e:
                if not os.path.exists(output_file_path):
                    print(f"[ERROR] Unable to create file for {segment}: ", e)
            if os.path.exists(output_file_path):
                segs.append(output_file_path)

                # replace title tag with segment title
                Mp3TagUtilities.set_audio_file_tag(output_file_path,
                                                   title=segment[0].replace("_00", "").replace("_", " "))
                # clean file metadata
                Mp3TagUtilities.clean_metadata(output_file_path)

                # Square Image
                Mp3TagUtilities.square_audio_file_image(output_file_path)

                print(f"Created {output_file_path}")
        else:
            print(f"File {output_file_path} already exists")
    return segs


def process_single_mp3(filename: str, output_dir: str = "") -> List[str]:
    split_files = []
    try:
        print(f"Processing:{filename}")
        end_time, segments = build_segments(filename)
        segments = complete_segments(segments, end_time)
        segs = split_file(audio_file_path=filename, segments=segments, output_dir=output_dir)
        split_files.extend(segs)
    except Exception as e:
        print(f"[ERROR] error splitting {filename}: {e}")
    return split_files

def sanitize_filepath(filepath: str) -> str:
    return filepath \
        .replace('"', '') \
        .replace("'", "") \
        .replace("%", "") \
        .replace(":", "")

def process_filepath(filepath: str, output_dir: str) -> List[str]:
    split_files = []
    all_mp3s: List[str] = []
    if os.path.isfile(filepath):
        all_mp3s.append(filepath)
    elif os.path.isdir(filepath):
        dir_mp3s = Utilities.get_mp3_files_in_directory(filepath)
        for mp3 in dir_mp3s:
            all_mp3s.append(mp3)

    for mp3 in all_mp3s:
        split_files.extend(process_single_mp3(filename=mp3, output_dir=output_dir))

    chapterized_output = combine_chapters(split_files=split_files)
    return chapterized_output

def combine_chapters(split_files: List[str]) -> List[str]:
    """Combine split files from the same chapter into single files"""
    final_chapters = []
    pattern_suffix = r"(_\(00_00\))?(_00)?--split.mp3"
    pattern_chapter_part = r"-Part([0-9]{2})?_([0-9]{3})?_"
    patterns = [pattern_suffix, pattern_chapter_part]
    while len(split_files) > 0:
        chapter_files = []
        current = split_files.pop(0)
        chapter_files.append(current)
        for file in split_files:
            if are_same_chapter(current, file, patterns_to_strip=patterns):
                chapter_files.append(file)
                split_files.remove(file)
            else:
                break
        filepath = re.sub(pattern_chapter_part, "_", current)
        filepath = filepath.replace("_00", "")
        if len(chapter_files) > 1:
            ffmpeg_output = Mp3TagUtilities.concat_mp3s(file_names=chapter_files, output_file_path=filepath)
        else:
            path = pathlib.Path(current)
            path.replace(filepath)
        final_chapters.append(filepath)

    return final_chapters


def main(filepath: str, output_dir: str = ""):
    """
    Attempts to split mp3s into chapters based on mp3 tag data and output them in the specified directory
    If FILEPATH is a valid path to a directory, it will attempt to split all mp3s in the directory.
    Optional --output-dir specifies the directory where the split mp3s should be deposited. If omitted,
    deposits the split files in their source directory
    """
    filepath = filepath.rstrip("\"'\\").lstrip("\"'")
    output_dir = output_dir.rstrip("\"'").lstrip("\"'")
    print(f"filepath: {filepath}")
    print(f"output: {output_dir}")
    chapterized_output = process_filepath(filepath=filepath, output_dir=output_dir)
    if len(chapterized_output) > 0:
        print("Created the following chapterized files:\n")
        for file in chapterized_output:
            print(f"\t{file}\n")
    else:
        print(f"Kick rocks, no files found at '{filepath}'")

if __name__ == "__main__":
    typer.run(main)
