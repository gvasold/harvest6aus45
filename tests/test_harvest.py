"Test the module function of harvest."
import csv
import json
import os
import tempfile
from unittest.mock import patch

import pytest
import responses

import harvest

#pylint: disable=C0301
@pytest.fixture(name='tmpdir')
def fixture_tmpdir():
    "Yield a temporary directory."
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture(name='mocksmalldata')
def fixture_mocksmalldata():
    "Return a data dict for old data (no 4ZZ etc)"
    data = {
        "date": "2017-08-15",
        "numbers": [1, 2, 3, 4, 5, 6],
        "ZZ": 7,
        "results": {
            "currency": "EUR",
            "6": {"count": 1, "winnings": 1234567},
            "5ZZ": {"count": 3, "winnings": 243565},
            "5": {"count": 45, "winnings": 123456},
            "4": {"count": 100, "winnings": 123},
            "3": {"count": 1000, "winnings": 12},
        },
    }
    yield data


@pytest.fixture(name='mockfulldata')
def fixture_mockfulldata(mocksmalldata):
    "Return a data dict for new data (with 4ZZ etc)."
    mocksmalldata["results"]["4ZZ"] = {"count": 765, "winnings": 155}
    mocksmalldata["results"]["3ZZ"] = {"count": 45678, "winnings": 1.5}
    return mocksmalldata


@pytest.fixture(name='col_names')
def fixture_col_names():
    "Return lost of column names as used in csv output."
    return [
        "date",
        "numbers",
        "zz",
        "currency",
        "count_6",
        "winnings_6",
        "count_5zz",
        "winnings_5zz",
        "count_5",
        "winnings_5",
        "count_4zz",
        "winnings_4zz",
        "count_4",
        "winnings_4",
        "count_3zz",
        "winnings_3zz",
        "count_3",
        "winnings_3",
    ]


@responses.activate
def test_read_from_url():
    "read_from_url should yield the response line by line."
    responses.add(responses.GET, "http://example.com/foo/bar", body="foo\nbar\nfoobar")
    lines = list(harvest.read_from_url("http://example.com/foo/bar"))
    assert lines[0] == "foo"
    assert lines[1] == "bar"
    assert lines[2] == "foobar"


@responses.activate
def test_read_from_url_empty_line():
    "read_from_url should not yield empty lines."
    responses.add(
        responses.GET, "http://example.com/foo/bar", body="foo\n\nbar\n   \nfoobar"
    )
    lines = list(harvest.read_from_url("http://example.com/foo/bar"))
    assert lines[0] == "foo"
    assert lines[1] == "bar"
    assert lines[2] == "foobar"


@responses.activate
def test_read_from_url_empty_fields():
    "read_from_url should not yield lines consiting of delimiters only."
    responses.add(
        responses.GET,
        "http://example.com/foo/bar",
        body="foo\n;;;;;;;;;;;\nbar\n;; ;;; ;;;;;;\nfoobar",
    )
    lines = list(harvest.read_from_url("http://example.com/foo/bar"))
    assert lines[0] == "foo"
    assert lines[1] == "bar"
    assert lines[2] == "foobar"


@responses.activate
def test_read_from_url_leading_datum():
    "read_from_url should not yield lines starting with 'Datum."
    responses.add(
        responses.GET,
        "http://example.com/foo/bar",
        body="foo\nDatum;\nbar\n  Datum\nfoobar",
    )
    lines = list(harvest.read_from_url("http://example.com/foo/bar"))
    assert lines[0] == "foo"
    assert lines[1] == "bar"
    assert lines[2] == "foobar"


@responses.activate
def test_read_from_url_leading_zahlen():
    "read_from_url should not yield lines starting with ';;Zahlen."
    responses.add(
        responses.GET, "http://example.com/foo/bar", body="foo\n;;Zahlen\nbar\nfoobar"
    )
    lines = list(harvest.read_from_url("http://example.com/foo/bar"))
    assert lines[0] == "foo"
    assert lines[1] == "bar"
    assert lines[2] == "foobar"


