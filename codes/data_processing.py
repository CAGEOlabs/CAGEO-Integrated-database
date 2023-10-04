import numpy as np
import pandas as pd
# import matplotlib.pyplot as plt
# from openpyxl import Workbook
# from openpyxl import load_workbook
import glob
import os
import chardet


class dataprocess:
    
    def cond_sus_proc(self,prop):

        data_inventory = pd.read_excel(self.path_to_report, sheet_name = None)
        df_record = data_inventory.get(prop)

        os.chdir(f'{self.drillhole}/cond_sus')


        dic_result = {'sample id':[],'mean':[], 'std':[],'median':[], 'max':[],'min':[]} ## creating dataframe for results #######


        for dir in os.listdir():
            os.chdir(dir+'/'+'kt20_0385')

            try:
                meta_data = pd.read_csv('kappa_sigma_0385.csv')
                df_record_sub = df_record[df_record['measurement_id'].isin(meta_data['Record_Id'])]
                
            except KeyError:
                meta_data = pd.read_csv('kappa_sigma_0385.csv',sep=';')
                df_record_sub = df_record[df_record['measurement_id'].isin(meta_data['Record_Id'])]

                                        
                                        
            record_id_list_sub = df_record_sub['measurement_id'].tolist()
            record_id_strings_sub = [str(record_id) for record_id in record_id_list_sub] 
            sample_id_sub = df_record_sub['sample_id'].tolist()
            sample_id_strings_sub = [str(sample_id) for sample_id in sample_id_sub]

            for i in range(len(record_id_strings_sub)):
                os.chdir(str(record_id_strings_sub[i]))   #### changing directory iteratively##########
                file = glob.glob('*.csv')
                df = pd.read_csv(file[0])    
                a1 = df.index[df['Date'] == 'Min'].to_list()
                a1 = int(np.array(a1))
                d1 = np.array(df.iloc[2:a1,1])
                d1 = d1.astype('float32')
                d1 = np.reshape(d1, (a1-2,1))
                w1 = np.ma.masked_outside(d1,np.mean(d1)+(2*np.std(d1)),np.mean(d1)-(2*np.std(d1)))
                dic_result['sample id'].append(sample_id_strings_sub[i]),dic_result['mean'].append(np.mean(w1)),dic_result['std'].append(np.std(w1)),dic_result['median'].append(np.median(w1)),dic_result['max'].append(np.max(w1)),dic_result['min'].append(np.min(w1))
                os.chdir(os.path.normpath(os.getcwd() + os.sep + os.pardir))
                # print(os.getcwd())
            os.chdir(os.path.normpath(os.getcwd() + os.sep + os.pardir+os.sep + os.pardir))

        os.chdir(os.path.normpath(os.getcwd() + os.sep + os.pardir + os.sep + os.pardir))

        df_proc = pd.DataFrame(dic_result)

        sample_id = df_record['sample_id']
        nan_indices = df_record[df_record['measurement_id'].isna()].index

        dic_nan = {str(i) : ['no_data'] for i in df_proc.columns}
        df_nan = pd.DataFrame(dic_nan)

        
        for index in nan_indices:
            df_proc = pd.concat([df_proc.iloc[:index], df_nan, df_proc.iloc[index:]]).reset_index(drop=True)
        result_df = df_proc.reset_index(drop=True)

        result_df.iloc[:,0] = (sample_id).astype(str)
        cal = result_df['sample id'].str.contains('cal')
        df_cal = result_df[cal]
        df_final = result_df[np.logical_not(cal)]
        df_final.index = range(len(df_final))

        return df_final,df_cal


    def gamma(self):     
    
        dict = pd.read_excel(self.path_to_report, sheet_name = None)
        df_record = dict.get('gamma') 
        
        os.chdir(f'{self.drillhole}/gamma')

        # measurement_id_array = np.c_[df_record['measurement_id1'],df_record['measurement_id2'],df_record['measurement_id3']]
        dic_result = {'sample id':[],'K_mean':[],'K_median':[], 'K_max':[],'K_min':[], 'K_std':[],'U_mean':[],'U_median':[], 
                    'U_max':[],'U_min':[], 'U_std':[],'Th_mean':[],'Th_median':[], 'Th_max':[],'Th_min':[], 'Th_std':[]}

        for dir in os.listdir():
            os.chdir(f'{dir}/gt40_0154/assay')

            # file_record = glob.glob('*.xlsx')
            # df_record = pd.read_excel(file_record[0])

            file_assay = glob.glob('*.csv')
            assay = pd.read_csv(file_assay[0],sep=';')
            df_assay = assay[assay['Id'].notna()]
            df_record_sub = df_record[df_record['measurement_id1'].isin(df_assay['Id']) + 
                                    df_record['measurement_id2'].isin(df_assay['Id']) + df_record['measurement_id3'].isin(df_assay['Id'])]
            sampleid = np.array(df_record_sub['sample_id'])
            measurement_id_array = np.c_[df_record_sub['measurement_id1'],df_record_sub['measurement_id2'],df_record_sub['measurement_id3']] 

            
            for i in range (len(df_record_sub)):
                measurement_id_temp = measurement_id_array[i,:].tolist()
                df_temp = df_assay[df_assay['Id'].isin(measurement_id_temp)]
                df_temp.replace('<  0.00000', '0', inplace=True)
                dic_result['sample id'].append(str(sampleid[i])),dic_result['K_mean'].append(df_temp['Component_1 value'].astype('float16').mean()),
                dic_result['K_median'].append(df_temp['Component_1 value'].astype('float16').median()),dic_result['K_max'].append(df_temp['Component_1 value'].astype('float16').max()),
                dic_result['K_min'].append(df_temp['Component_1 value'].astype('float16').min()),dic_result['K_std'].append(df_temp['Component_1 value'].astype('float16').std()),
                dic_result['U_mean'].append(df_temp['Component_2 value'].astype('float16').mean()),dic_result['U_median'].append(df_temp['Component_2 value'].astype('float16').median()),
                dic_result['U_max'].append(df_temp['Component_2 value'].astype('float16').max()),dic_result['U_min'].append(df_temp['Component_2 value'].astype('float16').min()),
                dic_result['U_std'].append(df_temp['Component_2 value'].astype('float16').std()),
                dic_result['Th_mean'].append(df_temp['Component_3 value'].astype('float16').mean()),dic_result['Th_median'].append(df_temp['Component_3 value'].astype('float16').median()),
                dic_result['Th_max'].append(df_temp['Component_3 value'].astype('float16').max()),dic_result['Th_min'].append(df_temp['Component_3 value'].astype('float16').min()),dic_result['Th_std'].append(df_temp['Component_3 value'].astype('float16').std())

        

            os.chdir(os.path.normpath(os.getcwd() + os.sep + os.pardir + os.sep + os.pardir + os.sep + os.pardir))   

        os.chdir(os.path.normpath(os.getcwd() + os.sep + os.pardir+os.sep + os.pardir))

        df_proc = pd.DataFrame(dic_result)

        sample_id = df_record['sample_id']
        nan_indices = df_record[df_record['measurement_id1'].isna()].index
        dic_nan = {str(i) : ['no_data'] for i in df_proc.columns}
        df_nan = pd.DataFrame(dic_nan)

        for index in nan_indices:
            df_proc = pd.concat([df_proc.iloc[:index], df_nan, df_proc.iloc[index:]]).reset_index(drop=True)
        result_df = df_proc.reset_index(drop=True)

        result_df.iloc[:,0] = (sample_id).astype(str)
        cal = result_df['sample id'].str.contains('cal')
        df_cal = result_df[cal]
        df_final = result_df[np.logical_not(cal)]
        df_final.index = range(len(df_final))

        return df_final,df_cal
    
    
    def density(self):
    
        dict = pd.read_excel(self.path_to_report, sheet_name = None)
        df_den = dict.get('den') 
        df_out = pd.concat([df_den['sample_id'],df_den['density']],axis=1)
        df_out.rename(columns={'sample_id': 'sample id'}, inplace=True)

        return df_out
    
    def ip_res(self):

        data_inventory = pd.read_excel(self.path_to_report, sheet_name = None)
        df_record = data_inventory.get('ip_res')
        sample_id = df_record['sample_id']

        # meas_id_prop = df_record['measurement_id'].tolist()

        os.chdir(f'{self.drillhole}/ip_res')

        df_proc = pd.DataFrame()
        
        for dir in os.listdir():
            os.chdir(dir+'/'+'kt20_0385'+'/'+'ip')
            ip_record = pd.read_csv('ip_records.csv')
            df_proc = pd.concat([df_proc, ip_record], ignore_index=True)

            os.chdir(os.path.normpath(os.getcwd() + os.sep + os.pardir+os.sep + os.pardir+os.sep + os.pardir))

        os.chdir(os.path.normpath(os.getcwd() + os.sep + os.pardir + os.sep + os.pardir))

        nan_indices = df_record[df_record['measurement_id'].isna()].index

        dic_nan = {str(i) : ['no_data'] for i in df_proc.columns}
        df_nan = pd.DataFrame(dic_nan)

        
        for index in nan_indices:
            df_proc = pd.concat([df_proc.iloc[:index], df_nan, df_proc.iloc[index:]]).reset_index(drop=True)
        result_df = df_proc.reset_index(drop=True)

        result_df.iloc[:,0] = (sample_id).astype(str)
        result_df.rename(columns={'Record_Id': 'sample id'}, inplace=True)
        cal = result_df['sample id'].str.contains('cal')
        df_cal = result_df[cal]
        df_final = result_df[np.logical_not(cal)]
        df_final.index = range(len(df_final))

        return df_final,df_cal
    
    def convert_csv_to_utf8(self, input_file):
        with open(input_file, 'rb') as f:
            enc = chardet.detect(f.read())

        if enc['encoding'].lower() == 'utf-8':
            print(f"The file {input_file} is already in UTF-8 encoding.")
        else:
            # Use a temporary DataFrame to read the CSV with the detected encoding
            df = pd.read_csv(input_file, encoding=enc['encoding'])
            
            # Save the DataFrame with UTF-8 encoding
            output_file = input_file.replace('.csv', '_utf8.csv')
            df.to_csv(output_file, encoding='utf-8', sep=',',index=False)
            print(f"File converted and saved as {output_file}")
    
    def vel(self,prop):

        data_inventory = pd.read_excel(self.path_to_report, sheet_name = None)
        df_record = data_inventory.get(prop)
        sample_id = df_record['sample_id']

        os.chdir(f'{self.drillhole}/{prop}')

        df_proc = pd.DataFrame()

        for dir in os.listdir():
            os.chdir(dir)

            self.convert_csv_to_utf8('Punditlink Data.csv')

            file = glob.glob('*.csv')

            rawdata = open(file[len(file)-1], 'rb').read()
            enc = chardet.detect(rawdata)
            # df = pd.read_csv(list1[0],sep='	', encoding = enc['encoding'],header = 14)

            try:
                df_data = pd.read_csv(file[len(file)-1],sep=',', encoding = enc['encoding'],header = 14)
                df_data.columns = df_data.columns.str.strip()
                record_id = df_data['ID']
                a=[]
                for i in range(1,len(df_data),25):
                    a.append(i)

            except KeyError:
                df_data = pd.read_csv(file[len(file)-1],sep='\t', encoding = enc['encoding'],header = 10)
                df_data.columns = df_data.columns.str.strip()
                record_id = df_data['ID']
                a=[]
                for i in range(1,len(df_data),16):
                    a.append(i)
    
            df_vel = df_data.iloc[a]
            df_proc = pd.concat([df_proc, df_vel], ignore_index=True)
            os.chdir(os.path.normpath(os.getcwd() + os.sep + os.pardir))

        os.chdir(os.path.normpath(os.getcwd() + os.sep + os.pardir + os.sep + os.pardir))

        nan_indices = df_record[df_record['measurement_id'].isna()].index

        dic_nan = {str(i) : ['no_data'] for i in df_proc.columns}
        df_nan = pd.DataFrame(dic_nan)

        
        for index in nan_indices:
            df_proc = pd.concat([df_proc.iloc[:index], df_nan, df_proc.iloc[index:]]).reset_index(drop=True)
        result_df = df_proc.reset_index(drop=True)

    
        result_df.iloc[:,0] = (sample_id).astype(str)
        result_df.rename(columns={'ID': 'sample id'}, inplace=True)
        cal = result_df['sample id'].str.contains('cal')
        df_cal = result_df[cal]
        df_final = result_df[np.logical_not(cal)]
        df_final.index = range(len(df_final))

        return df_final
    

    def extract_last_four_digits(self,number):
        return float(number[-4:])


    
    def xrf(self):
        
        os.chdir(f'{self.drillhole}/xrf')  

        
        df_proc = pd.DataFrame()

        for dir in os.listdir():
            os.chdir(dir)
            file = glob.glob('*.csv')
            try:
                df_xrf = pd.read_csv(file[len(file)-1],skiprows=1)
                info = df_xrf['info']
            except KeyError:
                df_xrf = pd.read_csv(file[len(file)-1])
                info = df_xrf['info']
            except KeyError:
                df_xrf = pd.read_csv(file[len(file)-1],sep=';')
                info = df_xrf['info']
            except KeyError:
                df_xrf = pd.read_csv(file[len(file)-1],sep=',')
                info = df_xrf['info']
               
                
            os.chdir(os.path.normpath(os.getcwd() + os.sep + os.pardir))
            df_proc = pd.concat([df_proc, df_xrf], ignore_index=True)

        info = df_proc['info'].tolist()
        
        i = 0
        drop_list = []

        while i < len(info):
            if isinstance(info[i], str) and info[i].startswith('cal'):
                drop_list.append(i)
            if isinstance(info[i], str) and info[i].startswith('std'):
                drop_list.append(i)
            if isinstance(info[i], str) and info[i].startswith('blk'):
                drop_list.append(i)
            i += 1
        # print(drop_list)
        new_df = df_proc.drop(df_proc.index[drop_list])

        # display(new_df)

        new_df.reset_index(inplace = True)
        new_info = new_df['info'].tolist()
        sampleid_list = []
        # delete the last letter of info
        for temp_info in new_info:
            sampleid = str(temp_info)[:-1]
            sampleid_list.append(sampleid)
        # delete NaN & abcdef columns
        new_df['info']=sampleid_list
        new_df = new_df.dropna(axis=1, how='all') #drop all rows that have any NaN values
        new_df =new_df.drop( ['Instrument Serial Num','Reading #','Date','Time','Method Name','Test Label','Collimation Status','Units'],axis=1)
        # delete 'errors' columns
        new_df1=new_df.filter(regex='Error')
        new_df2=new_df.filter(regex='User')
        # new_df1=new_df.filter(regex='Compound')
        new_df = new_df.drop(new_df1,axis=1)
        new_df = new_df.drop(new_df2,axis=1)
        new_df = new_df.replace('<LOD','0.0')
        new_df = new_df.replace('na',np.NaN)
        new_df = new_df.replace('de',np.NaN)

        new_df = pd.concat([new_df.iloc[:, :-1].apply(np.float64),new_df['info']],axis=1)
        new_df['temp_info'] = new_df['info'].apply(self.extract_last_four_digits)

        new_df1 = new_df.groupby(['temp_info'])[['Mg Concentration','Al Concentration','Si Concentration','P Concentration','S Concentration','K Concentration','Ca Concentration','Ti Concentration','V Concentration','Cr Concentration','Mn Concentration','Fe Concentration','Mg Concentration','Co Concentration','Ni Concentration','Cu Concentration','Zn Concentration','As Concentration','Se Concentration','Rb Concentration','Sr Concentration','Y Concentration','Zr Concentration','Nb Concentration','Mo Concentration','Ag Concentration','Cd Concentration','Sn Concentration','Sb Concentration','W Concentration','Au Concentration','Hg Concentration','Pb Concentration','Bi Concentration','Th Concentration','U Concentration','LE Concentration']].mean().reset_index()
        new_df2 = new_df.groupby(['temp_info'])[['Mg Concentration','Al Concentration','Si Concentration','P Concentration','S Concentration','K Concentration','Ca Concentration','Ti Concentration','V Concentration','Cr Concentration','Mn Concentration','Fe Concentration','Mg Concentration','Co Concentration','Ni Concentration','Cu Concentration','Zn Concentration','As Concentration','Se Concentration','Rb Concentration','Sr Concentration','Y Concentration','Zr Concentration','Nb Concentration','Mo Concentration','Ag Concentration','Cd Concentration','Sn Concentration','Sb Concentration','W Concentration','Au Concentration','Hg Concentration','Pb Concentration','Bi Concentration','Th Concentration','U Concentration','LE Concentration']].std().reset_index()
        new_df3 = new_df.groupby(['temp_info'])[['Mg Concentration','Al Concentration','Si Concentration','P Concentration','S Concentration','K Concentration','Ca Concentration','Ti Concentration','V Concentration','Cr Concentration','Mn Concentration','Fe Concentration','Mg Concentration','Co Concentration','Ni Concentration','Cu Concentration','Zn Concentration','As Concentration','Se Concentration','Rb Concentration','Sr Concentration','Y Concentration','Zr Concentration','Nb Concentration','Mo Concentration','Ag Concentration','Cd Concentration','Sn Concentration','Sb Concentration','W Concentration','Au Concentration','Hg Concentration','Pb Concentration','Bi Concentration','Th Concentration','U Concentration','LE Concentration']].median().reset_index()
        new_df4 = new_df.groupby(['temp_info'])[['Mg Concentration','Al Concentration','Si Concentration','P Concentration','S Concentration','K Concentration','Ca Concentration','Ti Concentration','V Concentration','Cr Concentration','Mn Concentration','Fe Concentration','Mg Concentration','Co Concentration','Ni Concentration','Cu Concentration','Zn Concentration','As Concentration','Se Concentration','Rb Concentration','Sr Concentration','Y Concentration','Zr Concentration','Nb Concentration','Mo Concentration','Ag Concentration','Cd Concentration','Sn Concentration','Sb Concentration','W Concentration','Au Concentration','Hg Concentration','Pb Concentration','Bi Concentration','Th Concentration','U Concentration','LE Concentration']].max().reset_index()
        new_df5 = new_df.groupby(['temp_info'])[['Mg Concentration','Al Concentration','Si Concentration','P Concentration','S Concentration','K Concentration','Ca Concentration','Ti Concentration','V Concentration','Cr Concentration','Mn Concentration','Fe Concentration','Mg Concentration','Co Concentration','Ni Concentration','Cu Concentration','Zn Concentration','As Concentration','Se Concentration','Rb Concentration','Sr Concentration','Y Concentration','Zr Concentration','Nb Concentration','Mo Concentration','Ag Concentration','Cd Concentration','Sn Concentration','Sb Concentration','W Concentration','Au Concentration','Hg Concentration','Pb Concentration','Bi Concentration','Th Concentration','U Concentration','LE Concentration']].min().reset_index()
        new_df1.columns = new_df1.columns.str.replace('Concentration', 'Mean')
        # new_df1.columns = new_df1.replace('Concentration', 'Mean')
        new_df2.columns = new_df2.columns.str.replace('Concentration', 'Std')
        new_df3.columns = new_df3.columns.str.replace('Concentration', 'Median')
        new_df4.columns = new_df4.columns.str.replace('Concentration', 'Max')
        new_df5.columns = new_df5.columns.str.replace('Concentration', 'Min')
        new_df6 = pd.concat([new_df1,new_df2,new_df3,new_df4,new_df5],axis=1)
        new_df7 = new_df6.sort_index(axis=1)
        new_df7 = new_df7.loc[:, ~new_df7.columns.duplicated()]
        new_df7 = new_df7.iloc[:, :-1]
        new_df7['info']=np.unique(sampleid_list)
        df_final = new_df7 
        
        df_final.rename(columns={'info': 'sample id'}, inplace=True)

        os.chdir(os.path.normpath(os.getcwd() + os.sep + os.pardir+ os.sep + os.pardir))

        return df_final
    
   
    
        