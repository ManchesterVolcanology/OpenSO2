import os
import yaml
import xarray as xr
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
from flask import Flask
from dash import Dash, dcc, html
import dash_bootstrap_components as dbc
from dash.dependencies import Output, Input, State

# Read the station settings
with open('Station/station_settings.yml', 'r') as ymlfile:
    config = yaml.load(ymlfile, Loader=yaml.FullLoader)

home = '/home/pi/'
home = 'D:/Code'

# Set possible plot items
plot_items = ["SO2", "O3", "Ring", "int_av", "fit_quality"]

# Get today's date
tday_date = datetime.now().date()

# Get the dates available
data_folders = os.listdir(f"{home}/Results")
data_folders.sort()
if len(data_folders) == 0:
    data_folders = [tday_date]
data_dates = pd.to_datetime(data_folders)
disabled_days = [
    d for d in pd.date_range(data_dates.min(), tday_date)
    if d not in data_dates
]


def update_status():
    # Get the station status
    try:
        with open(f"{home}/OpenSO2/Station/status.txt", 'r') as r:
            status_time, status_text = r.readline().split(' - ')
            status_time = datetime.strptime(
                status_time, "%Y-%m-%d %H:%M:%S.%f"
            ).strftime("%Y-%m-%d %H:%M:%S")
    except Exception as e:
        status_text, status_time = f'Unknown ({e})', '???'

    return f"Current status: {status_text} (at {status_time})"


# Generate the map data
vlat, vlon = config['volcano_location']
with open('Station/location.yml', 'r') as ymlfile:
    scanner_location = yaml.load(ymlfile, Loader=yaml.FullLoader)
slat, slon = scanner_location['Lat'], scanner_location['Lon']
df = pd.DataFrame(
    {
        "name": [config["station_name"], config["volcano_name"]],
        "lat": [slat, vlat],
        "lon": [slon, vlon],
        "color": ["Red", "Blue"],
        "size": [5, 5]
     }
)

map_fig = px.scatter_mapbox(
    df, lat="lat", lon="lon", zoom=config['map_zoom'],
    hover_data=["lat", "lon"],
    mapbox_style="stamen-terrain",
    color="color",
    size="size",
    hover_name="name",
    text="name"
)
map_fig.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0})
map_fig.update_layout(showlegend=False)

# Geerate the scan position graph
polar_fig = px.line_polar(
    r=[0, 1], theta=[0, -90], start_angle=90, template="plotly_dark"
)
tickvals = np.concatenate([
    [x for x in np.arange(270, 360, 10)],
    [x for x in np.arange(0, 91, 10)],
    [180]
])
ticktext = [str(x) for x in np.arange(-90, 91, 10)] + ['Home']
polar_fig.update_layout(
    polar = dict(
        radialaxis=dict(
            range=[0, 1], showticklabels=False, ticks='', showgrid=False
        ),
        angularaxis = dict(
            tickmode='array',
            tickvals=tickvals,
            ticktext=ticktext
        )
    )
)

go.Figure(go.Indicator(
    mode='gauge+number',
    value=-180,
    domain={'x': [0, 1], 'y': [0, 1]},
    title={'text': 'Scanner Position'}
))

# Setup the Dash app
server = Flask(__name__)
app = Dash(__name__, server=server, external_stylesheets=[dbc.themes.DARKLY])
app.title = f"{config['station_name']} Dashboard"

# =============================================================================
# App Controls
# =============================================================================

controls = dbc.Card(
    [
        html.Div(
            [
                dcc.DatePickerSingle(
                    id="date-picker",
                    min_date_allowed=data_dates.min().date(),
                    max_date_allowed=tday_date,
                    initial_visible_month=tday_date,
                    date=tday_date,
                    display_format="YYYY/MM/DD",
                    disabled_days=disabled_days
                )
            ],
            className="dash-bootstrap"
        ),

        html.Div(
            [
                dbc.Label("Plot Parameter"),
                dcc.Dropdown(
                    id="param-filter",
                    options=[{"label": plot_param, "value": plot_param}
                             for plot_param in plot_items],
                    value="SO2",
                    clearable=False,
                    searchable=False,
                    className="dropdown",
                    style=dict(color="black")
                )
            ]
        ),

        html.Hr(),

        html.Div(
            [
                dbc.Button("View logs", id="open", color="primary"),

                dbc.Modal(
                    [
                        dbc.ModalHeader("Station logs"),
                        dbc.ModalBody(
                            dbc.Textarea(rows=10, id="log-text")
                        ),
                        dbc.ModalFooter(
                            dbc.Button(
                                "Close",
                                id="close",
                                className="ml-auto"
                            )
                        )
                    ],
                    id="modal",
                    is_open=False,
                    size="xl",
                    backdrop=True,
                    scrollable=True,
                    centered=True,
                    fade=True
                ),

                dbc.Button("Refresh", id="refresh", color="primary",
                           style={"margin-left": "15px"})
            ]
        ),

        html.Hr(),

        html.Div(
            [
                dbc.Label('Scanner Position'),
                dcc.Graph(id="polar-chart", figure=polar_fig),
            ]
        )
    ],
    body=True
)

# =============================================================================
# App Plots
# =============================================================================

plots = dbc.Card(
    [
        html.Div([
            dcc.Graph(id="scan-chart"),
            dcc.Interval(
                id='interval_component',
                interval=1 * 1000, n_intervals=0
            )
        ]),
        html.Hr(),

        html.Div(
            [
                dbc.Label("Upper Limit"),
                dbc.Input(id='clim-hi', type='number', placeholder="-")
            ]
        ),

        html.Div(
            [
                dbc.Label("Lower Limit"),
                dbc.Input(id='clim-lo', type='number', placeholder="-")
            ]
        ),
        html.Div(
            dcc.Graph(id="param-chart")
        ),
        html.Hr(),
        html.Div(
            dcc.Graph(id="map-chart", figure=map_fig)
        )
    ],
    body=True
)

