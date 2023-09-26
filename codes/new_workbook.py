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

    def createworkbook(self):
        workbook = Workbook()
        workbook.save(self.path_to_database)
   
    def add_sheets(self,property_list):
        workbook = load_workbook(self.path_to_database)
        for property in property_list:
            workbook.create_sheet(property)
        workbook.save(self.path_to_database)
    
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
    
    def select_and_process(self,property):
        if property == 'cond':
            return self.cond_sus_proc('cond')
        elif property == 'sus':
            return self.cond_sus_proc('sus')
        elif property == 'gamma':
            return self.gamma()
        elif property == 'den':
            return self.density()
        elif property == 'ip_res':
            return self.ip_res()
        elif property == 'v_p':
            return self.vel('v_p')
        elif property == 'v_s':
            return self.vel('v_s')
        elif property == 'xrf':
            return self.xrf()
        
        
    def add_data(self,property):

        if property in ['den','v_p','v_s','xrf']:
            df_proc = self.select_and_process(property)
        else:
            df_proc,df_cal = self.select_and_process(property)

        int_data = pd.read_excel(self.path_to_database, sheet_name = None)
        sheet_prop = int_data.get(property)
        df_proc = df_proc.drop(['sample id'], axis=1)
        column_list = df_proc.columns 

        for column in column_list:
            sheet_prop[column] = df_proc[column]

        with pd.ExcelWriter(self.path_to_database, mode ='a',engine = 'openpyxl', if_sheet_exists='replace') as writer:
            sheet_prop.to_excel(writer, sheet_name=property, index = False)



       
            
    


       

        











