# Experiment and Utility Scripts

This directory contains scripts for running the LogRoca experiments and preparing log files for use with the replication package.

## Scripts

| Script | Purpose |
| --- | --- |
| `exp_diff_log_chunk_size.py` | Runs the experiment comparing log chunk sizes. |
| `exp_diff_log_sumarisation.py` | Runs the experiment comparing log summarisation methods. |
| `xml2json.py` | Converts XML log files to JSON. |
| `remove-at-char.py` | Removes `@` characters from JSON keys, for use when preparing files produced by `xml2json.py`. |

## Requirements

- LogRoca v0.5.0. See the [v0.5.0 release](https://codeberg.org/rahmanuh/LogRoca/src/tag/v0.5.0) for the source and installation instructions.
- Python dependencies: install the packages listed in `requirements.txt` (`pandas`, `openpyxl`, `python-dotenv`, and `xmltodict`).
- Access to the experiment dataset used by the experiment scripts. Dataset access may be restricted; contact the authors if you require it.

## Configure the experiment dataset

The two experiment scripts read `LOGROCA_ALSTOM_DATASET_PATH` from a `.env` file. Create a `.env` file in this directory with the dataset path, for example:

```dotenv
LOGROCA_ALSTOM_DATASET_PATH=/path/to/authorised/dataset
```

Alternatively, set the variable in your shell environment. Do not commit private dataset paths or credentials to version control.

Install the Python packages from this directory with:

```bash
python -m pip install -r requirements.txt
```

## Run the experiment scripts

After installing the requirements and configuring the dataset path, run a script from this directory:

```bash
python exp_diff_log_chunk_size.py
python exp_diff_log_sumarisation.py
```

Run the utilities with Python as needed:

```bash
python xml2json.py path/to/log.xml
python remove-at-char.py path/to/log.json
```