# =============================================================================
# App Layout
# =============================================================================

app.layout = dbc.Container(
    [
        html.H1(f"{config['station_name']} Dashboard"),
        html.Div([dbc.Label(update_status())], id="status-text"),
        html.Hr(),
        dbc.Row(
            [
                dbc.Col(controls, md=4),
                dbc.Col(plots, md=8),
            ]
        )
    ],
    fluid=True
)


# =============================================================================
# Callbacks
# =============================================================================

@app.callback(
    [
        Output("polar-chart", "figure"),
        Output("scan-chart", "figure"),
        Output("param-chart", "figure"),
        Output("status-text", "children")
    ],
    [
        Input("date-picker", "date"),
        Input("param-filter", "value"),
        Input("clim-hi", "value"),
        Input("clim-lo", "value"),
        Input("refresh", "n_clicks"),
        Input("interval_component", "n_intervals")
    ]
)
def refresh(plot_date, plot_param, climhi, climlo, n, i_n):
    """Callback to refresh the dashboard."""
    # Get the scanner position
    try:
        scanner_pos = np.loadtxt('Station/scanner_position.txt')
    except FileNotFoundError:
        scanner_pos = -180
    polarfig = px.line_polar(
        r=[0, 1], theta=[0, scanner_pos], start_angle=90,
        template="plotly_dark"
    )
    tickvals = np.concatenate([
        [x for x in np.arange(270, 360, 10)],
        [x for x in np.arange(0, 91, 10)],
        [180]
    ])
    ticktext = [str(x) for x in np.arange(-90, 91, 10)] + ['Home']
    polarfig.update_layout(
        polar = dict(
            radialaxis=dict(
                range=[0, 1], showticklabels=False, ticks='', showgrid=False
            ),
            angularaxis = dict(
                tickmode='array',
                tickvals=tickvals,
                ticktext=ticktext
            )
        )
    )

    # Get the path to the data
    fpath = f'{home}/{config["output_folder"]}'

    # Get the data files
    try:
        scan_fnames = os.listdir(f"{fpath}/{plot_date}/so2")
        scan_fnames.sort()
    except FileNotFoundError:
        scandf = pd.DataFrame(
            index=np.arange(0),
            columns=["Scan Angle (deg)", plot_param]
        )
        paramdf = pd.DataFrame(
            index=np.arange(0),
            columns=["Scan Time (UTC)", "Scan Angle (deg)", plot_param]
        )
        scanfig = px.scatter(
            scandf, x="Scan Angle (deg)", y=plot_param, template="plotly_dark"
        )
        paramfig = px.scatter(
            paramdf, x="Scan Time (UTC)", y="Scan Angle (deg)",
            color=plot_param, range_color=[0, 1], template="plotly_dark"
        )
        return [polarfig, scanfig, paramfig, [dbc.Label(update_status())]]

    plot_data = {'Scan Time (UTC)': [], 'Scan Angle (deg)': [], plot_param: []}

    # Iterate through the files
    for fname in scan_fnames:

        # Load the scan file, unpacking the angle and SO2 data
        try:
            scan_ds = xr.load_dataset(f"{fpath}/{plot_date}/so2/{fname}")
        except pd.errors.EmptyDataError:
            continue

        scan_times = pd.date_range(
            scan_ds.scan_start_time,
            scan_ds.scan_end_time,
            periods=len(scan_ds.angle)
        )
        plot_data['Scan Time (UTC)'].extend(scan_times)
        plot_data['Scan Angle (deg)'].extend(scan_ds.angle.data)
        plot_data[plot_param].extend(scan_ds[plot_param].data)

    # Save the last scan
    scandf = pd.DataFrame({
        'Scan Angle (deg)': scan_ds.angle.data,
        plot_param: scan_ds[plot_param].data
    })
    scandf = scan_ds.to_dataframe()
    scandf['Scan Angle (deg)'] = scan_ds.angle

    # Convert to a dataframe
    paramdf = pd.DataFrame(plot_data)

    # Remove row with nan times
    paramdf = paramdf[paramdf["Scan Time (UTC)"].notna()]

    # Set nan values to zero
    paramdf = paramdf.fillna(0)

    # Set the limits
    if climlo is None:
        climlo = paramdf[plot_param].min()
    if climhi is None:
        climhi = paramdf[plot_param].max()
    limits = [climlo, climhi]

    # Generate the figures
    scanfig = px.line(
        scandf, x="Scan Angle (deg)", y=plot_param, template="plotly_dark"
    )
    paramfig = px.scatter(
        paramdf, x="Scan Time (UTC)", y="Scan Angle (deg)",
        color=plot_param, range_color=limits, template="plotly_dark"
    )

    return [polarfig, scanfig, paramfig, [dbc.Label(update_status())]]


@app.callback(
    Output("modal", "is_open"),
    [Input("open", "n_clicks"), Input("close", "n_clicks")],
    State("modal", "is_open")
)
def toggle_modal(n1, n2, is_open):
    if n1 or n2:
        return not is_open
    return is_open


@app.callback(
    Output("log-text", "value"),
    Input("date-picker", "date")
)
def update_log_text(date):
    # Try to read the log file
    fname = f"{home}/{config['output_folder']}/{date}/{date}.log"
    try:
        with open(fname, "r") as r:
            lines = r.readlines()
        log_text = ""
        for line in lines:
            log_text += line.strip() + "\n"
    except FileNotFoundError:
        log_text = f"Log file {fname} not found!"

    return log_text


if __name__ == "__main__":
    app.run_server(debug=True)
