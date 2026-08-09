"""
Drillhole geophysical/geochemical measurement processing.


NOTE ON `gamma`: the code needs modifications in the future based on the equipment troubleshoot.
"""

import os
import glob
import numpy as np
import pandas as pd
import chardet
from pathlib import Path
from datetime import datetime


# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

HEADER_ROWS = 2   # rows to skip before numeric data starts (cond_sus)
SIGMA = 2         # outlier threshold in std devs (cond_sus)

# Single source of truth for the analyte columns used across all five xrf
# groupby aggregations -- avoids independently-maintained duplicate lists
# drifting out of sync if elements are added/removed. (The original had
# this same 36/37-element list repeated five times, with 'Mg Concentration'
# accidentally duplicated within each copy.)
XRF_ELEMENT_COLS = [
    'Mg Concentration', 'Al Concentration', 'Si Concentration', 'P Concentration',
    'S Concentration', 'K Concentration', 'Ca Concentration', 'Ti Concentration',
    'V Concentration', 'Cr Concentration', 'Mn Concentration', 'Fe Concentration',
    'Co Concentration', 'Ni Concentration', 'Cu Concentration', 'Zn Concentration',
    'As Concentration', 'Se Concentration', 'Rb Concentration', 'Sr Concentration',
    'Y Concentration', 'Zr Concentration', 'Nb Concentration', 'Mo Concentration',
    'Ag Concentration', 'Cd Concentration', 'Sn Concentration', 'Sb Concentration',
    'W Concentration', 'Au Concentration', 'Hg Concentration', 'Pb Concentration',
    'Bi Concentration', 'Th Concentration', 'U Concentration', 'LE Concentration',
]

# (sep, header) combinations to try in order for the different XRF export formats
XRF_READ_CONFIGS = [
    {'sep': ',', 'header': 1},
    {'sep': ',', 'header': 0},
    {'sep': ';', 'header': 0},
    {'sep': '\t', 'header': 0},
]

# (sep, header_row, sample_stride) configs to try, in order, for the different
# vendor export formats seen in `vel`. header_row/stride are best-guess
# constants inherited from the original code -- confirm against actual file
# layouts before relying on them.
VEL_READ_CONFIGS = [
    {'sep': ',', 'header': 14, 'stride': 25},
    {'sep': '\t', 'header': 10, 'stride': 16},
    {'sep': ';', 'header': 14, 'stride': 25},
]

GAMMA_STAT_COLS = [
    'K_mean', 'K_median', 'K_max', 'K_min', 'K_std',
    'U_mean', 'U_median', 'U_max', 'U_min', 'U_std',
    'Th_mean', 'Th_median', 'Th_max', 'Th_min', 'Th_std',
]


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _sorted_date_folders(directory):
    """
    List subfolder names of `directory` that parse as %d-%m-%y dates,
    sorted chronologically. Anything that isn't a valid date-named folder
    is silently skipped.
    """
    date_folders = []
    for name in os.listdir(directory):
        try:
            date_folders.append((datetime.strptime(name, "%d-%m-%y"), name))
        except ValueError:
            continue
    return [name for _, name in sorted(date_folders)]


