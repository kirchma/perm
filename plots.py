import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots


class Plotter:

    def __init__(self, df, **kwargs):
        self.df = df
        for key, value in kwargs.items():
            setattr(self, key, value)

    def raw_data_chart(self):
        fig = make_subplots(specs=[[{'secondary_y': True}]])
        # Add traces
        fig.add_trace(
            go.Scatter(x=self.df['Duration'], y=self.df['Inlet_Pressure'] * 1e-6, name='Eingangsdruck',
                       line_color='blue'),
            secondary_y=False)
        fig.add_trace(
            go.Scatter(x=self.df['Duration'], y=self.df['Outlet_Pressure'] * 1e-6, name='Ausgangsdruck',
                       line_color='blue'),
            secondary_y=False)
        fig.add_trace(
            go.Scatter(x=self.df['Duration'], y=self.df['Confining_Pressure'] * 1e-6, name='Manteldruck',
                       line_color='black', visible='legendonly'),
            secondary_y=False)
        fig.add_trace(
            go.Scatter(x=self.df['Duration'], y=self.df['Temperature'] - 273.15, name='Temperatur',
                       line_color='red'),
            secondary_y=True)
        fig.add_vline(
            x=self.df.iloc[self.start]['Duration'], line_dash='dot')
        fig.add_vline(
            x=self.df.iloc[self.stop - 1]['Duration'], line_dash='dot')

        fig.update_layout(
            title=f'<b>{self.name}</b>',
            xaxis=dict(showexponent='all', exponentformat='power'))
        fig.update_xaxes(title_text='Messdauer in s', type='log')
        fig.update_yaxes(title_text='Druck in MPa', secondary_y=False)
        fig.update_yaxes(title_text='Temperatur in °C', secondary_y=True, range=[12, 16], showgrid=False)
        fig.show()

    def result_chart(self):
        self.df['Diff_Inlet'] = (abs(self.df['Inlet_Pressure'] - self.df['Inlet_Pressure_Cal'])
                                 / self.df['Inlet_Pressure'])
        self.df['Diff_Outlet'] = (abs(self.df['Outlet_Pressure'] - self.df['Outlet_Pressure_Cal'])
                                  / self.df['Outlet_Pressure'])

        fig = make_subplots(specs=[[{'secondary_y': True}]])
        # Add traces
        fig.add_trace(
            go.Scatter(x=self.df['Duration'], y=self.df['Inlet_Pressure'] * 1e-6, name='Messwert Eingang',
                       line_color='blue'))
        fig.add_trace(
            go.Scatter(x=self.df['Duration'], y=self.df['Outlet_Pressure'] * 1e-6, name='Messwert Ausgang',
                       line_color='blue'))
        fig.add_trace(
            go.Scatter(x=self.df['Duration'], y=self.df['Confining_Pressure'] * 1e-6, name='Manteldruck',
                       line_color='black', visible='legendonly'))
        fig.add_trace(
            go.Scatter(x=self.df['Duration'], y=self.df['Temperature'] - 273.15, name='Temperatur',
                       line_color='red', visible='legendonly'),
            secondary_y=True)

        fig.add_trace(
            go.Scatter(x=self.df['Duration'], y=self.df['Inlet_Pressure_Cal'] * 1e-6, name='Rechenwert Eingang',
                       line_color='red', mode='markers', marker=dict(size=3)))
        fig.add_trace(
            go.Scatter(x=self.df['Duration'], y=self.df['Outlet_Pressure_Cal'] * 1e-6, name='Rechenwert Ausgang',
                       line_color='red', mode='markers', marker=dict(size=3)))

        fig.add_trace(
            go.Scatter(x=self.df['Duration'], y=self.df['Diff_Inlet'], name='Abweichung Eingang',
                       line_color='green', fill='tozeroy'),
            secondary_y=True)
        fig.add_trace(
            go.Scatter(x=self.df['Duration'], y=self.df['Diff_Outlet'], name='Abweichung Ausgang',
                       line_color='yellow', fill='tozeroy'),
            secondary_y=True)

        fig.update_layout(
            xaxis=dict(showexponent='all', exponentformat='power'))
        fig.update_xaxes(title_text='Messdauer in s', type='log')
        fig.update_yaxes(title_text='Druck in MPa', secondary_y=False)
        fig.update_yaxes(secondary_y=True, showgrid=False)
        fig.show()