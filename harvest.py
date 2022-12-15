#!/usr/bin/env python3
"""Harvest Lotto stats from win2day.

run havest_stats.py -h for usage.
"""
import argparse
import csv
import json
import os
import re
from collections import UserDict
from typing import Dict, List

import requests

BASEURL = "https://www.win2day.at/media/NN_W2D_STAT_Lotto_"  # 2021.csv
OUTPUT_DIR = "data"


class SingleLineDraw(UserDict):
    "Helper class to collect draws before 2010."

    def __init__(self, year, currency="EUR"):
        super().__init__()
        self.year = year
        self.currency = currency

    def parse(self, line: str) -> None:
        "Parse the draw line from csv."
        line = self.fix_faulty_line(line)
        parts = line.split(";")
        self.data["date"] = self._make_date(parts[1])
        self.data["numbers"] = [int(i) for i in parts[2:8]]
        self.data["ZZ"] = int(parts[9])
        self._parse_results(parts[10:])

    @classmethod
    def fix_faulty_line(cls, line):
        "Some lines on the server have missing delimiters etc."
        line = re.sub(r"^Mi\. 14\.03\.;;", "Mi.;14.03.;", line)
        return line

    def _parse_results(self, fields: List[str]) -> None:
        """Parse win, num of wins and amount for each winning."""
        fields_of_interrest = [
            ("6", 0, 2),  # (label, idx_of_count, idx_of_winnings)
            ("5ZZ", 3, 5),
            ("5", 6, 8),
            ("4", 9, 11),
            ("3", 12, 14),
        ]
        results = {"currency": self.currency}
        for label, count_id, winnings_id in fields_of_interrest:
            if "JP" in fields[count_id]:
                count = 0
                winnings = 0
            else:
                count = self.clean_count(fields[count_id])
                winnings = float(self.clean_number_str(fields[winnings_id]))
            results[label] = {"count": count, "winnings": winnings}
        self.data["results"] = results

    @classmethod
    def clean_count(cls, val: str) -> int:
        "Convert the count string to an integer."
        if "JP" in val:
            clean_val = 0
        else:
            clean_val = int(cls.clean_number_str(val))
        return clean_val

    @classmethod
    def clean_number_str(cls, num: str) -> str:
        """Convert number strings to castable number strings.

        Numbers are contained in german notation like
        123.456,70  which is converted to 123456.70
        """
        num = num.replace(".", "")
        return num.replace(",", ".")

    def _make_date(self, date_str: str) -> str:
        "Convert date_str to yyyy-mm-dd"
        parts = date_str.split(".")
        month = int(parts[1])
        day = int(parts[0])
        return f"{self.year}-{month:02d}-{day:02d}"


class DoubleLineDraw(SingleLineDraw):
    "Helper class to collect draws after 2010."

    def parse(self, line: str) -> None:
        """Parse the first csv line of a draw.

        The nice guys from win2day split each draw into 2 lines in the csv file.
        So we have to handle this with different parsings.
        """
        parts = line.split(";")
        self.data["date"] = self._make_date(parts[0])
        self.data["numbers"] = [int(i) for i in parts[2:8]]
        self.data["ZZ"] = int(parts[9])
        self.data["results"] = {"currency": self.currency}
        self._parse_results(parts[10:])

    def parse_second_line(self, line: str) -> None:
        """Parser the second csv line of a draw.

        The nice guys from win2day split each draw into 2 lines in the csv file.
        So we have to handle this with different parsings.
        """
        parts = line.split(";")
        self._parse_results(parts[10:])

    def _parse_results(self, fields: List[str]) -> None:
        """Parse win, num of wins and amount for each win.

        Each win comes in a form like:

        6er;1;à;123456;5er + ZZ;2;à;12345 ...

        We put each win in a sub-dict like

        '6': {
            'count': 1,
            'winnings': 123456
        }
        """
        for i, field in enumerate(fields):
            match = re.match(r"(\d)er(.*)", field)
            if match:
                win_name = match.group(1) + match.group(2).replace(" + ", "")
                win_name = win_name.upper()
                self.data["results"][win_name] = {}
                if "JP" in fields[i + 1]:
                    self.data["results"][win_name]["count"] = 0
                    self.data["results"][win_name]["winnings"] = 0
                else:
                    self.data["results"][win_name]["count"] = int(
                        self.clean_number_str(fields[i + 1])
                    )
                    self.data["results"][win_name]["winnings"] = float(
                        self.clean_number_str(fields[i + 3])
                    )