def find_missing_list_indices(dataframe, column_name, value_list):
    """
    Align `dataframe` to the full `value_list` of expected sample ids.

    A value_list entry with no matching row in `dataframe` at all means
    that sample was never logged in this sheet -- treated as case 1
    (blank row: sample id restored, every other cell left as real NaN).
    Rows already present with 'missing' in other columns (case 2, set by
    the calling function before this runs) are left untouched.
    """
    df = dataframe.copy()
    df = df[df[column_name] != 'del'].reset_index(drop=True)

    def last_four_key(x):
        if pd.isna(x):
            return None
        try:
            return int(str(x)[-4:])
        except ValueError:
            return None

    df['_key'] = df[column_name].apply(last_four_key)

    value_keys = [int(str(x)[-4:]) for x in value_list]
    if pd.Series(value_keys).duplicated().any():
        dupes = pd.Series(value_keys)[pd.Series(value_keys).duplicated()].unique().tolist()
        raise ValueError(f"value_list has non-unique last-four-digit keys: {dupes}")

    df = df[df['_key'].notna()].drop_duplicates(subset='_key')
    df = df.set_index('_key').reindex(value_keys)
    df = df.drop(columns=['_key'], errors='ignore')

    # A row that's entirely NaN (including column_name) is one reindex just
    # introduced -- i.e. this sample id had no row in the sheet at all.
    never_logged_mask = df.isna().all(axis=1)
    if never_logged_mask.any():
        ids = [v for v, m in zip(value_list, never_logged_mask) if m]
        print(f"Note: {len(ids)} sample id(s) not present in this sheet at all: {ids}")

    df.loc[never_logged_mask, column_name] = [
        str(v) for v, m in zip(value_list, never_logged_mask) if m
    ]

    return df.reset_index(drop=True)


def extract_last_four_digits(number):
    return float(str(number)[-4:])


def convert_csv_to_utf8(input_file):
    """
    Detect encoding and, if not already UTF-8, write a UTF-8 copy alongside
    the original. Returns the path that should actually be read downstream,
    so callers never have to re-detect encoding or guess which file to open
    (the original converted one hardcoded filename but then read whatever
    `glob` happened to return last, which were not guaranteed to be the
    same file).
    """
    with open(input_file, 'rb') as f:
        raw = f.read()
    enc = chardet.detect(raw)

    if enc['encoding'] and enc['encoding'].lower() == 'utf-8':
        print(f"The file {input_file} is already in UTF-8 encoding.")
        return input_file

    df = pd.read_csv(input_file, encoding=enc['encoding'])
    output_file = input_file.replace('.csv', '_utf8.csv')
    df.to_csv(output_file, encoding='utf-8', sep=',', index=False)
    print(f"File converted and saved as {output_file}")
    return output_file


# ---------------------------------------------------------------------------
# cond_sus helpers
# ---------------------------------------------------------------------------

def _load_measurement_stats(csv_path, header_rows=HEADER_ROWS, sigma=SIGMA):
    """Read one cond_sus measurement CSV and return outlier-filtered summary
    stats, or None if unusable."""
    df = pd.read_csv(csv_path)

    min_marker_rows = df.index[df['Date'] == 'Min'].to_list()
    if len(min_marker_rows) != 1:
        return None
    end_row = min_marker_rows[0]

    raw_values = np.array(df.iloc[header_rows:end_row, 1]).astype('float32')
    raw_values = np.reshape(raw_values, (end_row - header_rows, 1))

    mean = raw_values.astype('float64').mean()
    std = raw_values.astype('float64').std()

    # masked_outside(x, v1, v2) masks x < v1 or x > v2 -- lower bound first
    masked = np.ma.masked_outside(raw_values, mean - sigma * std, mean + sigma * std)

    if masked.compressed().size == 0:   # all values flagged as outliers
        return None

    return {
        'mean': np.mean(masked),
        'std': np.std(masked),
        'median': np.median(masked),
        'max': np.max(masked),
        'min': np.min(masked),
    }


def _read_kappa_sigma_meta(csv_path):
    """Read the kappa_sigma meta CSV, trying comma then semicolon delimiter."""
    for sep in (',', ';'):
        meta_data = pd.read_csv(csv_path, sep=sep)
        if 'Record_Id' in meta_data.columns:
            return meta_data
    raise ValueError(f"Could not find 'Record_Id' column in {csv_path} with ',' or ';' delimiter")


# ---------------------------------------------------------------------------
# ip_res helpers
# ---------------------------------------------------------------------------

