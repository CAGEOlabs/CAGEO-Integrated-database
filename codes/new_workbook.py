import numpy as np
import pandas as pd
# import matplotlib.pyplot as plt
from openpyxl import Workbook
from openpyxl import load_workbook
from codes.data_processing import dataprocess
import glob
import os

class database(dataprocess):

    def __init__(self,drillhole):
        self.drillhole = drillhole
        self.path_to_database = f'{drillhole}/{drillhole}_integrated_database.xlsx'
        self.path_to_report = f'{self.drillhole}/{self.drillhole}_sample_report.xlsx'
# create and save the spreadsheet
    def createworkbook(self):
        workbook = Workbook()
        workbook.save(self.path_to_database)
# add property lists   
    def add_sheets(self,property_list):
        workbook = load_workbook(self.path_to_database)
        for property in property_list:
            workbook.create_sheet(property)
        workbook.save(self.path_to_database)
#  copy the whole sample report to database
    def copy_sheet_columns(self, property_sheet, sample_report):
        maxr = sample_report.max_row
        maxc = sample_report.max_column
        for r in range (1, maxr + 1):
           for c in range (1, maxc + 1):
              property_sheet.cell(row=r,column=c).value = sample_report.cell(row=r,column=c).value

    def copy_col_for_all_sheets(self,common_column_property_sheet):
        report = load_workbook(self.path_to_report)
        sample_report = report.active = report['sample_report']
        for property in common_column_property_sheet:
                workbook = load_workbook(self.path_to_database)
                db_sheet = workbook.active = workbook[property]
                self.copy_sheet_columns(db_sheet, sample_report)
                workbook.save(self.path_to_database)
# select and process properties
    def select_and_process(self,property):
        if property == 'cond':
            df_proc,df_cal = self.cond_sus_proc('cond')
            df_cal_new =  df_cal.rename(columns={"mean": "cond mean", "std": "cond std", "median": "cond median", "max": "cond max", "min": "cond min"},)
            return df_proc,df_cal_new
        elif property == 'sus':
            df_proc,df_cal = self.cond_sus_proc('sus')
            df_cal_new =  df_cal.rename(columns={"mean": "sus mean", "std": "sus std", "median": "sus median", "max": "sus max", "min": "sus min"},)
            return df_proc,df_cal_new
        elif property == 'gamma':
            return self.gamma()
        elif property == 'den':
            df_proc,df_cal = self.density()
            df_cal_new =  df_cal[['sample id','density']]
            return df_proc,df_cal_new
        elif property == 'ip_res':
            df_proc,df_cal = self.ip_res()
            df_cal_new =  df_cal[['sample id','Resistance[ohm]']]
            df_cal_new1 =  df_cal_new.rename(columns={"Resistance[ohm]": "ip res[ohm]"},)
            return df_proc,df_cal_new1
            # return self.ip_res()
        elif property == 'v_p':
            df_proc,df_cal = self.vel('v_p')
            return df_proc,df_cal
        elif property == 'v_s':
            df_proc,df_cal = self.vel('v_p')
            return df_proc,df_cal
        elif property == 'xrf':
            df_proc,df_cal = self.xrf()
            # df_cal_new =  df_cal.rename(columns={"mean": "cond mean", "std": "cond std", "median": "cond median", "max": "cond max", "min": "cond min"},)
            return df_proc,df_cal
            # return self.xrf()
        
# write all of the properties        
    def add_data(self,property):

      
        df_proc,df_cal = self.select_and_process(property)
        
        int_data = pd.read_excel(self.path_to_database, sheet_name = None)
        sheet_prop = int_data.get(property)
        df_proc = df_proc.drop(['sample id'], axis=1)
        column_list = df_proc.columns # column_list: ['mean', 'std', 'median', 'max', 'min']

        for column in column_list:
            sheet_prop[column] = df_proc[column] # sheet_prop: [hole_id sample_id depth_from depth_to mean std median max min]

        with pd.ExcelWriter(self.path_to_database, mode ='a',engine = 'openpyxl', if_sheet_exists='replace') as writer:
            sheet_prop.to_excel(writer, sheet_name=property, index = False)

        
  
####### write cal
    def add_cal(self,prop_list):
        # df_sampid = data.groupby(by='sample id', as_index=False).max()

        # data_sampid = pd.merge(data['sample id'], how='left')

        df_cal1 = pd.DataFrame()

        for prop in prop_list:
            _,df_cal = self.select_and_process(prop)
            df_cal.reset_index(drop=True, inplace=True)
            df_cal1 = pd.concat([df_cal, df_cal1],axis=1, join='outer')
        df_cal1 = df_cal1.loc[:,~df_cal1.columns.duplicated()].copy()

        with pd.ExcelWriter(self.path_to_database, mode ='a',engine = 'openpyxl', if_sheet_exists='replace') as writer:
            df_cal1.to_excel(writer, sheet_name="cal", index = False)



 

    



       
           
    


       

        











