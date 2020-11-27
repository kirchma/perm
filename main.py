import pandas as pd
import os


class RawData:

    def __init__(self, path):
        self.path = path

    def read_file(self):
        try:
            df = pd.read_table(self.path, sep=' ')
            return df
        except Exception as ex:
            print(f"Exception {type(ex).__name__}, {ex.args}")

    def prepare_raw_data(self):
        df = self.read_file()
        df['temp'] = pd.to_datetime(df['Date'] + df['Time'], format='%d.%m.%Y%X')
        df['Duration'] = pd.to_timedelta(df['temp'] - df['temp'][0]).dt.total_seconds()
        df.drop(['Date', 'Time', 'temp'], axis=1, inplace=True)
        df = df[['Duration', 'Inlet_Pressure', 'Outlet_Pressure', 'Confining_Pressure', 'Temperature']]
        # convert bar (relative) to Megapascal (absolute)
        df[['Inlet_Pressure', 'Outlet_Pressure', 'Confining_Pressure']] = \
            df[['Inlet_Pressure', 'Outlet_Pressure', 'Confining_Pressure']].apply(lambda x: x / 10 + 0.0977)
        return df

x = RawData('b.txt')
df = x.prepare_raw_data()
print(df)