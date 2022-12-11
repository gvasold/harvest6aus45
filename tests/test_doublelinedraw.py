"Test for the DoubleLineDraw class."

from harvest import DoubleLineDraw


def test_init():
    "Test object initialization."
    draw = DoubleLineDraw(2012)
    assert draw.year == 2012
    assert draw.currency == "EUR"

    draw = DoubleLineDraw(1999, "ATS")
    assert draw.year == 1999
    assert draw.currency == "ATS"


def test_parse():
    """Test the parse methods.
    
    Testing these methods separately makes no sense."
    """
    draw = DoubleLineDraw(2012)
    line1 = (
        "19.9.;aufsteigend;6;17;20;26;34;36;Zz;16;6er;DJP;;2.173.795,00;"
        "5er + ZZ;7;à;42.699,50;5er;154;à;1.308,20;4er + ZZ;555;à;127,00;;;;;;"
    )
    line2 = (
        ";;gezogen;34;17;6;26;20;36;Zz;16;4er;8.005;à;41,50;3er + ZZ;"
        "11.879;à;13,50;3er;127.067;à;4,60;ZZ;382.085;à;1,10;;;;;;"
    )
    draw.parse(line1)
    draw.parse_second_line(line2)

    assert draw.data["date"] == "2012-09-19"
    assert draw.data["numbers"] == [6, 17, 20, 26, 34, 36]
    assert draw.data["ZZ"] == 16

    results = draw.data["results"]
    assert results["currency"] == "EUR"
    assert results["6"]["count"] == 0
    assert results["6"]["winnings"] == 0
    assert results["5ZZ"]["count"] == 7
    assert results["5ZZ"]["winnings"] == 42699.50
    assert results["5"]["count"] == 154
    assert results["5"]["winnings"] == 1308.20
    assert results["4ZZ"]["count"] == 555
    assert results["4ZZ"]["winnings"] == 127.0
    assert results["4"]["count"] == 8005
    assert results["4"]["winnings"] == 41.50
    assert results["3ZZ"]["count"] == 11879
    assert results["3ZZ"]["winnings"] == 13.50
    assert results["3"]["count"] == 127067
    assert results["3"]["winnings"] == 4.60
