# Harvest6aus45

Harvest6aus45 is a small script to collect data from the Austrian lotto site.
This site provides access to all draws starting in 1986, but it uses 3 different
csv formats, some of them spread over 2 lines and also combines multiple 
years into one file, sometimes switching format during the year.

When I needed a simple data example for my lecture, I decided to write this script,
which

* collects data on a yearly basis
* unifies the different formats
* knows how to deal with format switches during a single year
* can create json or csv data

## Installation

There is no real installation involved. 
Just clone the repository, install the requirements and run the script.

Needed steps:

1. Clone the project:
   
   ```
   git clone https://github.com/gvasold/harvest6aus45
   ```

2. Install the required libraries (for usage, this is only the requests module)
   
   ```
   pip install -r requirements.txt
   ```

   If you want to run the tests, also install requirements_dev.txt:

   ```
   pip install -r requirements_dev.txt
   ```


## Usage

Run 

```
python harvest.py --help
``` 

to get information on usage.

Normally you would use a command like

```
python harvest.py 2021
```

which will generate data for the year 2021.

Alternatively you can set multiple years:

```
python harvest.py 2021 2022
```

or an interval:

```
python harvest.py 1986-2022 
```

This will create a `data\json` and `data\csv` directory and create a json and a csv file for each year.

You can change the location of the output directory via ``--output-dir``.

If you'd prefer not to create both formats use ``--format json`` or ``--format csv``.

Here is a full example:

```
python harvest.py --output-dir /tmp/6aus45 --format csv 1986-2022
```