def read_from_url(url):
    "Yield each line from url."
    resp = requests.get(url)
    resp.raise_for_status()
    for line in resp.text.split("\n"):
        if (
            line.strip()
            and not re.match(r"[;\s]{8}", line)
            and not re.match(r"^\s*Datum", line)
            and not line.startswith(";;Zahlen")
            and not line.startswith("(Einführung von")
            and not "verschoben" in line
            and not "e n t f a l l e n" in line
        ):
            yield line


def harvest_modern(year: int) -> List[Dict]:
    "Beginning from February 2017 we have yearly csv files."
    results = []
    url = BASEURL + str(year) + ".csv"
    for i, line in enumerate(read_from_url(url)):
        if i % 2 == 0:
            line_data = DoubleLineDraw(year)
            line_data.parse(line)
        else:
            line_data.parse_second_line(line)
            results.append(line_data.data)
    return results


def harvest_2010_to_2017(year):
    """Return data for a single year between 2010 and 2017.

    Data from 2010 until February of 2017 is in one csv file
    and has an additional field.
    """
    results = []
    url = "https://www.win2day.at/media/lotto-ziehungen-2010-2017.csv"
    csv_year = 0
    line_counter = 0
    for line in read_from_url(url):
        match = re.match(r"(\d{4}) Lotto - Beträge in EUR", line)
        if match:
            csv_year = int(match.group(1))
        elif csv_year == year:
            line_counter += 1
            if line_counter % 2 > 0:
                line_data = DoubleLineDraw(year)
                # 2010-2017 has the weekday as first element.
                # If we strip it, we can user normal Draw class
                line_data.parse(line.split(";", 1)[1])
            else:
                line_data.parse_second_line(line.split(";", 1)[1])
                results.append(line_data.data)
    return results


def harvest_pre_2011(year: int) -> None:
    """Harvest a single year before 2011.

    Results before Sept 5 2010 have a different format:
        * onley on line
        * not 4+zz, 3+zz
    """
    url = "https://www.win2day.at/media/lotto-ziehungen-1986-2010.csv"
    results = []

    csv_year = 0
    currency = "EUR"
    for line in read_from_url(url):
        match = re.match(r"(\d{4}) Lotto - Beträge in (\w+)", line)
        if match:
            csv_year = int(match.group(1))
            currency = match.group(2)
        elif csv_year == year:
            line_data = SingleLineDraw(year, currency)
            line_data.parse(line)
            results.append(line_data.data)
    return results


def fetch_data(year):
    """Harvest data for a single year.

    This function knows how to deal with changing format.
    """
    data = []
    if year > 2017:
        data = harvest_modern(year)
    elif year == 2017:  # partly old format
        data = harvest_2010_to_2017(year)
        data += harvest_modern(year)
    elif year > 2010:
        data = harvest_2010_to_2017(year)
    elif year == 2010:  # partly very old format
        data = harvest_pre_2011(year)
        data += harvest_2010_to_2017(year)
    else:
        data = harvest_pre_2011(year)
    return data


def write_json(data: List, data_dir: str, year: int, indent: bool = False) -> None:
    "Write data of a single year into a json file in data_dir."
    os.makedirs(os.path.join(data_dir, "json"), exist_ok=True)
    filename = os.path.join(data_dir, "json", f"{year}.json")
    with open(filename, "w", encoding="utf-8") as jsonfile:
        if indent:
            json.dump(data, jsonfile, ensure_ascii=False, indent=2)
        else:
            json.dump(data, jsonfile, ensure_ascii=False)