@responses.activate
def test_read_from_url_einfuehrung():
    "read_from_url should not yield lines starting with '(Einführung von."
    responses.add(
        responses.GET,
        "http://example.com/foo/bar",
        body="foo\n(Einführung von\nbar\nfoobar",
    )
    lines = list(harvest.read_from_url("http://example.com/foo/bar"))
    assert lines[0] == "foo"
    assert lines[1] == "bar"
    assert lines[2] == "foobar"


@responses.activate
def test_read_from_url_verschoben():
    "read_from_url should not yield lines containing 'verschoben."
    responses.add(
        responses.GET,
        "http://example.com/foo/bar",
        body="foo\nabc verschoben def\nbar\nfoobar",
    )
    lines = list(harvest.read_from_url("http://example.com/foo/bar"))
    assert lines[0] == "foo"
    assert lines[1] == "bar"
    assert lines[2] == "foobar"


@responses.activate
def test_read_from_url_entfallen():
    "read_from_url should not yield lines contaiing 'e n t f a l l e n."
    responses.add(
        responses.GET,
        "http://example.com/foo/bar",
        body="foo\nabc e n t f a l l e n def\nbar\nfoobar",
    )
    lines = list(harvest.read_from_url("http://example.com/foo/bar"))
    assert lines[0] == "foo"
    assert lines[1] == "bar"
    assert lines[2] == "foobar"


def test_harvest_modern():
    "Test the harvest_modern function."
    # this is the value the mocked read_from_url returns
    mock_lines = [
        "21.11.;aufsteigend;1;13;24;30;36;38;Zz;19;6er;2;à;1.864.444,50;5er + ZZ;2;à;108.025,80;5er;160;à;1.473,00;4er + ZZ;477;à;172,90;;;;;;",
        ";gezogen;38;24;13;36;30;1;Zz;19;4er;8.099;à;48,00;3er + ZZ;11.676;à;16,10;3er;135.104;à;5,10;ZZ;472.879;à;1,10;;;;;;",
    ]
    with patch("harvest.read_from_url", return_value=mock_lines):
        results = harvest.harvest_modern(2010)
        assert len(results) == 1
        assert results[0]["date"] == "2010-11-21"


def test_harvest_2010_to_2017():
    """Test the harvest_2010_to_2017 function.

    It has 2 differences to modern: an extra column and multiple years in one response.
    """
    # this is the value the mocked read_from_url returns. We mock 2 years.
    mock_lines = [
        "2010 Lotto - Beträge in EUR;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;",
        "So;21.10.;aufsteigend;1;13;24;30;36;38;Zz;19;6er;2;à;1.864.444,50;5er + ZZ;2;à;108.025,80;5er;160;à;1.473,00;4er + ZZ;477;à;172,90;;;;;;",
        ";;gezogen;38;24;13;36;30;1;Zz;19;4er;8.099;à;48,00;3er + ZZ;11.676;à;16,10;3er;135.104;à;5,10;ZZ;472.879;à;1,10;;;;;;",
        "2011 Lotto - Beträge in EUR;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;",
        "So;21.11.;aufsteigend;1;13;24;30;36;38;Zz;19;6er;2;à;1.864.444,50;5er + ZZ;2;à;108.025,80;5er;160;à;1.473,00;4er + ZZ;477;à;172,90;;;;;;",
        ";;gezogen;38;24;13;36;30;1;Zz;19;4er;8.099;à;48,00;3er + ZZ;11.676;à;16,10;3er;135.104;à;5,10;ZZ;472.879;à;1,10;;;;;;",
    ]
    with patch("harvest.read_from_url", return_value=mock_lines):
        results = harvest.harvest_2010_to_2017(2011)
        assert len(results) == 1
        assert results[0]["date"] == "2011-11-21"


