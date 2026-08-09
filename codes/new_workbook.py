import re
import numpy as np
import pandas as pd
from openpyxl import Workbook
from openpyxl import load_workbook
from codes.data_processing import dataprocess
import glob
import os


def _extract_cal_number(sample_id):
    """Extract the integer following any digits in a calibration sample id
    string (e.g. 'cal_012' -> 12, 'std7' -> 7). Returns None if no digits
    are found."""
    match = re.search(r'\d+', str(sample_id))
    return int(match.group()) if match else None


class database(dataprocess):

    def __init__(self, drillhole):
        self.drillhole = drillhole
        self.path_to_database = f'{drillhole}/{drillhole}_integrated_database.xlsx'
        self.path_to_report = f'{self.drillhole}/{self.drillhole}_sample_report.xlsx'

    # -- workbook setup --------------------------------------------------

    def createworkbook(self):
        """Create and save a fresh (empty) integrated database workbook."""
        workbook = Workbook()
        workbook.save(self.path_to_database)

    def add_sheets(self, property_list):
        """Add one empty sheet per property name in `property_list`."""
        workbook = load_workbook(self.path_to_database)
        for prop in property_list:
            workbook.create_sheet(prop)
        workbook.save(self.path_to_database)

    def copy_sheet_columns(self, property_sheet, sample_report):
        """Copy every cell from `sample_report` into `property_sheet`, verbatim."""
        maxr = sample_report.max_row
        maxc = sample_report.max_column
        for r in range(1, maxr + 1):
            for c in range(1, maxc + 1):
                property_sheet.cell(row=r, column=c).value = sample_report.cell(row=r, column=c).value

    def copy_col_for_all_sheets(self, common_column_property_sheet):
        """Seed every listed property sheet with a full copy of sample_report."""
        report = load_workbook(self.path_to_report)
        sample_report = report.active = report['sample_report']
        for prop in common_column_property_sheet:
            workbook = load_workbook(self.path_to_database)
            db_sheet = workbook.active = workbook[prop]
            self.copy_sheet_columns(db_sheet, sample_report)
            workbook.save(self.path_to_database)

    # -- dispatch to the right processing method --------------------------

    def select_and_process(self, prop):
        if prop == 'cond':
            df_proc, df_cal = self.cond_sus_proc('cond')
            df_cal = df_cal.rename(columns={
                "mean": "cond mean", "std": "cond std",
                "median": "cond median", "max": "cond max", "min": "cond min",
            })
            return df_proc, df_cal

        elif prop == 'sus':
            df_proc, df_cal = self.cond_sus_proc('sus')
            df_cal = df_cal.rename(columns={
                "mean": "sus mean", "std": "sus std",
                "median": "sus median", "max": "sus max", "min": "sus min",
            })
            return df_proc, df_cal

        elif prop == 'gamma':
            return self.gamma()

        elif prop == 'den':
            df_proc, df_cal = self.density()
            df_cal = df_cal[['sample id', 'density']]
            return df_proc, df_cal

        elif prop == 'ip_res':
            df_proc, df_cal = self.ip_res()
            df_cal = df_cal[['sample id', 'Resistance[ohm]']]
            df_cal = df_cal.rename(columns={"Resistance[ohm]": "ip res[ohm]"})
            return df_proc, df_cal

        elif prop == 'v_p':
            df_proc, df_cal = self.vel('v_p')
            return df_proc, df_cal

        elif prop == 'v_s':
            df_proc, df_cal = self.vel('v_s')
            return df_proc, df_cal

        elif prop == 'xrf':
            df_proc, df_cal = self.xrf()
            return df_proc, df_cal

        else:
            raise ValueError(f"Unknown property '{prop}'")

    # -- write processed data into the database ---------------------------

    def add_data(self, prop):
        df_proc, df_cal = self.select_and_process(prop)

        int_data = pd.read_excel(self.path_to_database, sheet_name=None)
        sheet_prop = int_data.get(prop)
        if sheet_prop is None:
            raise ValueError(f"Sheet '{prop}' not found in {self.path_to_database}")

        # Guard against silent misalignment: sheet_prop was seeded from
        # sample_report row order (via copy_col_for_all_sheets), and df_proc
        # is aligned to sample_report via find_missing_list_indices -- both
        # are expected to already be the same length and order. Verify that
        # explicitly rather than assuming it and assigning columns blind.
        if len(sheet_prop) != len(df_proc):
            raise ValueError(
                f"Row count mismatch writing '{prop}': database sheet has "
                f"{len(sheet_prop)} rows, processed data has {len(df_proc)} rows."
            )

        if 'sample_id' in sheet_prop.columns and 'sample id' in df_proc.columns:
            expected_key = sheet_prop['sample_id'].astype(str).str[-4:]
            actual_key = df_proc['sample id'].astype(str).str[-4:]
            mismatch = expected_key.values != actual_key.values
            if mismatch.any():
                bad_rows = sheet_prop.loc[mismatch, 'sample_id'].tolist()
                raise ValueError(
                    f"Sample id mismatch writing '{prop}' at row(s) with "
                    f"sample_id: {bad_rows} -- refusing to write misaligned data."
                )

        df_proc = df_proc.drop(columns=['sample id'])

        for column in df_proc.columns:
            sheet_prop[column] = df_proc[column].values

        with pd.ExcelWriter(self.path_to_database, mode='a', engine='openpyxl', if_sheet_exists='replace') as writer:
            sheet_prop.to_excel(writer, sheet_name=prop, index=False)

    # -- write calibration data ---------------------------------------------

    def add_cal(self, prop_list):
        """
        Combine each property's calibration subset into a single 'cal'
        sheet, with 'sample id' as the leftmost column, labeled 'cal_<n>'.

        The sheet covers every calibration number from the lowest to the
        highest seen across ALL properties in prop_list -- so a property
        with fewer measured standards (e.g. cond might only go up to
        cal_16) doesn't truncate the sheet relative to one with more (e.g.
        xrf might go up to cal_73); rows beyond a property's own range are
        simply NaN for that property's columns.

        Properties can use different raw naming/padding conventions for
        calibration ids (confirmed: e.g. 'cal_001'..'cal_017' vs
        'cal_00'..'cal_073' depending on drillhole). Rather than trying to
        reconcile those string formats, every property's calibration id is
        reduced to its extracted integer, and everything is merged on that
        integer. The final sheet always shows the canonical 'cal_<n>'
        label (unpadded), regardless of what format any source property
        originally used.
        """
        numbered_frames = []
        all_numbers = []

        for prop in prop_list:
            _, df_cal = self.select_and_process(prop)
            df_cal = df_cal.reset_index(drop=True)

            numbers = df_cal['sample id'].apply(_extract_cal_number)
            df_cal = df_cal.drop(columns=['sample id'])
            df_cal.insert(0, '_cal_number', numbers)
            df_cal = df_cal.dropna(subset=['_cal_number'])
            df_cal['_cal_number'] = df_cal['_cal_number'].astype(int)

            if not df_cal.empty:
                all_numbers.extend(df_cal['_cal_number'].tolist())

            numbered_frames.append(df_cal)

        if not all_numbers:
            df_cal_combined = pd.DataFrame(columns=['sample id'])
        else:
            lo, hi = min(all_numbers), max(all_numbers)
            df_cal_combined = pd.DataFrame({'_cal_number': range(lo, hi + 1)})

            for df_cal in numbered_frames:
                df_cal_combined = df_cal_combined.merge(df_cal, on='_cal_number', how='left')

            df_cal_combined.insert(0, 'sample id', 'cal_' + df_cal_combined['_cal_number'].astype(str))
            df_cal_combined = df_cal_combined.drop(columns=['_cal_number'])

        with pd.ExcelWriter(self.path_to_database, mode='a', engine='openpyxl', if_sheet_exists='replace') as writer:
            df_cal_combined.to_excel(writer, sheet_name="cal", index=False)