def _load_ip_records(ip_res_dir):
    """
    Read every ip_records.csv across all date/instrument subfolders exactly
    once, concatenating into a single Record_Id -> measurement lookup table.
    """
    all_records = []
    for folder_name in _sorted_date_folders(ip_res_dir):
        csv_path = ip_res_dir / folder_name / 'kt20_0385' / 'ip' / 'ip_records.csv'
        if csv_path.exists():
            all_records.append(pd.read_csv(csv_path))
        else:
            print(f"Warning: no ip_records.csv found for {folder_name}")

    if not all_records:
        return pd.DataFrame(columns=['Record_Id'])

    combined = pd.concat(all_records, ignore_index=True)

    # Guard against the same Record_Id appearing in more than one file --
    # without this, a duplicate would silently create a 1:many merge and
    # inflate row count rather than erroring out.
    dup_mask = combined['Record_Id'].duplicated()
    if dup_mask.any():
        dupes = combined.loc[dup_mask, 'Record_Id'].unique().tolist()
        print(f"Warning: duplicate Record_Id(s) across ip_records.csv files: {dupes}")
        combined = combined[~dup_mask]

    return combined


# ---------------------------------------------------------------------------
# vel helpers
# ---------------------------------------------------------------------------

def _read_vel_csv(csv_path):
    """
    Try each known (sep, header, stride) combination until one produces an
    'ID' column. Returns None if nothing works -- explicitly, so a failed
    parse can never fall through and reuse another folder's leftover data
    (the original's failure mode when all delimiter attempts raised
    KeyError).
    """
    for cfg in VEL_READ_CONFIGS:
        try:
            df_data = pd.read_csv(csv_path, sep=cfg['sep'], encoding='utf-8', header=cfg['header'])
            df_data.columns = df_data.columns.str.strip()
            if 'ID' not in df_data.columns:
                continue
            sample_rows = list(range(1, len(df_data), cfg['stride']))
            return df_data.iloc[sample_rows]
        except (KeyError, pd.errors.ParserError):
            continue

    print(f"Warning: none of the known formats parsed {csv_path}")
    return None


def _load_vel_records(prop_dir):
    """
    Walk every date-named subfolder once, convert/read its raw vendor CSV,
    and concatenate the sampled rows into a single ID -> record lookup table.
    """
    all_records = []
    for folder_name in _sorted_date_folders(prop_dir):
        folder_path = prop_dir / folder_name

        raw_path = folder_path / 'Punditlink Data.csv'
        if not raw_path.exists():
            print(f"Warning: no 'Punditlink Data.csv' in {folder_path}")
            continue

        # Convert (if needed) and read the SAME file path back -- removes
        # the original's disconnect between what was converted and what
        # was actually read (it hardcoded the conversion target but read
        # glob's last match, which weren't guaranteed to be the same file).
        utf8_path = convert_csv_to_utf8(str(raw_path))
        sampled = _read_vel_csv(utf8_path)
        if sampled is not None:
            all_records.append(sampled)

    if not all_records:
        return pd.DataFrame(columns=['ID'])

    combined = pd.concat(all_records, ignore_index=True)
    combined['ID'] = combined['ID'].astype(str).str.strip()

    dup_mask = combined['ID'].duplicated()
    if dup_mask.any():
        dupes = combined.loc[dup_mask, 'ID'].unique().tolist()
        print(f"Warning: duplicate ID(s) across vendor CSVs: {dupes}")
        combined = combined[~dup_mask]

    return combined


# ---------------------------------------------------------------------------
# xrf helpers
# ---------------------------------------------------------------------------

def _read_xrf_csv(csv_path):
    """
    Try each known format until one produces an 'info' column. Returns None
    if nothing works, so a failed folder contributes zero rows instead of
    silently duplicating the previous folder's data.
    """
    for cfg in XRF_READ_CONFIGS:
        try:
            df_xrf = pd.read_csv(csv_path, sep=cfg['sep'], skiprows=1 if cfg['header'] == 1 else 0)
            if 'info' in df_xrf.columns:
                return df_xrf
        except (KeyError, pd.errors.ParserError):
            continue
    print(f"Warning: cannot read {csv_path} with any known format")
    return None


