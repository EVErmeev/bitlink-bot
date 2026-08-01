import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from meeting_metadata import extract_date_from_filename, determine_meeting_date, compute_sha256, count_words


class TestDateExtraction:
    def test_date_from_filename_with_time(self):
        d, t = extract_date_from_filename(Path("2026_07_24T09_14_Название.txt"))
        assert d is not None
        assert d.year == 2026
        assert d.month == 7
        assert d.day == 24
        assert t is not None
        assert t.hour == 9
        assert t.minute == 14

    def test_date_from_filename_underscore(self):
        d, t = extract_date_from_filename(Path("2026_07_24_Название.md"))
        assert d is not None
        assert d.year == 2026
        assert d.month == 7
        assert d.day == 24

    def test_date_from_filename_dash(self):
        d, t = extract_date_from_filename(Path("2026-07-24_Название.md"))
        assert d is not None
        assert d.year == 2026

    def test_date_from_filename_dot(self):
        d, t = extract_date_from_filename(Path("2026.07.24_Название.txt"))
        assert d is not None
        assert d.year == 2026

    def test_no_date_in_filename(self):
        d, t = extract_date_from_filename(Path("meeting_notes.txt"))
        assert d is None
        assert t is None

    def test_no_current_date_fallback(self):
        d, t = determine_meeting_date(filepath=Path("no_date_here.txt"))
        assert d is None
        assert t is None

    def test_date_priority_filepath_over_metadata(self):
        d, t = determine_meeting_date(
            filepath=Path("2026_07_24_Название.md"),
            file_metadata={"date": "2026-07-25"},
        )
        assert d is not None
        assert d.day == 24  # filename has priority per pattern ordering

    def test_date_from_slash_format(self):
        d, t = extract_date_from_filename(Path("2026_07_24_09_14_Название.mp4"))
        assert d is not None
        assert t is not None
        assert d.year == 2026

    def test_time_not_set_to_midnight(self):
        d, t = extract_date_from_filename(Path("2026_07_24_Название.txt"))
        assert d is not None
        assert t is None  # no time in filename, should be None not 00:00


class TestWordCount:
    def test_simple_count(self):
        assert count_words("один два три") == 3

    def test_empty_text(self):
        assert count_words("") == 0

    def test_multiline(self):
        text = "строка один\nстрока два\nстрока три"
        assert count_words(text) == 6


class TestSHA256:
    def test_sha256_from_bytes(self):
        h1 = compute_sha256(Path(__file__))
        assert len(h1) == 64
        assert all(c in "0123456789abcdef" for c in h1)

    def test_different_files_different_hash(self, tmp_path):
        f1 = tmp_path / "a.txt"
        f2 = tmp_path / "b.txt"
        f1.write_text("hello")
        f2.write_text("world")
        assert compute_sha256(f1) != compute_sha256(f2)

    def test_same_content_same_hash(self, tmp_path):
        f1 = tmp_path / "x.txt"
        f2 = tmp_path / "y.txt"
        f1.write_text("same")
        f2.write_text("same")
        assert compute_sha256(f1) == compute_sha256(f2)


class TestDetermineMeetingDate:
    def test_user_date_priority(self):
        from datetime import date
        d, t = determine_meeting_date(user_date=date(2026, 8, 1), filepath=Path("2026_07_24.md"))
        assert d == date(2026, 8, 1)

    def test_bitlink_metadata(self):
        from datetime import date
        d, t = determine_meeting_date(bitlink_metadata={"date": "2026-06-15"})
        assert d == date(2026, 6, 15)

    def test_bitlink_date_object(self):
        from datetime import date
        d, t = determine_meeting_date(bitlink_metadata={"date": date(2026, 5, 10)})
        assert d == date(2026, 5, 10)

    def test_all_none(self):
        d, t = determine_meeting_date()
        assert d is None
        assert t is None