def write_csv(data: List, data_dir: str, year: int) -> None:
    "Write data_ of a single year into a csv file."
    rows = []
    rows.append(
        [
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
    )
    for draw in data:
        row = []
        row.append(draw["date"])
        row.append(",".join([str(n) for n in draw["numbers"]]))
        row.append(draw["ZZ"])
        row.append(draw["results"]["currency"])
        row.append(draw["results"]["6"]["count"])
        row.append(draw["results"]["6"]["winnings"])
        if "5ZZ" in draw["results"]:
            row.append(draw["results"]["5ZZ"]["count"])
            row.append(draw["results"]["5ZZ"]["winnings"])
        else:
            row.append("")
            row.append("")
        row.append(draw["results"]["5"]["count"])
        row.append(draw["results"]["5"]["winnings"])
        if "4ZZ" in draw["results"]:
            row.append(draw["results"]["4ZZ"]["count"])
            row.append(draw["results"]["4ZZ"]["winnings"])
        else:
            row.append("")
            row.append("")
        row.append(draw["results"]["4"]["count"])
        row.append(draw["results"]["4"]["winnings"])
        if "3ZZ" in draw["results"]:
            row.append(draw["results"]["3ZZ"]["count"])
            row.append(draw["results"]["3ZZ"]["winnings"])
        else:
            row.append("")
            row.append("")
        row.append(draw["results"]["3"]["count"])
        row.append(draw["results"]["3"]["winnings"])
        rows.append(row)
    os.makedirs(os.path.join(data_dir, "csv"), exist_ok=True)
    filename = os.path.join(data_dir, "csv", f"{year}.csv")
    with open(filename, "w", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile, delimiter=";")
        writer.writerows(rows)


def parse_args():
    "Parse command line arguments."

    class YearAction(argparse.Action):
        "An action to convert year intervals to a list of ints."

        def __call__(self, parser, namespace, values, option_string=None):
            if len(values) == 1 and "-" in values[0]:  # eg. 2010-2015
                first, last = values[0].split("-")
                values = list(range(int(first), int(last) + 1))
            else:
                values = [int(year) for year in values]
            setattr(namespace, self.dest, values)

    parser = argparse.ArgumentParser(
        description="Fetch lotto results from the win2day archive."
    )
    parser.add_argument(
        "years",
        action=YearAction,
        metavar="YEAR",
        nargs="+",
        help=(
            "Year(s) to fetch. Can be a single year, multiple years or an interval "
            "like '2010-2012', which harvests 2010, 2011 and 2012."
        ),
    )
    parser.add_argument(
        "-o", "--output-dir", default=OUTPUT_DIR, help="output directory"
    )
    parser.add_argument(
        "-i",
        "--indent",
        action="store_true",
        default=False,
        help="Set this flag to create 'pretty' json.",
    )
    parser.add_argument(
        "-f",
        "--format",
        choices=["csv", "json", "both"],
        default="both",
        help=(
            "Set the output format. Allowed values are 'json', 'csv' or 'both'. "
            "If not set or set to 'both', csv and json output will be produced."
        ),
    )
    args_ = parser.parse_args()
    if min(args_.years) < 1986:
        raise ValueError("No data before 1986.")
    return args_


def main(years: List[int], output_dir: str, format: str, indent: bool = False) -> None:
    "Run the script."
    for year in years:
        data = fetch_data(year)
        if format in ("json", "both"):
            write_json(data, output_dir, year, indent)
        if format in ("csv", "both"):
            write_csv(data, output_dir, year)


if __name__ == "__main__":
    args = parse_args()
    main(args.years, args.output_dir, args.format, args.indent)
