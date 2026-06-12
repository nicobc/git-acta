import pytest

from gitclerk.github.milestone import parse_epic_body


@pytest.mark.parametrize(
    "text, expected_description, expected_notes",
    [
        ("", "", []),
        ("  ", "", []),
        ("A description.", "A description.", []),
        (
            "A description.\n\nNotes:\n- note one\n- note two",
            "A description.",
            ["note one", "note two"],
        ),
        (
            "Desc.\n\nNotes:\n- first\n- second\nignored line",
            "Desc.",
            ["first", "second"],
        ),
        (
            "Multi-line desc.\nSecond line.\n\nNotes:\n- a note",
            "Multi-line desc.\nSecond line.",
            ["a note"],
        ),
    ],
    ids=[
        "empty",
        "whitespace_only",
        "description_only",
        "description_and_notes",
        "notes_ignores_non_list_lines",
        "multiline_description",
    ],
)
def test_parse_epic_body(text: str, expected_description: str, expected_notes: list[str]) -> None:
    description, notes = parse_epic_body(text)
    assert description == expected_description
    assert notes == expected_notes