def test_harvest_pre_2011():
    "Test the harvest_pre_2011 function."
    # this is the value the mocked read_from_url returns
    mock_lines = [
        "1999 Lotto - Beträge in ATS;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;",
        "Mi.;01.09.;3;6;10;13;21;43;Zz:;7;4;à;5.442.999,00;15;à;271.997,00;415;à;14.746,00;19.480;à;418,00;296.846;à;34,00;10;43;21;13;3;6;Zz:;7;",
    ]
    with patch("harvest.read_from_url", return_value=mock_lines):
        results = harvest.harvest_pre_2011(1999)
        assert len(results) == 1
        assert results[0]["date"] == "1999-09-01"


def test_fetch_data():
    """Test the fetch_data function.

    As this function calls different methods depending on the year param,
    it's enough to make sure, that the correct funtions are called.
    So we do not mock the return values of these called functions, but
    the name of the called function for testing.
    """
    with patch("harvest.harvest_modern", return_value=["hm_modern"]):
        with patch("harvest.harvest_2010_to_2017", return_value=["hm_2010_17"]):
            with patch("harvest.harvest_pre_2011", return_value=["hm_pre_2011"]):
                assert harvest.fetch_data(2020) == ["hm_modern"]
                assert harvest.fetch_data(1999) == ["hm_pre_2011"]
                assert harvest.fetch_data(2016) == ["hm_2010_17"]

    with patch("harvest.harvest_modern", return_value=["hm_modern"]):
        with patch("harvest.harvest_2010_to_2017", return_value=["hm_2010_17"]):
            with patch("harvest.harvest_pre_2011", return_value=["hm_pre_2011"]):
                assert harvest.fetch_data(2010) == ["hm_pre_2011", "hm_2010_17"]
                assert harvest.fetch_data(2017) == ["hm_2010_17", "hm_modern"]


def test_write_json(mockfulldata, tmpdir):
    "Write a full dataset to json and read it in again."
    harvest.write_json([mockfulldata], tmpdir, 2017)
    expected_file = os.path.join(tmpdir, "json", "2017.json")
    assert os.path.exists(expected_file)
    with open(expected_file, encoding="utf-8") as jsonfile:
        jdata = json.load(jsonfile)
    assert jdata[0] == mockfulldata


def test_write_json_small_data(mocksmalldata, tmpdir):
    "Data before 2011 had less winning numbers than later."
    harvest.write_json([mocksmalldata], tmpdir, 2017)
    expected_file = os.path.join(tmpdir, "json", "2017.json")
    assert os.path.exists(expected_file)
    with open(expected_file, encoding="utf-8") as jsonfile:
        jdata = json.load(jsonfile)
    assert jdata[0] == mocksmalldata


def test_write_csv(tmpdir, mockfulldata, col_names):
    "Test writing to csv with full data like provided by modern stats."
    expected_file = os.path.join(tmpdir, "csv", "2017.csv")
    expected_values = [
        "2017-08-15",
        "1,2,3,4,5,6",
        "7",
        "EUR",
        "1",
        "1234567",
        "3",
        "243565",
        "45",
        "123456",
        "765",
        "155",
        "100",
        "123",
        "45678",
        "1.5",
        "1000",
        "12",
    ]

    harvest.write_csv([mockfulldata], tmpdir, 2017)
    assert os.path.exists(expected_file)
    with open(expected_file, encoding="utf-8") as csvfile:
        reader = csv.reader(csvfile, delimiter=";")
        rows = list(reader)
        assert rows[0] == col_names
        assert rows[1] == expected_values


def test_write_csv_small_data(tmpdir, mocksmalldata, col_names):
    "Results before 2011 do not have 4ZZ and 3ZZ"
    expected_file = os.path.join(tmpdir, "csv", "2017.csv")
    expected_values = [
        "2017-08-15",
        "1,2,3,4,5,6",
        "7",
        "EUR",
        "1",
        "1234567",
        "3",
        "243565",
        "45",
        "123456",
        "",
        "",
        "100",
        "123",
        "",
        "",
        "1000",
        "12",
    ]

    harvest.write_csv([mocksmalldata], tmpdir, 2017)
    assert os.path.exists(expected_file)
    with open(expected_file, encoding="utf-8") as csvfile:
        reader = csv.reader(csvfile, delimiter=";")
        rows = list(reader)
        assert rows[0] == col_names
        assert rows[1] == expected_values