def _load_xrf_records(xrf_dir):
    all_records = []
    for folder_name in _sorted_date_folders(xrf_dir):
        folder_path = xrf_dir / folder_name
        csv_files = glob.glob(str(folder_path / '*.csv'))
        if not csv_files:
            print(f"Warning: no CSV in {folder_path}")
            continue
        df_xrf = _read_xrf_csv(csv_files[-1])
        if df_xrf is not None:
            all_records.append(df_xrf)

    return pd.concat(all_records, ignore_index=True) if all_records else pd.DataFrame()


# ---------------------------------------------------------------------------
# gamma helpers
# ---------------------------------------------------------------------------

def _read_gamma_assay_csv(csv_path):
    """Read a gamma assay CSV, trying semicolon then comma delimiter
    (matches the original's try order)."""
    for sep in (';', ','):
        try:
            assay = pd.read_csv(csv_path, sep=sep)
            assay.columns = assay.columns.str.strip()
            if 'Id' in assay.columns:
                return assay[assay['Id'].notna()]
        except (KeyError, pd.errors.ParserError):
            continue
    print(f"Warning: cannot read {csv_path} with ';' or ',' delimiter")
    return None


def _load_gamma_assays(gamma_dir):
    """
    Read every assay CSV across all date folders exactly once, concatenating
    into a single Id -> assay-row lookup table.

    NOTE: the original processed each date folder's assay file independently
    and matched df_record against it per-folder. If a single sample's three
    replicate measurement_ids were split across two different dates, the
    original would produce two partial (and incorrectly separate) result
    rows for that one sample. Building one combined table across all folders
    first, as done here, avoids that -- consistent with the fix applied to
    ip_res/vel/xrf -- but changes behavior if that split-across-folders case
    actually occurs in your data. Verify against real folders before relying
    on this.
    """
    all_assays = []
    for folder_name in _sorted_date_folders(gamma_dir):
        assay_dir = gamma_dir / folder_name / 'gt40_0154' / 'assay'
        csv_files = glob.glob(str(assay_dir / '*.csv'))
        if not csv_files:
            print(f"Warning: no assay CSV in {assay_dir}")
            continue
        df_assay = _read_gamma_assay_csv(csv_files[0])
        if df_assay is not None:
            all_assays.append(df_assay)

    if not all_assays:
        return pd.DataFrame(columns=['Id'])

    combined = pd.concat(all_assays, ignore_index=True)
    dup_mask = combined['Id'].duplicated()
    if dup_mask.any():
        dupes = combined.loc[dup_mask, 'Id'].unique().tolist()
        print(f"Warning: duplicate assay Id(s) across folders: {dupes}")
        combined = combined[~dup_mask]

    return combined


# ---------------------------------------------------------------------------
# Main class
# ---------------------------------------------------------------------------

