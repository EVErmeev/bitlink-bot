"""Negative + regression tests for safe meeting-date parsing (TASK §8, §13).

Covers: invalid month/day/hour/minute, impossible calendar dates, time-only and
hash filenames, fallback to file_metadata, absence of exceptions for arbitrary
names, and ISO-with-seconds handling. Also verifies the "never raises" contract
over a large set of arbitrary names.
"""
import sys
from datetime import date, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from meeting_metadata import (
    determine_meeting_date,
    extract_date_from_filename,
)

_INVALID = [
    "15_15_26_10_30_00_video.mp4",        # invalid month (DD_MM_YY)
    "31_15_26_10_30_00_video.mp4",        # invalid month
    "2026_15_31_10_30_00_video.mp4",      # invalid month (YYYY_MM_DD)
    "2026_02_30_10_30_00_video.mp4",      # Feb 30 — invalid calendar date
    "2026_08_05_25_30_00_video.mp4",      # invalid hour 25
    "2026_08_05_15_70_00_video.mp4",      # invalid minute 70
    "2026_08_05_15_30_99_video.mp4",      # invalid second 99
    "local-872b2e3cdd76beb0_transcript.txt",
    "meeting_15_30_45_recording.mp4",     # time-only-looking but no date
    "recording_01_30_15_22_44_99.mp4",    # ambiguous time-like
    "2026_13_05_10_00_00.mp4",            # month 13
    "2026_00_05_10_00_00.mp4",            # month 0
    "2026_08_00_10_00_00.mp4",            # day 0
    "2026_08_32_10_00_00.mp4",            # day 32
    "2026_08_05_24_00_00.mp4",            # hour 24
    "2026_08_05_10_60_00.mp4",            # minute 60
]


class TestInvalidFilenamesNeverRaise:
    @pytest.mark.parametrize("name", _INVALID)
    def test_invalid_filename_never_raises(self, name):
        d, t = extract_date_from_filename(Path(name))
        assert isinstance(d, (date, type(None)))
        assert d is None  # these names carry no valid, unambiguous date

    def test_invalid_month_does_not_raise(self):
        assert extract_date_from_filename(Path("15_15_26_10_30_00_video.mp4")) == (None, None)

    def test_invalid_day_does_not_raise(self):
        assert extract_date_from_filename(Path("2026_02_30_10_30_00_video.mp4")) == (None, None)

    def test_invalid_hour_does_not_raise(self):
        assert extract_date_from_filename(Path("2026_08_05_25_30_00_video.mp4")) == (None, None)

    def test_invalid_minute_does_not_raise(self):
        assert extract_date_from_filename(Path("2026_08_05_15_70_00_video.mp4")) == (None, None)

    def test_invalid_calendar_date_does_not_raise(self):
        assert extract_date_from_filename(Path("2026_02_30_10_30_00_video.mp4")) == (None, None)

    def test_time_only_filename_is_not_date(self):
        assert extract_date_from_filename(Path("meeting_15_30_45_recording.mp4")) == (None, None)

    def test_hash_filename_is_not_date(self):
        assert extract_date_from_filename(Path("local-872b2e3cdd76beb0_transcript.txt")) == (None, None)

    def test_determine_meeting_date_never_leaks_value_error(self):
        # Regression: the old parser raised ValueError('month must be in 1..12')
        d, t = determine_meeting_date(filepath=Path("31_15_26_10_30_00_video.mp4"))
        assert d is None and t is None


class TestFallback:
    def test_invalid_filename_falls_back_to_file_metadata(self):
        d, t = determine_meeting_date(
            filepath=Path("31_15_26_10_30_00_video.mp4"),
            file_metadata={"date": "2026-08-05"},
        )
        assert d == date(2026, 8, 5)

    def test_valid_filename_has_priority_over_metadata(self):
        d, t = determine_meeting_date(
            filepath=Path("2026_07_24_09_14_30_video.mp4"),
            file_metadata={"date": "2026-08-05"},
        )
        assert d == date(2026, 7, 24)
        assert t == time(9, 14)


class TestArbitraryNamesNeverRaise:
    # A broad, mechanical set of names; the contract is "never raises".
    @pytest.mark.parametrize("name", [
        "abc",
        "meeting",
        "просто имя без даты",
        "123",
        "12",
        "2026",
        "26",
        "meeting_123",
        "video_2026",
        "rec_2026_07",
        "a_b_c_d_e_f_g",
        "1_2_3_4_5_6_7",
        "00_00_00_00_00_00",
        "99_99_99_99_99_99",
        "2026-07",
        "2026.07",
        "07-2026",
        "24_07_2026",
        "24.07.2026",
        "24_07_26",
        "07_26_2026",
        "2026_13",
        "foo_2026_02_30_bar",
        "31_04_2026",            # Apr 31 invalid
        "2026_04_31_10_00_00",   # invalid calendar
        "___",
        "_",
        ".-.",
        "2026__07__24",
        "20",
        "20.20.2020.20.20.20",
        "02_29_2025",            # 2025 not a leap year
        "2024_02_29_10_00_00",   # leap year valid
        "x_15_99_99_99_99_99",
        "meeting_2026_08_05_25_99_00_x",
        "transcript_local_872b2e3c",
        "output_newton_2026_08",
        "2026_08_05T",
        "T_2026_08_05",
        "2026_08_05_",
        "_2026_08_05",
        "2026",
        "2026_",
        "26_07",
        "20260724",
        "20260724091430",
        "07032026",
        "15_07_26",
        "record_26_07_2026_mp4",
        "Екатеринбург_2026_07_24_09_14_30",
        "УралДронЗавод_2026_07_24_09_14_30_видео",
        "запись_31_07_26_14_06_05",
        "protocol_31.07.2026",
        "31.07.2026_protocol",
    ])
    def test_never_raises(self, name):
        d, t = extract_date_from_filename(Path(name))
        assert d is None or d.year >= 1900
        assert t is None or (d is not None)
