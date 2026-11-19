# Drillhole Integrated Database Builder

This tool takes raw geophysical and geochemical lab measurements from drillhole core samples, matches them to the master **sample report** for each drillhole, and writes everything into one Excel workbook: `<drillhole>_integrated_database.xlsx`.

Supported properties:

| Key      | Property                          | Instrument / source                  |
|----------|-----------------------------------|--------------------------------------|
| `den`    | Density                           | Read directly from the sample report |
| `ip_res` | Induced polarisation / resistance | KT-20 (`kt20_0385`) IP records       |
| `cond`   | Electrical conductivity           | KT-20 (`kt20_0385`) kappa/sigma      |
| `sus`    | Magnetic susceptibility           | KT-20 (`kt20_0385`) kappa/sigma      |
| `v_p`    | P-wave velocity                   | Pundit (`Punditlink Data.csv`)       |
| `v_s`    | S-wave velocity                   | Pundit (`Punditlink Data.csv`)       |
| `gamma`  | Gamma spectrometry (K, U, Th)     | Pre-computed `gamma_concentrations*.csv`, copied as-is |
| `xrf`    | Portable XRF geochemistry         | pXRF CSV exports                     |

---

## Table of contents

1. [Repository structure](#1-repository-structure)
2. [Requirements](#2-requirements)
3. [Expected data layout](#3-expected-data-layout)
4. [The sample report workbook](#4-the-sample-report-workbook)
5. [Running the code](#5-running-the-code)
6. [Output workbook](#6-output-workbook)
7. [Processing logic per property](#7-processing-logic-per-property)
8. [API reference](#8-api-reference)
9. [Missing-data conventions](#9-missing-data-conventions)
10. [Troubleshooting](#10-troubleshooting)
11. [Known limitations and notes](#11-known-limitations-and-notes)

---

## 1. Repository structure

```
database_code/
├── database_creation_widget.ipynb   # Google Colab notebook with an interactive UI (main entry point)
├── README.md
└── codes/
    ├── __init__.py                  # makes `codes` an importable package
    ├── data_processing.py           # reads and processes the raw data (class `dataprocess`)
    └── new_workbook.py              # builds and writes the Excel database (class `database`)
```

- **`data_processing.py`** reads the raw instrument files and the sample report, then returns clean pandas DataFrames, one per property.
- **`new_workbook.py`** subclasses `dataprocess`. It creates the output workbook, seeds each sheet from the sample report, and writes the processed values and calibration data into it.
- **`database_creation_widget.ipynb`** is a point-and-click front end for Google Colab. You pick a site, a drillhole and the properties, then click **Run**.

---

## 2. Requirements

- Python 3.8 or newer
- Python packages:

| Package      | Used for                                         |
|--------------|--------------------------------------------------|
| `pandas`     | Reading CSV/Excel files, all tabular processing  |
| `numpy`      | Numeric work and outlier masking                 |
| `openpyxl`   | Creating and writing `.xlsx` workbooks           |
| `chardet`    | Detecting the encoding of Pundit CSV exports     |
| `ipywidgets` | Notebook UI (only needed for the notebook)       |

Install them with:

```bash
pip install pandas numpy openpyxl chardet ipywidgets
```

Google Colab already includes everything except possibly `chardet`. If the import fails, run `!pip install chardet` in a cell.

---

## 3. Expected data layout

All paths inside the code are **relative to the current working directory**. That directory must be the *site* folder that contains the drillhole folders. The notebook changes into it for you.

```
<BASE_DIR>/                                   e.g. /content/drive/Shareddrives/CAGEO/Database/
└── <Site>/                                   e.g. Gortdrum      <-- working directory
    └── <Drillhole>/                          e.g. G-2529-4
        ├── <Drillhole>_sample_report.xlsx    # master workbook (required)
        ├── <Drillhole>_integrated_database.xlsx   # OUTPUT (created by the tool)
        │
        ├── cond_sus/                         # used by both `cond` and `sus`
        │   └── DD-MM-YY/
        │       └── kt20_0385/
        │           ├── kappa_sigma_0385.csv  # meta file listing Record_Id values
        │           └── <measurement_id>/
        │               └── *.csv             # raw readings for one measurement
        │
        ├── ip_res/
        │   └── DD-MM-YY/
        │       └── kt20_0385/ip/ip_records.csv
        │
        ├── v_p/
        │   └── DD-MM-YY/
        │       └── Punditlink Data.csv
        ├── v_s/
        │   └── DD-MM-YY/
        │       └── Punditlink Data.csv
        │
        ├── gamma/
        │   ├── gamma_concentrations*.csv     # copied as-is into the 'gamma' tab
        │   └── DD-MM-YY/                     # raw data; ignored by the code
        │
        └── xrf/
            └── DD-MM-YY/
                └── *.csv                     # the last CSV found (glob order) is used
```

### Rules for date folders

- Measurement subfolders **must** be named `DD-MM-YY`, for example `07-03-24`. (Gamma is the exception: its date folders are not read at all.)
- The code skips any folder whose name does not parse as that date format, without a warning.
- Date folders are processed in chronological order. When the same measurement appears in more than one date folder, the **first** (earliest) usable result is kept and a warning is printed.

### Instrument serial numbers are hard-coded

The folder name `kt20_0385` and the file name `kappa_sigma_0385.csv` are hard-coded. If you use a different instrument unit, update the paths in `data_processing.py`:

- `cond_sus_proc()`: `kt20_0385`, `kappa_sigma_0385.csv`
- `_load_ip_records()`: `kt20_0385/ip/ip_records.csv`

---

## 4. The sample report workbook

`<Drillhole>_sample_report.xlsx` is the master record. Every property sheet in the output database is aligned to it.

| Sheet           | Required columns                                             | Used by                 |
|-----------------|--------------------------------------------------------------|-------------------------|
| `sample_report` | `sample_id` (plus any descriptive columns you want copied)   | all properties          |
| `den`           | `sample_id`, `density`                                       | `den`                   |
| `ip_res`        | `sample_id`, `measurement_id`                                | `ip_res`                |
| `cond`          | `sample_id`, `measurement_id`                                | `cond`                  |
| `sus`           | `sample_id`, `measurement_id`                                | `sus`                   |
| `v_p`           | `sample_id`, `measurement_id`                                | `v_p`                   |
| `v_s`           | `sample_id`, `measurement_id`                                | `v_s`                   |
| *(none)*        | Gamma has no sheet. The `gamma_concentrations*.csv` is copied as-is | `gamma` |
| *(none)*        | XRF has no sheet. Samples are matched through the `info` column of the XRF CSVs | `xrf` |

Sample ID conventions:

- **Matching uses the last four characters of the sample ID**, which must be numeric (for example `G2529-0123` matches on `0123`). These four-digit keys **must be unique** within `sample_report`. If they are not, the code raises `ValueError`.
- Any sample ID that **contains `cal`** is treated as a calibration or standard sample. These rows go to the `cal` sheet and are left out of the property sheet. (Gamma is not split: any calibration rows in the CSV stay in the `gamma` tab.)
- Rows whose ID is `del` are treated as deleted and dropped.
- `measurement_id` values are the instrument record IDs, for example the `Record_Id` in KT-20 files or the `ID` in Pundit files. Leave the cell **empty** if a sample was never measured.

---

## 5. Running the code

### Option A: Google Colab notebook (recommended)

1. Open `database_creation_widget.ipynb` in Google Colab.
2. **Cell 1** mounts Google Drive. Authorise access when prompted.
3. **Cell 2** imports `os` and `ipywidgets`.
4. **Cell 3** sets `path_to_database_python_code_folder` to the folder that contains `codes/` and changes into it:
   ```python
   path_to_database_python_code_folder = '/content/drive/Shared drives/CAGEO/Database_python_code/'
   ```
   Edit this line if your copy of the code lives somewhere else.
5. **Cell 4** imports the builder: `from codes.new_workbook import database as db`.
6. **Cell 5** sets `BASE_DIR`, the root that holds the site folders, and shows a **Select Folder** dropdown:
   ```python
   BASE_DIR = '/content/drive/Shareddrives/CAGEO/Database/'
   ```
   Pick a site, for example `Gortdrum`, and click **Change Directory**. The working directory is now the site folder.
7. **Cell 6** shows the database builder UI:
   - **Drillhole** dropdown: lists the subfolders of the current site.
   - **Property** checkboxes: `den`, `ip_res`, `cond`, `sus`, `v_p`, `v_s`, `gamma`, `xrf`.
   - **Run**: builds the database.

   Progress messages, warnings and the final `🎉 Processing complete.` line appear under the button.

> **Note:** Cell 3 uses `Shared drives` (with a space) and Cell 5 uses `Shareddrives` (without one). Colab usually exposes both spellings, but if you get a `FileNotFoundError`, check that both paths exist in the Colab file browser.

> **Run Cell 6 again after changing the site in Cell 5.** The drillhole list is read only when Cell 6 runs.

### Option B: Plain Python script (local or server)

The pipeline does not depend on Colab. Put the `codes` package on `sys.path`, change into the site folder, and call the same methods the notebook calls:

```python
import os, sys

CODE_DIR = r"D:\Prithwijit\codes\database_code"     # folder containing `codes/`
SITE_DIR = r"D:\path\to\Database\Gortdrum"           # folder containing drillhole folders

sys.path.insert(0, CODE_DIR)
from codes.new_workbook import database

os.chdir(SITE_DIR)

drillhole     = "G-2529-4"
property_list = ["den", "ip_res", "cond", "sus", "v_p", "v_s", "gamma", "xrf"]

db = database(drillhole)
db.createworkbook()                       # 1. new empty workbook (OVERWRITES any existing one)
db.add_sheets(property_list)              # 2. one sheet per property
db.copy_col_for_all_sheets(property_list) # 3. copy sample_report into every property sheet
db.add_cal(property_list)                 # 4. build the combined 'cal' sheet
for prop in property_list:                # 5. append processed data to each property sheet
    db.add_data(prop)
```

Run the steps **in this order**. `add_data` relies on the sheets having been seeded from `sample_report` in step 3.

### Option C: Use the processors directly (no Excel output)

To inspect the processed data without writing a workbook:

```python
from codes.data_processing import dataprocess

dp = dataprocess("G-2529-4")          # run from inside the site folder
df, df_cal = dp.cond_sus_proc("sus")  # or "cond"
df, df_cal = dp.density()
df, df_cal = dp.ip_res()
df, df_cal = dp.vel("v_p")            # or "v_s"
df, df_cal = dp.gamma()               # df is the CSV unchanged, or None if absent
df, df_cal = dp.xrf()
```

Each call returns a tuple `(df_final, df_cal)`. `df_final` holds the real samples and `df_cal` holds the calibration or standard rows. For `gamma`, `df_cal` is always empty.

---

## 6. Output workbook

The tool creates `<Drillhole>/<Drillhole>_integrated_database.xlsx`. **It is recreated from scratch on every run**, so any manual edits to an existing file are lost.

| Sheet          | Contents |
|----------------|----------|
| `<prop>` ×N    | A full copy of `sample_report`, with the processed columns for that property added on the right. **Exception:** `gamma` holds the contents of `gamma_concentrations*.csv` only (or the plain `sample_report` copy if no such CSV exists). |
| `cal`          | Calibration and standard results for all selected properties, one row per calibration number (`cal_1`, `cal_2`, …). |

### Columns added per property

| Property | Columns appended |
|----------|------------------|
| `cond`, `sus` | `mean`, `std`, `median`, `max`, `min` |
| `den` | `density` |
| `ip_res` | Every column of `ip_records.csv` except `Record_Id` |
| `v_p`, `v_s` | Every column of the Pundit export except `ID` |
| `gamma` | Not appended. The whole tab is replaced by the columns of `gamma_concentrations*.csv` |
| `xrf` | For each of the 36 elements in `XRF_ELEMENT_COLS`: `<El> Mean`, `<El> Std`, `<El> Median`, `<El> Max`, `<El> Min`, plus any other numeric columns left in the export |

### `cal` sheet columns

| Property | Columns |
|----------|---------|
| `cond` | `cond mean`, `cond std`, `cond median`, `cond max`, `cond min` |
| `sus` | `sus mean`, `sus std`, `sus median`, `sus max`, `sus min` |
| `den` | `density` |
| `ip_res` | `ip res[ohm]` (from `Resistance[ohm]`) |
| `v_p`, `v_s` | All vendor columns |
| `gamma` | None. Gamma adds nothing to the `cal` sheet |
| `xrf` | `As Concentration`, `As Error1s` (standards only, numbered in order of appearance) |

Calibration IDs in different formats (`cal_001`, `cal_17`, `std7`, …) are reduced to their integer and merged on it. The sheet runs from the lowest to the highest number seen across all properties. Cells are blank where a property has no reading for that number.

---

## 7. Processing logic per property

### `cond` / `sus`: `dataprocess.cond_sus_proc(prop)`
1. For each `cond_sus/DD-MM-YY/kt20_0385/` folder, read `kappa_sigma_0385.csv`. The delimiter is `,`, with `;` as a fallback, and the file must have a `Record_Id` column.
2. For every row in the `cond` or `sus` sheet whose `measurement_id` appears in `Record_Id`, open the first CSV in `kt20_0385/<measurement_id>/`.
3. Read the numeric readings from **column 2**, from row `HEADER_ROWS` (default 2) down to the row where the `Date` column equals `Min`.
4. Drop outliers outside **mean ± `SIGMA`·std** (default `SIGMA = 2`), then compute mean, std, median, max and min.
5. Split off calibration rows, then align the result to `sample_report`.

### `den`: `dataprocess.density()`
Takes `sample_id` and `density` straight from the `den` sheet, splits off calibration rows, and aligns the result to `sample_report`.

### `ip_res`: `dataprocess.ip_res()`
Concatenates every `ip_res/DD-MM-YY/kt20_0385/ip/ip_records.csv` into one table, with duplicate `Record_Id`s removed and a warning printed. It then left-joins this onto the `ip_res` sheet on `measurement_id` = `Record_Id`.

### `v_p` / `v_s`: `dataprocess.vel(prop)`
1. In each date folder, `Punditlink Data.csv` is converted to UTF-8 if needed. The converted copy is written **next to the original** as `Punditlink Data_utf8.csv`.
2. The file is parsed by trying each format in `VEL_READ_CONFIGS` until one produces an `ID` column:

   | sep  | header row | sample stride |
   |------|-----------:|--------------:|
   | `,`  | 14 | 25 |
   | `\t` | 10 | 16 |
   | `;`  | 14 | 25 |

   One summary row is taken every `stride` rows, starting at row 1.
3. The sampled rows are joined onto the sheet on `measurement_id` = `ID`.

### `gamma`: `dataprocess.gamma()`
No processing is done. The raw GT-40 date folders are ignored.
1. Looks for a file matching `gamma_concentrations*.csv` **directly inside** `<Drillhole>/gamma/` (not in the date folders). If several match, the first alphabetically is used and a warning is printed.
2. Reads it as-is. The delimiter (`,`, `;`, tab, …) is auto-detected; UTF-8 (with or without BOM) is tried first, then latin-1. Column names are stripped of surrounding spaces; nothing else is changed.
3. `add_data('gamma')` replaces the whole `gamma` tab with the CSV contents. There is no alignment to `sample_report` and no row-count or sample-id check.
4. If no CSV is found, a warning is printed and the `gamma` tab keeps its copy of `sample_report`.

### `xrf`: `dataprocess.xrf()`
1. Reads the last CSV in each `xrf/DD-MM-YY/` folder, trying the formats in `XRF_READ_CONFIGS` until one has an `info` column.
2. Rows whose `info` starts with `cal`, `std` or `blk` are removed. The `std` rows become the calibration output.
3. Rows with `info == 'del'` are dropped. **The last character of `info` is stripped** (a replicate or position suffix), and only IDs present in `sample_report` are kept.
4. Metadata, `Error` and `User` columns are dropped. `<LOD` becomes `0.0`, and `na` / `de` become NaN.
5. Readings are grouped by the last four digits of the sample ID. The code computes mean, std, median, max and min for each element in `XRF_ELEMENT_COLS`.
6. The result is aligned to `sample_report`. Samples with no XRF reading are marked `missing`.

---

## 8. API reference

### `codes/data_processing.py`

#### Module constants

| Name | Default | Description |
|------|---------|-------------|
| `HEADER_ROWS` | `2` | Rows to skip before numeric data in `cond`/`sus` measurement CSVs. |
| `SIGMA` | `2` | Outlier threshold, in standard deviations, for `cond`/`sus`. |
| `XRF_ELEMENT_COLS` | 36 columns | The `<El> Concentration` columns aggregated for XRF (Mg, Al, Si, P, S, K, Ca, Ti, V, Cr, Mn, Fe, Co, Ni, Cu, Zn, As, Se, Rb, Sr, Y, Zr, Nb, Mo, Ag, Cd, Sn, Sb, W, Au, Hg, Pb, Bi, Th, U, LE). |
| `XRF_READ_CONFIGS` | 4 configs | `(sep, header)` combinations tried when reading XRF CSVs. |
| `VEL_READ_CONFIGS` | 3 configs | `(sep, header, stride)` combinations tried when reading Pundit CSVs. |
| `GAMMA_CSV_PATTERN` | `'gamma_concentrations*.csv'` | File name pattern searched for in `<Drillhole>/gamma/`. |

#### Public helper functions

| Function | Description |
|----------|-------------|
| `find_missing_list_indices(dataframe, column_name, value_list)` | Reorders `dataframe` to match `value_list`, the full list of expected sample IDs, using the last four digits as the key. Drops `del` rows and duplicate keys. Samples absent from the sheet get a blank row with only the sample ID filled in, and their IDs are printed. Raises `ValueError` if the keys in `value_list` are not unique. |
| `extract_last_four_digits(number)` | Returns `float(str(number)[-4:])`. |
| `convert_csv_to_utf8(input_file)` | Detects the file encoding with `chardet`. If it is not UTF-8, writes `<name>_utf8.csv` and returns that path. Otherwise returns the original path. |

#### Private helpers

| Function | Description |
|----------|-------------|
| `_sorted_date_folders(directory)` | Subfolder names that parse as `%d-%m-%y`, sorted chronologically. |
| `_load_measurement_stats(csv_path, header_rows, sigma)` | Reads one `cond`/`sus` reading CSV and returns a dict of outlier-filtered stats. Returns `None` if the file is unusable (no single `Min` marker, or every value is an outlier). |
| `_read_kappa_sigma_meta(csv_path)` | Reads the KT-20 meta CSV with a `,` or `;` delimiter. Raises if `Record_Id` is not found. |
| `_load_ip_records(ip_res_dir)` | Concatenates every `ip_records.csv` and de-duplicates `Record_Id`. |
| `_read_vel_csv(csv_path)` | Tries each `VEL_READ_CONFIGS` entry and returns the sampled rows, or `None`. |
| `_load_vel_records(prop_dir)` | Converts and reads every `Punditlink Data.csv`, concatenates them, and de-duplicates `ID`. |
| `_read_xrf_csv(csv_path)` | Tries each `XRF_READ_CONFIGS` entry and returns the DataFrame, or `None`. |
| `_load_xrf_records(xrf_dir)` | Concatenates the last CSV from every XRF date folder. |
| `_find_gamma_concentrations_csv(gamma_dir)` | Path of the first `gamma_concentrations*.csv` directly in `gamma_dir`, or `None`. |
| `_read_gamma_concentrations_csv(csv_path)` | Reads that CSV unchanged, with auto-detected delimiter and a UTF-8 → latin-1 encoding fallback. |

#### `class dataprocess(drillhole)`

| Attribute / method | Returns | Description |
|--------------------|---------|-------------|
| `drillhole` | | Drillhole folder name. |
| `path_to_report` | | `<drillhole>/<drillhole>_sample_report.xlsx` |
| `_load_inventory()` | `dict[str, DataFrame]` | Every sheet of the sample report. |
| `_sample_id_report(inventory)` | `list` | `sample_id` values from the `sample_report` sheet. |
| `cond_sus_proc(prop, header_rows=2, sigma=2)` | `(df_final, df_cal)` | Conductivity (`'cond'`) or susceptibility (`'sus'`) statistics. |
| `density()` | `(df_final, df_cal)` | Density values. |
| `ip_res()` | `(df_final, df_cal)` | IP / resistance records. |
| `vel(prop)` | `(df_final, df_cal)` | P-wave (`'v_p'`) or S-wave (`'v_s'`) velocity records. |
| `xrf()` | `(result_df, new_cal)` | Aggregated XRF geochemistry and standards. |
| `gamma()` | `(df_gamma, df_cal)` | Contents of `gamma_concentrations*.csv` unchanged (or `None` if absent); `df_cal` is always empty. |

All returned DataFrames use a **`sample id`** column (with a space) as the identifier, except `gamma()`, which keeps the CSV's own column names.

### `codes/new_workbook.py`

#### `_extract_cal_number(sample_id)`
Returns the first run of digits in a calibration ID as an `int` (`'cal_012'` → `12`, `'std7'` → `7`), or `None`.

#### `class database(dataprocess)`

| Attribute / method | Description |
|--------------------|-------------|
| `path_to_database` | `<drillhole>/<drillhole>_integrated_database.xlsx` |
| `path_to_report` | `<drillhole>/<drillhole>_sample_report.xlsx` |
| `createworkbook()` | Creates and saves an empty workbook. **Overwrites an existing file.** |
| `add_sheets(property_list)` | Adds one empty sheet per property name and removes the empty default `Sheet` that `openpyxl` creates. |
| `copy_sheet_columns(property_sheet, sample_report)` | Copies every cell from one openpyxl worksheet to another, value for value. |
| `copy_col_for_all_sheets(property_list)` | Seeds each property sheet with a full copy of the `sample_report` sheet. |
| `select_and_process(prop)` | Calls the right `dataprocess` method for `prop` and renames or selects the calibration columns (see the [`cal` sheet columns](#cal-sheet-columns)). Raises `ValueError` for an unknown property. |
| `add_data(prop)` | Processes `prop` and appends its columns to the matching sheet. Before writing, it checks that **(a)** the row counts match and **(b)** the last four digits of every `sample_id` line up row by row. If either check fails, it raises `ValueError` and writes nothing. For `gamma`, these checks are skipped and the tab is replaced with the CSV contents. |
| `add_cal(prop_list)` | Builds the combined `cal` sheet (see [Output workbook](#6-output-workbook)). |

---

## 9. Missing-data conventions

The output uses two kinds of empty cell, and they mean different things:

| Cell value | Meaning |
|------------|---------|
| **Blank (NaN)** | **Case 1: never measured.** The `measurement_id` was empty in the sample report, or the sample does not appear in that property's sheet at all. No data was expected. |
| **`missing`** | **Case 2: measured but no data found.** A `measurement_id` was recorded, but no matching raw file or record exists, or the file could not be used. Check the raw data. |

For XRF, any sample in `sample_report` without an XRF reading is marked `missing`.

---

## 10. Troubleshooting

| Message | Likely cause and fix |
|---------|----------------------|
| `Sheet '<prop>' not found in ..._sample_report.xlsx` | The sample report has no sheet named after that property. Add it, or untick that property. |
| `Sheet 'sample_report' not found` | The master sheet must be named exactly `sample_report`. |
| `value_list has non-unique last-four-digit keys` / `sample_id_report has non-unique last-four-digit keys` | Two sample IDs end in the same four digits. Matching relies on these being unique. |
| `Row count mismatch writing '<prop>'` | The processed data has a different number of rows from `sample_report`. This usually happens with `ip_res`, `v_p` or `v_s`, which are **not** re-aligned to `sample_report`: their property sheet must list the same non-calibration samples in the same order as `sample_report`. |
| `Sample id mismatch writing '<prop>'` | The rows are in a different order from `sample_report`. Reorder the property sheet. |
| `Could not find 'Record_Id' column` | The KT-20 meta CSV is not in the expected format. |
| `Warning: none of the known formats parsed ...` / `cannot read ... with any known format` | Unknown export layout. Add a new entry to `VEL_READ_CONFIGS` or `XRF_READ_CONFIGS`. |
| `Warning: duplicate Record_Id / ID / Id ...` | The same record appears in more than one date folder. The first one is kept. |
| `Warning: no 'gamma_concentrations*.csv' found in <Drillhole>/gamma` | No gamma CSV directly in the `gamma` folder (one inside a date folder is not found). The `gamma` tab is left as a copy of `sample_report`. |
| `Skipping <date>: no meta CSV found` | That date folder has no `kt20_0385/kappa_sigma_0385.csv`. |
| `ModuleNotFoundError: No module named 'codes'` | The folder containing `codes/` is not the working directory or on `sys.path` when you import. |
| `FileNotFoundError` on the sample report | The working directory is not the site folder. Run the **Change Directory** cell again (notebook) or `os.chdir(SITE_DIR)` (script). |
| `PermissionError` when saving | The output `.xlsx` is open in Excel. Close it and run again. |

---

## 11. Known limitations and notes

- **Every run overwrites the output workbook.** Keep a copy if you have edited it by hand.
- **Each property is processed twice per run**: once in `add_cal` and once in `add_data`. Large XRF or Pundit datasets therefore take roughly twice as long to process, and warnings are printed twice.
- **`v_p` / `v_s` write files into your data folders.** Non-UTF-8 Pundit exports produce a `Punditlink Data_utf8.csv` copy.
- **Pundit header rows and strides are fixed.** Check them against your actual export layout.
- **XRF below-detection values (`<LOD`) are set to 0**, which understates trace-element concentrations compared with an LOD/2 substitution. Mention this in your methods section.
- **XRF file selection:** only the *last* CSV in each date folder (in `glob` order) is read.
- **Gamma is copied, not processed.** The `gamma` tab is exactly what is in `gamma_concentrations*.csv`: it is not checked against `sample_report`, its rows may be in a different order or count, and any calibration rows stay in it.
- **The calibration test differs between properties.** Most properties use "contains `cal`". XRF uses the `cal`/`std`/`blk` prefixes in the `info` column. Gamma has none.
