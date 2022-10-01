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


def build_segments(filename: str) -> Tuple[str, List[Tuple[str, str]]]:
    """Creates a list or segments representing chapter names with start and end times
        Args:
            filename (str): Path to an mp3 file
        Returns:
            Tuple(str, List(str, str)): a tuple representing end time of the file, and a list of tuples representing chapter names and thier start times
    """
    try:
        audio = eyed3.load(filename)
        text_frames = audio.tag.user_text_frames
        end_time = Utilities.convert_time(audio.info.time_secs)
        segments = []
        xml_text = get_markers_xml(filename=filename, text_frames=text_frames)
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


def are_same_chapter(chapter_title1: str, chapter_title2: str, pattern=r"_\(([0-9]{2})?\:?[0-9]{2}\:[0-9]{2}\)") -> bool:
    """Determines whether two strings (filenames or segments from xml) refer to the same chapter.
    Assumes both strings contain a chapter title and a timestamp in the format (00:00:00)"""
    # regex pattern to match timestamp (00:00:00) or (00:00)
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


def split_file(filename: str, segments: List[Tuple[str, str, str]]) -> List[str]:
    fn = pathlib.Path(filename)
    real_path = os.path.realpath(filename)
    dir_path = os.path.dirname(real_path)
    segs = []
    for index, segment in enumerate(segments):
        title, start_timestamp, end_timestamp = segment
        output_file_path = f"{dir_path}\\{fn.stem}_{index:03}_{Utilities.clean_filename(title)}--split{fn.suffix}"
        already_created = os.path.exists(output_file_path)

        if not already_created:
            try:
                command = ["ffmpeg",
                           "-i",
                           "" + filename + "",
                           "-acodec",
                           "copy",
                           "-ss",
                           f"{start_timestamp}",
                           "-to",
                           f"{end_timestamp}",
                           f"{output_file_path}",
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

                Mp3TagUtilities.clean_metadata(output_file_path)

                print(f"Created {output_file_path}")
        else:
            print(f"File {output_file_path} already exists")
    return segs


def process_single_mp3(filename: str) -> List[str]:
    split_files = []
    try:
        print(f"Processing:{filename}")
        end_time, segments = build_segments(filename)
        segments = complete_segments(segments, end_time)
        segs = split_file(filename, segments)
        split_files.extend(segs)

        with open("copyit.sh", "w") as ff:
            print("#!/bin/sh", file=ff)
            print("mkdir /media/usb0/book", file=ff)
            for seg in split_files:
                print(f"cp {seg} /media/usb0/book/", file=ff)
    except Exception as e:
        print(f"[ERROR] error splitting {filename}: {e}")
    return split_files


def process_filepath(filename: str) -> List[str]:
    split_files = []
    if os.path.isfile(filename):
        split_files.extend(process_single_mp3(filename))
    elif os.path.isdir(filename):
        mp3s = Utilities.get_mp3_files_in_directory(filename)
        for mp3 in mp3s:
            split_files.extend(process_single_mp3(mp3))
    chapterized_output = combine_chapters(split_files=split_files)
    return chapterized_output

def combine_chapters(split_files: List[str]) -> List[str]:
    """Combine split files from the same chapter into single files"""
    final_chapters = []
    pattern = r"_\(([0-9]{2})?\:?[0-9]{2}\:[0-9]{2}\)_00--split.mp3"
    while len(split_files) > 0:
        chapter_files = []
        current = split_files.pop(0)
        chapter_files.append(current)
        for file in split_files:
            if are_same_chapter(current, file, pattern=pattern):
                chapter_files.append(file)
                split_files.remove(file)
        if len(chapter_files) > 1:
            combined_files = Mp3TagUtilities.concat_mp3s(chapter_files, current)
            final_chapters.extend(combined_files)
        else:
            final_chapters.extend(chapter_files)

    return final_chapters

if __name__ == "__main__":
    for filename in sys.argv[1:]:
        chapterized_output = process_filepath(filename)
        if len(chapterized_output) > 0:
            print("Created the following chapterized files:\n")
            for file in chapterized_output:
                print(f"\t{file}\n")


