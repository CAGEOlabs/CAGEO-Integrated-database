import numpy as np
import pandas as pd
import glob
import os
import chardet
from datetime import datetime
import re

class dataprocess:
    
    def cond_sus_proc(self,prop):

        data_inventory = pd.read_excel(self.path_to_report, sheet_name = None)
        df_record = data_inventory.get(prop)
        df_report = data_inventory.get('sample_report') 
        sample_id_report = df_report['sample_id'].to_list()

        os.chdir(f'{self.drillhole}/cond_sus')


        dic_result = {'sample id':[],'mean':[], 'std':[],'median':[], 'max':[],'min':[]} ## creating dataframe for results #######


        date_objects = [datetime.strptime(date_str, "%d-%m-%y") for date_str in os.listdir()]

        # Sort the list based on datetime objects
        sorted_folder_names = [date.strftime("%d-%m-%y") for date in sorted(date_objects)]

        
        for dir in sorted_folder_names:
            os.chdir(dir+'/'+'kt20_0385')

            try:
                meta_data = pd.read_csv('kappa_sigma_0385.csv')
                df_record_sub = df_record[df_record['measurement_id'].isin(meta_data['Record_Id'])]
                
            except KeyError:
                meta_data = pd.read_csv('kappa_sigma_0385.csv',sep=';')
                df_record_sub = df_record[df_record['measurement_id'].isin(meta_data['Record_Id'])]

                                    
            record_id_list_sub = df_record_sub['measurement_id'].tolist()
            record_id_strings_sub = [str(int(record_id)) for record_id in record_id_list_sub] 
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

        dic_nan = {str(i) : ['nan'] for i in df_proc.columns}
        df_nan = pd.DataFrame(dic_nan)

        
        for index in nan_indices:
            df_proc = pd.concat([df_proc.iloc[:index], df_nan, df_proc.iloc[index:]]).reset_index(drop=True)
        result_df = df_proc.reset_index(drop=True)

        # result_df.iloc[:,0] = (sample_id).astype(str)
        cal = result_df['sample id'].str.contains('cal')
        df_cal = result_df[cal]
        df_final = result_df[np.logical_not(cal)]
        df_final.index = range(len(df_final))
        df_final = self.find_missing_list_indices(df_final,'sample id',sample_id_report)

        return df_final,df_cal
    
    def find_missing_list_indices(self,dataframe, column_name, value_list):

        nan_ind = dataframe[dataframe[column_name] == 'nan'].index

        dataframe.drop(nan_ind,inplace=True)

        int_df_sample_id = [int(str(x)[-4:]) for x in dataframe[column_name].tolist()]

        int_value_list = [int(str(x)[-4:]) for x in value_list]

        indices = [index for index, value in enumerate(int_value_list) if value not in int_df_sample_id]

        dic_err = {str(i) : ['error'] for i in dataframe.columns}
        df_err = pd.DataFrame(dic_err)
        
        for index in indices:
            dataframe = pd.concat([dataframe.iloc[:index], df_err, dataframe.iloc[index:]]).reset_index(drop=True)
        result_df = dataframe.reset_index(drop=True)

        result_df.iloc[nan_ind,:] = 'nan'
        
        return result_df


    def gamma(self):     
    
        data_inventory = pd.read_excel(self.path_to_report, sheet_name = None)
        df_record = data_inventory.get('gamma') 
        df_report = data_inventory.get('sample_report') 
        sample_id_report = df_report['sample_id'].to_list()    
        
        os.chdir(f'{self.drillhole}/gamma')

        # measurement_id_array = np.c_[df_record['measurement_id1'],df_record['measurement_id2'],df_record['measurement_id3']]
        dic_result = {'sample id':[],'K_mean':[],'K_median':[], 'K_max':[],'K_min':[], 'K_std':[],'U_mean':[],'U_median':[], 
                    'U_max':[],'U_min':[], 'U_std':[],'Th_mean':[],'Th_median':[], 'Th_max':[],'Th_min':[], 'Th_std':[]}
        
        dic_cal = {'sample id':[],'K_cal':[],'U_cal':[],'Th_cal':[]}

        date_objects = [datetime.strptime(date_str, "%d-%m-%y") for date_str in os.listdir()]

        # Sort the list based on datetime objects
        sorted_folder_names = [date.strftime("%d-%m-%y") for date in sorted(date_objects)]

        
        for dir in sorted_folder_names:
            os.chdir(f'{dir}/gt40_0154/assay')

            # file_record = glob.glob('*.xlsx')
            # df_record = pd.read_excel(file_record[0])
            try:
                file_assay = glob.glob('*.csv')
                assay = pd.read_csv(file_assay[0],sep=';')
                assay.columns = assay.columns.str.strip()
                df_assay = assay[assay['Id'].notna()]
            except KeyError:
                try:
                    file_assay = glob.glob('*.csv')
                    assay = pd.read_csv(file_assay[0],sep=',')
                    assay.columns = assay.columns.str.strip()
                    df_assay = assay[assay['Id'].notna()]
                except KeyError:
                    print('cannot read the .csv file')
            
            df_record_sub = df_record[df_record['measurement_id1'].isin(df_assay['Id']) + 
                                    df_record['measurement_id2'].isin(df_assay['Id']) + df_record['measurement_id3'].isin(df_assay['Id'])]
            sampleid = np.array(df_record_sub['sample_id'])
            measurement_id_array = np.c_[df_record_sub['measurement_id1'],df_record_sub['measurement_id2'],df_record_sub['measurement_id3']] 

            
            for i in range (len(df_record_sub)):
                measurement_id_temp = measurement_id_array[i,:].tolist()
                df_temp = df_assay[df_assay['Id'].isin(measurement_id_temp)]
                df_temp.replace('<  0.00000', '0', inplace=True)


                if str(sampleid[i]).startswith('cal'):
                    
                    dic_cal['sample id'].append(str(sampleid[i])),dic_cal['K_cal'].append(float(df_temp['Component_1 value'].to_list()[0])),dic_cal['U_cal'].append(float(df_temp['Component_2 value'].to_list()[1])),
                    dic_cal['Th_cal'].append(float(df_temp['Component_3 value'].to_list()[2]))

                else:
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
        df_cal = pd.DataFrame(dic_cal)
        # sample_id = df_proc['sample id']

        nan_indices = df_record[df_record['measurement_id1'].isna()].index
        dic_nan = {str(i) : ['nan'] for i in df_proc.columns}
        df_nan = pd.DataFrame(dic_nan)

        for index in nan_indices:
            df_proc = pd.concat([df_proc.iloc[:index], df_nan, df_proc.iloc[index:]]).reset_index(drop=True)
        result_df = df_proc.reset_index(drop=True)

        # result_df.iloc[:,0] = (sample_id).astype(str)

        rem = result_df['sample id'].str.contains('cal')
        # df_rem = result_df[rem]
        df_final = result_df[np.logical_not(rem)]
        df_final.index = range(len(df_final))
        df_final = self.find_missing_list_indices(df_final,'sample id',sample_id_report)

        return df_final,df_cal
    
    
    def density(self):
    
        data_inventory = pd.read_excel(self.path_to_report, sheet_name = None)
        df_report = data_inventory.get('sample_report') 
        sample_id_report = df_report['sample_id']

        df_den = data_inventory.get('den') 
        df_out = pd.concat([df_den['sample_id'],df_den['density']],axis=1)

        df_out.rename(columns={'sample_id': 'sample id'}, inplace=True)

        df_out.iloc[:,0] = (sample_id_report).astype(str)

        cal = df_out['sample id'].str.contains('cal')
        df_cal = df_out[cal]
        df_final = df_out[np.logical_not(cal)]
        df_final.index = range(len(df_final))
        df_final = self.find_missing_list_indices(df_final,'sample id',sample_id_report)

        return df_final,df_cal
    
    
    def ip_res (self):

            data_inventory = pd.read_excel(self.path_to_report, sheet_name = None)
            df_record = data_inventory.get('ip_res')
            sample_id = df_record['sample_id']
            df_record_nan_rem = df_record[~df_record['measurement_id'].isna()]

            os.chdir(f'{self.drillhole}/ip_res')

            df_proc = pd.DataFrame()

            date_objects = [datetime.strptime(date_str, "%d-%m-%y") for date_str in os.listdir()]

            # Sort the list based on datetime objects
            sorted_folder_names = [date.strftime("%d-%m-%y") for date in sorted(date_objects)]

            for i in df_record_nan_rem['measurement_id']:

                    for dir in sorted_folder_names:

                        os.chdir(dir+'/'+'kt20_0385'+'/'+'ip')
                        ip_record = pd.read_csv('ip_records.csv')         
                        df_proc_temp = ip_record[ip_record.Record_Id==i]
                        df_proc = pd.concat([df_proc, df_proc_temp], ignore_index=True)
                        os.chdir(os.path.normpath(os.getcwd() + os.sep + os.pardir+os.sep + os.pardir+os.sep + os.pardir))

            os.chdir(os.path.normpath(os.getcwd() + os.sep + os.pardir + os.sep + os.pardir))

            nan_indices = df_record[df_record['measurement_id'].isna()].index

            dic_nan = {str(i) : ['nan'] for i in df_proc.columns}
            df_nan = pd.DataFrame(dic_nan)

            
            for index in nan_indices:
                df_proc = pd.concat([df_proc.iloc[:index], df_nan, df_proc.iloc[index:]]).reset_index(drop=True)
            result_df = df_proc.reset_index(drop=True)

            result_df[result_df['Record_Id']=='nan']=-1
            proc_meas_id_with_nan = result_df['Record_Id'].to_list()
            df_record[df_record['measurement_id'].isna()]=-1 
            df_rec_meas_id = df_record['measurement_id'].to_list()
            ind_bool_err = []
            for i in df_rec_meas_id:       # df_test has to be the df_record
                ind_bool_err.append(i not in proc_meas_id_with_nan)
            ind_err=[]
            for i in range(len(ind_bool_err)):
                if ind_bool_err[i]==True:
                    ind_err.append(i)
            df_processed_data_with_nan_rem = result_df[result_df['Record_Id']!=-1]

            a = result_df['Record_Id']==-1
            nan_ind=[]
            for i in range(len(a)):
                if a[i]==True:
                    nan_ind.append(i)

            nan_ind.extend(ind_err)
            nan_ind.sort()

            dic_nan = {str(i) : ['nan'] for i in df_processed_data_with_nan_rem.columns}
            df_nan = pd.DataFrame(dic_nan) 
            for index in nan_ind:
                df_processed_data_with_nan_rem = pd.concat([df_processed_data_with_nan_rem.iloc[:index], df_nan,df_processed_data_with_nan_rem.iloc[index:]]).reset_index(drop=True)
            result_df = df_processed_data_with_nan_rem.reset_index(drop=True)

            result_df.iloc[ind_err,:] = 'error'

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
        df_record_nan_rem = df_record[~df_record['measurement_id'].isna()]

        os.chdir(f'{self.drillhole}/{prop}')

        df_proc = pd.DataFrame()

        date_objects = [datetime.strptime(date_str, "%d-%m-%y") for date_str in os.listdir()]

        # Sort the list based on datetime objects
        sorted_folder_names = [date.strftime("%d-%m-%y") for date in sorted(date_objects)]

        for dir in sorted_folder_names:
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

                try:
                    df_data = pd.read_csv(file[len(file)-1],sep='\t', encoding = enc['encoding'],header = 10)
                    df_data.columns = df_data.columns.str.strip()
                    record_id = df_data['ID']
                    a=[]
                    for i in range(1,len(df_data),16):
                        a.append(i)
                except KeyError:
                    
                    try:
                        df_data = pd.read_csv(file[len(file)-1],sep=';', encoding = enc['encoding'],header = 14)
                        df_data.columns = df_data.columns.str.strip()
                        record_id = df_data['ID']
                        a=[]
                        for i in range(1,len(df_data),25):
                            a.append(i)

                    except KeyError:
                        print('none of the attempts works')
    
            df_vel = df_data.iloc[a]
            df_proc = pd.concat([df_proc, df_vel], ignore_index=True)
            
            os.chdir(os.path.normpath(os.getcwd() + os.sep + os.pardir))

        df_proc_comp = pd.DataFrame()

        for i in df_record_nan_rem['measurement_id']:
            df_proc_temp = df_proc[df_proc.ID.str.strip()==str(int(i))]
            df_proc_comp = pd.concat([df_proc_comp, df_proc_temp], ignore_index=True)

            

        os.chdir(os.path.normpath(os.getcwd() + os.sep + os.pardir + os.sep + os.pardir))

        nan_indices = df_record[df_record['measurement_id'].isna()].index

        dic_nan = {str(i) : ['nan'] for i in df_proc_comp.columns}
        df_nan = pd.DataFrame(dic_nan)

        
        for index in nan_indices:
            df_proc_comp = pd.concat([df_proc_comp.iloc[:index], df_nan, df_proc_comp.iloc[index:]]).reset_index(drop=True)
        result_df = df_proc_comp.reset_index(drop=True)

        result_df[result_df['ID']=='nan']=-1
        proc_meas_id_with_nan = result_df['ID'].to_list()
        proc_meas_id_with_nan_int = [int(x) for x in proc_meas_id_with_nan]

        df_record[df_record['measurement_id'].isna()]=-1 
        df_rec_meas_id = df_record['measurement_id'].to_list()
        df_rec_meas_id_int = [int(x) for x in df_rec_meas_id]

        ind_bool_err = []
        for i in df_rec_meas_id_int:       
            ind_bool_err.append(i not in proc_meas_id_with_nan_int)
        ind_err=[]
        for i in range(len(ind_bool_err)):
            if ind_bool_err[i]==True:
                ind_err.append(i)
        df_processed_data_with_nan_rem = result_df[result_df['ID']!=-1]

        a = result_df['ID']==-1
        nan_ind=[]
        for i in range(len(a)):
            if a[i]==True:
                nan_ind.append(i)

        nan_ind.extend(ind_err)
        nan_ind.sort()

        dic_nan = {str(i) : ['nan'] for i in df_processed_data_with_nan_rem.columns}
        df_nan = pd.DataFrame(dic_nan) 
        for index in nan_ind:
            df_processed_data_with_nan_rem = pd.concat([df_processed_data_with_nan_rem.iloc[:index], df_nan,df_processed_data_with_nan_rem.iloc[index:]]).reset_index(drop=True)
        result_df = df_processed_data_with_nan_rem.reset_index(drop=True)

        result_df.iloc[ind_err,:] = 'error'

        result_df.rename(columns={'ID': 'sample id'}, inplace=True)

        result_df.iloc[:,0] = (sample_id).astype(str)
        result_df.index = range(len(result_df))

        cal = result_df['sample id'].str.contains('cal')
        df_cal = result_df[cal]
        df_final = result_df[np.logical_not(cal)]
        df_final.index = range(len(df_final))

        return df_final,df_cal

        return result_df
    

    def extract_last_four_digits(self,number):
        return float(str(number)[-4:])


    
    def xrf(self):

        data_inventory = pd.read_excel(self.path_to_report, sheet_name = None)
        df_record = data_inventory.get('sample_report')
        sample_id_report = df_record['sample_id'].to_list()
        
        os.chdir(f'{self.drillhole}/xrf')  

        
        df_proc = pd.DataFrame()

        date_objects = [datetime.strptime(date_str, "%d-%m-%y") for date_str in os.listdir()]

        # Sort the list based on datetime objects
        sorted_folder_names = [date.strftime("%d-%m-%y") for date in sorted(date_objects)]

        for dir in sorted_folder_names:
            os.chdir(dir)
            file = glob.glob('*.csv')
            try:
                df_xrf = pd.read_csv(file[len(file)-1],skiprows=1)
                info = df_xrf['info']
            except KeyError:
                try:
                    df_xrf = pd.read_csv(file[len(file)-1])
                    info = df_xrf['info']
                except KeyError:
                    try:
                        df_xrf = pd.read_csv(file[len(file)-1],sep=';')
                        info = df_xrf['info']
                    except KeyError:
                        try:
                            df_xrf = pd.read_csv(file[len(file)-1],sep='\t')
                            info = df_xrf['info']
                        except KeyError:
                            print('cannot read the .csv file')
                    
                
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
        j = 0
    ###########
        cal_list = []
        for temp_cal in cal_list:
            calid = str(cal_list)[:-1]
            cal_list.append(calid)
        cal_list = [x for x,y in enumerate(info) if "s" in str(y)]

        # cal_list = pd.DataFrame(cal_list)
    ###########
        
        new_df = df_proc.drop(df_proc.index[drop_list])
        new_cal =df_proc.iloc[cal_list]
        # display(new_df)

        new_df.reset_index(inplace = True)
        new_cal.reset_index(inplace = True)
        new_cal_sample = [i for i in range(new_cal.shape[0])]
        new_cal_sample = np.reshape(new_cal_sample,(new_cal.shape[0],1))
        new_cal['info'] = new_cal_sample
        new_cal['info'] = 'cal_0'+new_cal['info'].astype('str')
        new_cal = new_cal[['info','As Concentration','As Error1s']]
        new_cal = new_cal.rename(columns={'info':'sample id'})
        new_cal = pd.DataFrame(new_cal)
        new_df = new_df.drop(new_df[new_df['info'] == 'del'].index)
        new_info = new_df['info'].tolist()
        sampleid_list = []
        # delete the last letter of info
        for temp_info in new_info:
            sampleid = str(temp_info)[:-1]
            sampleid_list.append(sampleid)
        # delete NaN & abcdef columns
        new_df['info']=sampleid_list
        new_df.index = range(len(new_df))

        str_sampleid_report = [str(x) for x in sample_id_report]

        ind = []
        for i in range(len(sampleid_list)):
            if str(sampleid_list[i]) not in str_sampleid_report:
                ind.append(i)

        for i in sorted(ind,reverse=True):
            del sampleid_list[i]

        new_df = new_df.drop(new_df.index[ind])

        new_df = new_df.dropna(axis=1, how='all') #drop all rows that have any NaN values
        new_df.columns = new_df.columns.str.strip()
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
        new_df1 = new_df.drop(['info'],axis=1)


        new_df = pd.concat([new_df1.apply(np.float64),new_df['info']],axis=1)
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
        new_df7['info']= np.unique(sampleid_list)
        df_final = new_df7 
        
        df_final.rename(columns={'info': 'sample id'}, inplace=True)

        os.chdir(os.path.normpath(os.getcwd() + os.sep + os.pardir+ os.sep + os.pardir))

        nan_ind = df_final[df_final['sample id'] == 'nan'].index

        df_final.drop(nan_ind,inplace=True)

        int_sample_id_report = [int(str(x)[-4:]) for x in df_final['sample id'].tolist()]

        int_df_sample_id = [int(str(x)[-4:]) for x in sample_id_report]

        indices = [index for index, value in enumerate(int_df_sample_id) if value not in int_sample_id_report]

        dic_err = {str(i) : ['error'] for i in df_final.columns}
        df_err = pd.DataFrame(dic_err)


        for index in indices:
            df_final = pd.concat([df_final.iloc[:index], df_err, df_final.iloc[index:]]).reset_index(drop=True)
        result_df = df_final.reset_index(drop=True)

        result_df.iloc[nan_ind,:] = 'nan'

        return result_df,new_cal


   
    
        