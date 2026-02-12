"""
Tests for PsychSheetParser service.
"""

from swim_ai_reflex.backend.services.psych_sheet_parser import PsychSheetParser


def test_detect_format_csv():
    parser = PsychSheetParser()
    assert parser._detect_format("", "test.csv") == "hytek_csv"
    assert parser._detect_format("Event #,Event Name", "test.txt") == "hytek_csv"


def test_detect_format_text():
    parser = PsychSheetParser()
    assert (
        parser._detect_format("Event 1 Boys 200 Medley Relay", "test.txt")
        == "text_regex"
    )


def test_parse_hytek_csv():
    parser = PsychSheetParser()
    content = """Event #,Event Name,Athlete Name,Team Code,Seed Time,Grade
1,Boys 200 Yard Medley Relay,,SST,1:45.00,
2,Boys 200 Yard Freestyle,"Smith, John",SST,1:50.50,12
2,Boys 200 Yard Freestyle,"Doe, Jane",TCS,1:55.20,11"""

    sheet = parser.parse(content, "test.csv")
    assert (
        len(sheet.entries) == 2
    )  # Relay is skipped by name parser logic or processed differently?
    # Wait, my logic checks for "swimmer" column. empty swimmer name for relay?
    # Let's check logic: if swimmer column empty -> "Relay"

    # In my implementation: swimmer_raw = row[...] if ... else "Relay"
    # But CSV reader returns empty string for empty field.
    # Ah, implementation: swimmer_raw = row[col] if col exists.
    # If standard hytek has blank name for relay, normalize_swimmer_name("") -> ""

    # Let's verify specific entries
    e1 = sheet.entries[0]
    assert e1.swimmer_name == "John Smith"
    assert e1.event == "Boys 200 Free"
    assert e1.team == "Seton"
    assert e1.seed_time == 110.5
    assert e1.grade == 12


def test_parse_text_regex():
    parser = PsychSheetParser()
    content = """
    Event 3  Boys 50 Yard Freestyle
      1  Smith, John        12  SST     22.50
      2  Doe, Bob           10  TCS     23.10

    Event 4  Girls 100 Yard Butterfly
      1  Jones, Mary        11  OAK     1:05.50
    """

    sheet = parser.parse(content)
    assert len(sheet.entries) == 3

    e1 = sheet.entries[0]
    assert e1.swimmer_name == "John Smith"
    assert e1.event == "Boys 50 Free"
    assert e1.seed_time == 22.50
    assert e1.team == "Seton"

    e3 = sheet.entries[2]
    assert e3.swimmer_name == "Mary Jones"
    assert e3.event == "Girls 100 Fly"
    assert e3.seed_time == 65.50
