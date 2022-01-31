import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import sys


class Plotter:

    def __init__(self, df, **kwargs):
        self.df = df
        for key, value in kwargs.items():
            setattr(self, key, value)

    def raw_data_chart(self):
        app = dash.Dash(__name__)

        max_index = len(self.df)

        fig = make_subplots(specs=[[{'secondary_y': True}]])
        # Add traces
        fig.add_trace(
            go.Scatter(x=self.df['Duration'], y=self.df['Inlet_Pressure'] * 1e-6, name='Eingangsdruck',
                       line_color='blue'),
            secondary_y=False
        )
        fig.add_trace(
            go.Scatter(x=self.df['Duration'], y=self.df['Outlet_Pressure'] * 1e-6, name='Ausgangsdruck',
                       line_color='blue'),
            secondary_y=False
        )
        fig.add_trace(
            go.Scatter(x=self.df['Duration'], y=self.df['Confining_Pressure'] * 1e-6, name='Manteldruck',
                       line_color='black', visible='legendonly'),
            secondary_y=False
        )
        fig.add_trace(
            go.Scatter(x=self.df['Duration'], y=self.df['Temperature'] - 273.15, name='Temperatur',
                       line_color='red'),
            secondary_y=True
        )
        fig.add_vline(
            x=self.df.iloc[self.start]['Duration'], line_dash='dot'
        )
        fig.add_vline(
            x=self.df.iloc[self.stop - 1]['Duration'], line_dash='dot'
        )

        fig.update_layout(
            xaxis=dict(showexponent='all', exponentformat='power')
        )
        fig.update_xaxes(title_text='Messdauer in s', type='log')
        fig.update_yaxes(title_text='Druck in MPa', secondary_y=False)
        fig.update_yaxes(title_text='Temperatur in °C', secondary_y=True, range=[12, 16], showgrid=False)

        app.layout = html.Div([
            html.Div([
                html.H1(self.name),
                html.Button('Calculate', id='button'),
                dcc.Graph(id='measurement_plot', figure=fig,
                          style={'width': '70%', 'height': '70vh'}),
                html.Pre(id='click_x_value', hidden=True),
                html.Div([
                    html.H4('Beginn der Messung'),
                    dcc.Slider(
                        id='slider_start', min=1, max=max_index, value=self.start,
                    ),
                    dcc.Input(
                        id='input_start', type='number', min=1, max=max_index, value=self.start,
                    )
                ], style={'width': '25%', 'display': 'inline-block'}),

                html.Div([
                    html.H4('Ende der Messung'),
                    dcc.Slider(
                        id='slider_stop', min=0, max=max_index, value=self.stop,
                    ),
                    dcc.Input(
                        id='input_stop', type='number', min=0, max=max_index, value=self.stop,
                    )
                ], style={'width': '25%', 'display': 'inline-block'})
            ]),
        ])

        @app.callback(
            Output('measurement_plot', 'figure'),
            Input('slider_start', 'value'),
            Input('slider_stop', 'value'))
        def update_xaxis(x1, x2):
            x1 = self.df.iloc[x1]['Duration']
            x2 = self.df.iloc[x2-1]['Duration']
            x_min = np.log(x1)/np.log(10)
            x_max = np.log(x2)/np.log(10)
            fig.update_xaxes(range=[x_min, x_max])
            fig.update_layout(transition_duration=500)
            print(self.start, self.stop, len(self.df))
            return fig

        @app.callback(
            Output('slider_start', 'value'),
            Output('input_start', 'value'),
            Output('click_x_value', 'children'),
            Input('slider_start', 'value'),
            Input('input_start', 'value'),
            Input('measurement_plot', 'clickData'))
        def start_value(input_value, slider_value, clickData):
            ctx = dash.callback_context
            trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
            value = self.start

            if trigger_id == 'slider_start':
                value = input_value
            elif trigger_id == 'input_start':
                value = slider_value
            else:
                try:
                    x = clickData['points'][0]['x']
                    value = self.df.index[self.df['Duration'] == x][0]
                except:
                    pass

            return value, value, value

        @app.callback(
            Output('slider_stop', 'value'),
            Output('input_stop', 'value'),
            Input('slider_stop', 'value'),
            Input('input_stop', 'value'))
        def stop_value(input_value, slider_value):
            ctx = dash.callback_context
            trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
            value = input_value if trigger_id == 'slider_stop' else slider_value
            return value, value

        app.run_server(debug=True)