class dataprocess:
    """
    Processes drillhole geophysical/geochemical measurement data against a
    master sample_report workbook.

    Expected on-disk layout, relative to `drillhole`:
        {drillhole}/{drillhole}_sample_report.xlsx   -- master workbook
        {drillhole}/{prop}/{DD-MM-YY}/...             -- per-property, per-date data

    Parameters
    ----------
    drillhole : str
        Drillhole folder name.
    """

    def __init__(self, drillhole):
        self.drillhole = drillhole
        self.path_to_report = Path(drillhole) / f'{drillhole}_sample_report.xlsx'

    def _load_inventory(self):
        return pd.read_excel(self.path_to_report, sheet_name=None)

    def _sample_id_report(self, data_inventory):
        df_report = data_inventory.get('sample_report')
        if df_report is None:
            raise ValueError(f"Sheet 'sample_report' not found in {self.path_to_report}")
        return df_report['sample_id'].to_list()

    # -- cond_sus / mag ----------------------------------------------------

    def cond_sus_proc(self, prop, header_rows=HEADER_ROWS, sigma=SIGMA):
        base_dir = Path(self.drillhole)
        cond_sus_dir = base_dir / 'cond_sus'

        data_inventory = self._load_inventory()
        df_record = data_inventory.get(prop)
        if df_record is None:
            raise ValueError(f"Sheet '{prop}' not found in {self.path_to_report}")
        sample_id_report = self._sample_id_report(data_inventory)

        df_record = df_record.reset_index(drop=True)

        results = []
        stat_cols = ['mean', 'std', 'median', 'max', 'min']

        for folder_name in _sorted_date_folders(cond_sus_dir):
            instrument_dir = cond_sus_dir / folder_name / 'kt20_0385'
            meta_csv = instrument_dir / 'kappa_sigma_0385.csv'
            if not meta_csv.exists():
                print(f"Skipping {folder_name}: no meta CSV found")
                continue

            meta_data = _read_kappa_sigma_meta(meta_csv)
            df_record_sub = df_record[df_record['measurement_id'].isin(meta_data['Record_Id'])]

            for orig_idx, row in df_record_sub.iterrows():
                record_dir = instrument_dir / str(int(row['measurement_id']))
                csv_files = glob.glob(str(record_dir / '*.csv'))
                if not csv_files:
                    continue

                stats = _load_measurement_stats(csv_files[0], header_rows=header_rows, sigma=sigma)
                if stats is None:
                    continue

                results.append({'orig_index': orig_idx, **stats})

        df_proc = pd.DataFrame(results).set_index('orig_index') if results else pd.DataFrame(columns=stat_cols)
        df_proc = df_proc.reindex(df_record.index)

        # sample id is always filled, whether or not a measurement was found --
        # case 1 rows (measurement_id never recorded) still show their sample id.
        df_proc.insert(0, 'sample id', df_record['sample_id'].astype(str).values)

        not_recorded = df_record['measurement_id'].isna().values
        no_data_found = df_proc[stat_cols].isna().all(axis=1).values

        # Case 2: measurement_id WAS recorded, but no usable data was found for it
        data_missing_mask = no_data_found & ~not_recorded
        df_proc.loc[data_missing_mask, :] = 'missing'
        df_proc.loc[data_missing_mask, 'sample id'] = df_record.loc[data_missing_mask, 'sample_id'].astype(str).values

        cal_mask = df_proc['sample id'].str.contains('cal', na=False)
        df_cal = df_proc[cal_mask]
        df_final = df_proc[~cal_mask]
        df_final.index = range(len(df_final))

        # Cross-check against the full sample_report: a sample id entirely absent
        # from this sheet is case 1 (blank), same treatment as an explicit NaN.
        df_final = find_missing_list_indices(df_final, 'sample id', sample_id_report)

        return df_final, df_cal

    # -- density -------------------------------------------------------------

    def density(self):
        data_inventory = self._load_inventory()
        sample_id_report = self._sample_id_report(data_inventory)

        df_den = data_inventory.get('den')
        if df_den is None:
            raise ValueError(f"Sheet 'den' not found in {self.path_to_report}")

        df_out = df_den[['sample_id', 'density']].copy()
        df_out['sample_id'] = df_out['sample_id'].astype(str)
        df_out.rename(columns={'sample_id': 'sample id'}, inplace=True)

        cal_mask = df_out['sample id'].str.contains('cal', na=False)
        df_cal = df_out[cal_mask]

        df_final = df_out[~cal_mask].copy()
        df_final.index = range(len(df_final))

        # density has no separate "recorded but not found" step (the value is
        # read directly from the sheet), so every gap here is case 1 (blank).
        df_final = find_missing_list_indices(df_final, 'sample id', sample_id_report)

        return df_final, df_cal

    # -- ip_res ----------------------------------------------------------

    def ip_res(self):
        ip_res_dir = Path(self.drillhole) / 'ip_res'

        data_inventory = self._load_inventory()
        df_record = data_inventory.get('ip_res')
        if df_record is None:
            raise ValueError(f"Sheet 'ip_res' not found in {self.path_to_report}")

        df_record = df_record.reset_index(drop=True)
        ip_records = _load_ip_records(ip_res_dir)

        result_df = df_record[['sample_id', 'measurement_id']].merge(
            ip_records,
            left_on='measurement_id',
            right_on='Record_Id',
            how='left',
        )

        # Case 1: measurement_id was never recorded (NaN in the sample report)
        #   -> leave the row blank (real NaN) -- no data was ever expected here.
        # Case 2: measurement_id WAS recorded, but no matching Record_Id was
        # found in any ip_records.csv -> mark the row 'missing'.
        not_recorded = df_record['measurement_id'].isna().values   # .values forces
        no_match = result_df['Record_Id'].isna().values             # positional alignment

        data_missing_mask = no_match & ~not_recorded

        result_df['sample_id'] = df_record['sample_id'].astype(str)
        result_df.rename(columns={'sample_id': 'sample id'}, inplace=True)
        result_df.drop(columns=['measurement_id', 'Record_Id'], inplace=True)

        result_df.loc[data_missing_mask, :] = 'missing'
        result_df.loc[data_missing_mask, 'sample id'] = df_record.loc[data_missing_mask, 'sample_id'].astype(str).values

        cal_mask = result_df['sample id'].str.contains('cal', na=False)
        df_cal = result_df[cal_mask]
        df_final = result_df[~cal_mask].copy()
        df_final.index = range(len(df_final))

        return df_final, df_cal

    # -- vel / v_p / v_s -----------------------------------------------------

    def vel(self, prop):
        prop_dir = Path(self.drillhole) / prop

        data_inventory = self._load_inventory()
        df_record = data_inventory.get(prop)
        if df_record is None:
            raise ValueError(f"Sheet '{prop}' not found in {self.path_to_report}")
        df_record = df_record.reset_index(drop=True)

        vel_records = _load_vel_records(prop_dir)

        measurement_id_str = df_record['measurement_id'].apply(
            lambda x: str(int(x)) if pd.notna(x) else pd.NA
        )

        result_df = pd.DataFrame({
            'sample id': df_record['sample_id'].astype(str),
            'measurement_id': measurement_id_str,
        }).merge(vel_records, left_on='measurement_id', right_on='ID', how='left')

        not_recorded = df_record['measurement_id'].isna().values
        no_match = result_df['ID'].isna().values

        # Case 2: measurement_id WAS recorded, but no matching vendor CSV row found
        data_missing_mask = no_match & ~not_recorded

        result_df.drop(columns=['measurement_id', 'ID'], inplace=True)
        result_df.loc[data_missing_mask, :] = 'missing'
        result_df.loc[data_missing_mask, 'sample id'] = df_record.loc[data_missing_mask, 'sample_id'].astype(str).values

        # Case 1 rows (measurement_id never recorded) are already blank/NaN from
        # the left-merge -- nothing further to do for them.

        # Calibration samples are tagged with 'cal' in the sample ID and reported
        # separately from real measurements, matching the convention used by
        # cond_sus_proc/density/ip_res.
        cal_mask = result_df['sample id'].str.contains('cal', na=False)
        df_cal = result_df[cal_mask]
        df_final = result_df[~cal_mask].copy()
        df_final.index = range(len(df_final))

        return df_final, df_cal

    # -- xrf ---------------------------------------------------------------

    def xrf(self):
        xrf_dir = Path(self.drillhole) / 'xrf'

        data_inventory = self._load_inventory()
        sample_id_report = self._sample_id_report(data_inventory)

        df_proc = _load_xrf_records(xrf_dir)
        info = df_proc['info'].tolist()

        # Rows tagged as calibration/standard/blank material -- excluded from
        # the real-sample table entirely
        drop_list = [
            i for i, val in enumerate(info)
            if isinstance(val, str) and (val.startswith('cal') or val.startswith('std') or val.startswith('blk'))
        ]

        # Standards specifically (literal 'std' prefix) are pulled out
        # separately into new_cal
        cal_list = [i for i, val in enumerate(info) if isinstance(val, str) and val.startswith('std')]

        new_df = df_proc.drop(df_proc.index[drop_list])
        new_cal = df_proc.iloc[cal_list].reset_index(drop=True)

        new_cal['info'] = ['cal_' + str(i) for i in range(1,len(new_cal)+1)]
        new_cal = new_cal[['info', 'As Concentration', 'As Error1s']].rename(columns={'info': 'sample id'})

        new_df = new_df.drop(new_df[new_df['info'] == 'del'].index)

        # Sample IDs in the raw 'info' field carry a trailing letter suffix
        # (e.g. replicate/position marker) that isn't part of the true sample ID
        new_df['info'] = new_df['info'].astype(str).str[:-1]
        new_df.index = range(len(new_df))

        str_sample_id_report = [str(x) for x in sample_id_report]
        keep_mask = new_df['info'].isin(str_sample_id_report)
        new_df = new_df[keep_mask].reset_index(drop=True)

        new_df = new_df.dropna(axis=1, how='all')
        new_df.columns = new_df.columns.str.strip()
        new_df = new_df.drop(
            columns=['Instrument Serial Num', 'Reading #', 'Date', 'Time',
                     'Method Name', 'Test Label', 'Collimation Status', 'Units'],
            errors='ignore',
        )
        new_df = new_df.drop(columns=new_df.filter(regex='Error').columns)
        new_df = new_df.drop(columns=new_df.filter(regex='User').columns)

        # Below-detection-limit readings are set to zero here -- note for the
        # methods section that this understates true concentration relative
        # to e.g. an LOD/2 substitution, particularly for trace elements with
        # many <LOD readings
        new_df = new_df.replace('<LOD', '0.0')
        new_df = new_df.replace({'na': np.nan, 'de': np.nan})

        info_col = new_df['info']
        numeric_df = new_df.drop(columns=['info']).apply(pd.to_numeric, errors='coerce')
        new_df = pd.concat([numeric_df, info_col], axis=1)
        new_df['temp_info'] = new_df['info'].apply(extract_last_four_digits)

        # temp_info (last 4 digits) is assumed unique per sample -- a safe
        # groupby/join key. Build an explicit temp_info -> sample_id lookup.
        id_lookup = new_df[['temp_info', 'info']].drop_duplicates(subset='temp_info')

        agg_funcs = {'Mean': 'mean', 'Std': 'std', 'Median': 'median', 'Max': 'max', 'Min': 'min'}
        agg_frames = []
        for suffix, func in agg_funcs.items():
            grouped = new_df.groupby('temp_info')[XRF_ELEMENT_COLS].agg(func).reset_index()
            grouped.columns = ['temp_info'] + [col.replace('Concentration', suffix) for col in XRF_ELEMENT_COLS]
            agg_frames.append(grouped)

        result_df = agg_frames[0]
        for frame in agg_frames[1:]:
            result_df = result_df.merge(frame, on='temp_info')

        result_df = result_df.merge(id_lookup, on='temp_info', how='left')
        result_df = result_df.drop(columns=['temp_info']).rename(columns={'info': 'sample id'})

        # Align result_df to sample_id_report, marking unmatched rows 'missing'
        report_keys = [int(str(x)[-4:]) for x in sample_id_report]

        if pd.Series(report_keys).duplicated().any():
            dupe_keys = pd.Series(report_keys)[pd.Series(report_keys).duplicated()].unique().tolist()
            raise ValueError(
                f"sample_id_report has non-unique last-four-digit keys: {dupe_keys} "
                "-- reindex-based alignment is not safe with duplicate keys."
            )

        result_df['_match_key'] = result_df['sample id'].apply(lambda x: int(str(x)[-4:]))
        result_df = result_df.set_index('_match_key').reindex(report_keys)

        missing_mask = result_df.isna().all(axis=1)
        if missing_mask.any():
            missing_ids = [sid for sid, is_missing in zip(sample_id_report, missing_mask) if is_missing]
            print(f"Warning: no XRF match for {len(missing_ids)} sample id(s): {missing_ids}")

        result_df.loc[missing_mask, :] = 'missing'
        result_df.loc[missing_mask, 'sample id'] = [
            str(s) for s, m in zip(sample_id_report, missing_mask) if m
        ]

        result_df = result_df.reset_index(drop=True)

        return result_df, new_cal

    # -- gamma ---------------------------------------------------------------

    def gamma(self):
        """
        Process gamma (K/U/Th) assay data.

        """
        gamma_dir = Path(self.drillhole) / 'gamma'

        data_inventory = self._load_inventory()
        df_record = data_inventory.get('gamma')
        if df_record is None:
            raise ValueError(f"Sheet 'gamma' not found in {self.path_to_report}")
        sample_id_report = self._sample_id_report(data_inventory)

        df_record = df_record.reset_index(drop=True)
        df_assay = _load_gamma_assays(gamma_dir)

        row_stats = {}     # orig_index -> dict of stats, or None to mark 'missing'
        cal_results = []

        for idx, row in df_record.iterrows():
            sample_id = str(row['sample_id'])

            # Case 1: no measurement recorded for this sample at all -- leave
            # blank. (Only measurement_id1 is checked, matching the original.)
            if pd.isna(row['measurement_id1']):
                continue

            meas_ids = [row['measurement_id1'], row['measurement_id2'], row['measurement_id3']]
            df_temp = df_assay[df_assay['Id'].isin(meas_ids)].replace('<  0.00000', '0')

            if sample_id.startswith('cal'):
                if len(df_temp) < 3:
                    print(f"Warning: expected 3 replicate rows for calibration sample "
                          f"{sample_id}, found {len(df_temp)} -- skipping")
                    continue
                cal_results.append({
                    'sample id': sample_id,
                    'K_cal': float(df_temp['Component_1 value'].to_list()[0]),
                    'U_cal': float(df_temp['Component_2 value'].to_list()[1]),
                    'Th_cal': float(df_temp['Component_3 value'].to_list()[2]),
                })
                continue

            # Case 2: measurement_id WAS recorded, but no matching assay data found
            if df_temp.empty:
                row_stats[idx] = None
                continue

            k = df_temp['Component_1 value'].astype('float16')
            u = df_temp['Component_2 value'].astype('float16')
            th = df_temp['Component_3 value'].astype('float16')
            row_stats[idx] = {
                'K_mean': k.mean(), 'K_median': k.median(), 'K_max': k.max(), 'K_min': k.min(), 'K_std': k.std(),
                'U_mean': u.mean(), 'U_median': u.median(), 'U_max': u.max(), 'U_min': u.min(), 'U_std': u.std(),
                'Th_mean': th.mean(), 'Th_median': th.median(), 'Th_max': th.max(), 'Th_min': th.min(), 'Th_std': th.std(),
            }

        df_proc = pd.DataFrame(index=df_record.index, columns=GAMMA_STAT_COLS, dtype=object)
        for idx, stats in row_stats.items():
            if stats is None:
                df_proc.loc[idx, :] = 'missing'
            else:
                df_proc.loc[idx, GAMMA_STAT_COLS] = [stats[c] for c in GAMMA_STAT_COLS]

        df_proc.insert(0, 'sample id', df_record['sample_id'].astype(str).values)

        df_cal = pd.DataFrame(cal_results)

        df_final = df_proc.reset_index(drop=True)
        df_final = find_missing_list_indices(df_final, 'sample id', sample_id_report)

        return df_final, df_cal