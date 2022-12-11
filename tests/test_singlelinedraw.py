"Test the SingleLineDraw class."
from harvest import SingleLineDraw

# pylint: disable=W0212

def test_init():
    "Test object initialization."
    draw = SingleLineDraw(1999)
    assert draw.year == 1999
    assert draw.currency == "EUR"

    draw = SingleLineDraw(1999, "ATS")
    assert draw.year == 1999
    assert draw.currency == "ATS"


def test_parse():
    "Test the parse method."
    line = (
        "Mi.;02.12.;3;13;17;35;38;42;Zz:;12;3JP;;35.465.934,00;7;à;732.187,00;"
        "478;à;16.083,00;21.288;à;481,00;335.705;à;38,00;3;13;38;17;42;35;Zz:;12;"
    )
    draw = SingleLineDraw(1999, "ATS")
    draw.parse(line)
    assert draw.data["date"] == "1999-12-02"
    assert draw.data["numbers"] == [3, 13, 17, 35, 38, 42]
    assert draw.data["ZZ"] == 12
    results = draw.data["results"]
    assert results["currency"] == "ATS"
    assert results["6"]["count"] == 0
    assert results["6"]["winnings"] == 0
    assert results["5ZZ"]["count"] == 7
    assert results["5ZZ"]["winnings"] == 732187.0
    assert results["5"]["count"] == 478
    assert results["5"]["winnings"] == 16083, 0
    assert results["4"]["count"] == 21288
    assert results["4"]["winnings"] == 481, 0
    assert results["3"]["count"] == 335705
    assert results["3"]["winnings"] == 38, 0


def test_clean_count():
    "Test the clean_count class method."
    assert SingleLineDraw.clean_count("3JP") == 0
    assert SingleLineDraw.clean_count("123.456") == 123456


def test_clean_number_str():
    "Test the clean_number_str class method."
    assert SingleLineDraw.clean_number_str("123") == "123"
    assert SingleLineDraw.clean_number_str("123.456") == "123456"
    assert SingleLineDraw.clean_number_str("123.456,17") == "123456.17"


def test_make_date():
    "Test the make_date method."
    draw = SingleLineDraw(2005)
    assert draw._make_date("17.6.") == "2005-06-17"
    assert draw._make_date("17.06.") == "2005-06-17"
    assert draw._make_date(" 17.06. ") == "2005-06-17"
