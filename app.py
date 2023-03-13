import os
import yaml
import subprocess
import numpy as np
import xarray as xr
import pandas as pd
from flask import Flask
import plotly.express as px
from datetime import datetime
from dash import Dash, dcc, html
import dash_bootstrap_components as dbc
from dash.dependencies import Output, Input, State

# Read the station settings
with open('Station/station_settings.yml', 'r') as ymlfile:
    config = yaml.load(ymlfile, Loader=yaml.FullLoader)

# Set possible plot items
plot_items = ["SO2", "O3", "Ring", "average_intensity", "fit_quality"]

# Get today's date
tday_date = datetime.now().date()

# Get the dates available
data_folders = os.listdir(f"{config['output_folder']}")
data_folders.sort()
if len(data_folders) == 0:
    data_folders = [tday_date]
data_dates = pd.to_datetime(data_folders)
disabled_days = [
    d for d in pd.date_range(data_dates.min(), tday_date)
    if d not in data_dates
]


def update_scanner_status():
    # Get the station status
    try:
        with open("Station/status.txt", 'r') as r:
            status_time, status_text = r.readline().split(' - ')
            status_time = datetime.strptime(
                status_time, "%Y-%m-%d %H:%M:%S.%f"
            ).strftime("%Y-%m-%d %H:%M:%S")
    except Exception as e:
        status_text, status_time = f'Unknown ({e})', '???'

    return f"Current status: {status_text} (at {status_time})"


def update_board_status():
    output = subprocess.run(
        "/home/pi/OpenSO2/utility/read_board_status.sh",
        capture_output=True
    )
    board_data = output.stdout.decode('utf-8').strip().split(' | ')
    temp_str = f"Temp: {board_data[0].split(' / ')[0]}"
    vin_str = f"Vin: {board_data[1]} V"
    vout_str = f"Vout: {board_data[2]} V"
    iout_str = f"Iout: {board_data[3]} A"
    return [temp_str, vin_str, vout_str, iout_str]


def update_scanner_position():
    # Get the scanner position
    try:
        scanner_pos = np.loadtxt('Station/scanner_position.txt')
    except FileNotFoundError:
        scanner_pos = np.nan

    # Generate the figure
    positionfig = px.line_polar(
        r=[0, 1], theta=[0, scanner_pos], start_angle=90,
        template="plotly_dark", title='Scanner Position',
        markers=True
    )
    tickvals = np.concatenate([
        [x for x in np.arange(270, 360, 10)],
        [x for x in np.arange(0, 91, 10)],
        [180]
    ])
    ticktext = [str(x) for x in np.arange(-90, 91, 10)] + ['Home']
    positionfig.update_layout(
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

    return positionfig


# Generate the map data
with open('Station/location.yml', 'r') as ymlfile:
    scanner_location = yaml.load(ymlfile, Loader=yaml.FullLoader)
slat, slon = scanner_location['Lat'], scanner_location['Lon']
df = pd.DataFrame(
    {
        "name": [config["station_name"]],
        "lat": [slat],
        "lon": [slon],
        "color": ["Red"],
        "size": [5]
     }
)

map_fig = px.scatter_mapbox(
    df, lat="lat", lon="lon", zoom=11,
    hover_data=["lat", "lon"],
    mapbox_style="stamen-terrain",
    color="color",
    size="size",
    hover_name="name",
    text="name"
)
map_fig.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0})
map_fig.update_layout(showlegend=False)



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

                dbc.Button(
                    "Refresh", id="refresh", color="primary",
                    style={"margin-left": "15px"}
                ),

                dbc.Button(
                    "Pause Scanning", id="pause", color="primary",
                    style={"margin-left": "15px"}
                ),

                dbc.Button(
                    "Reboot Scanner", id="reboot", color="primary",
                    style={"margin-left": "15px"}
                )
            ]
        ),

        html.Hr(),

        html.Div([dbc.Label(update_scanner_status())], id="status-text"),
        html.Div([dbc.Label("-")], id="board-temp"),
        html.Div([dbc.Label("-")], id="board-vin"),
        html.Div([dbc.Label("-")], id="board-vout"),
        html.Div([dbc.Label("-")], id="board-iout"),

        html.Hr(),

        html.Div(
            [
                dcc.Graph(id="polar-chart", figure=update_scanner_position()),
                dcc.Interval(
                    id='position-updater',
                    interval=1 * 1000, n_intervals=0
                )
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
        html.Div([
            dcc.Graph(id="scan-chart"),
            dcc.Interval(
                id='data-updater',
                interval=600 * 1000, n_intervals=0
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
        Output("scan-chart", "figure"),
        Output("param-chart", "figure")
    ],
    [
        Input("date-picker", "date"),
        Input("param-filter", "value"),
        Input("clim-hi", "value"),
        Input("clim-lo", "value"),
        Input("refresh", "n_clicks"),
        Input("data-updater", "n_intervals")
    ]
)
def refresh(plot_date, plot_param, climhi, climlo, n, i_n):
    """Callback to refresh the dashboard."""
    # Get the path to the data
    fpath = f'{config["output_folder"]}'

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
            scandf, x="Scan Angle (deg)", y=plot_param, template="plotly_dark",
            title='Last Scan'
        )
        paramfig = px.scatter(
            paramdf, x="Scan Time (UTC)", y="Scan Angle (deg)",
            color=plot_param, range_color=[0, 1], template="plotly_dark",
            title='Scan Map'
        )
        return [scanfig, paramfig]

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
        scandf, x="Scan Angle (deg)", y=plot_param, template="plotly_dark",
        title='Last Scan'
    )
    paramfig = px.scatter(
        paramdf, x="Scan Time (UTC)", y="Scan Angle (deg)",
        color=plot_param, range_color=limits, template="plotly_dark",
            title='Scan Map'
    )

    return [scanfig, paramfig]


@app.callback(
    [
        Output("polar-chart", "figure"),
        Output("status-text", "children"),
        Output("board-temp", "children"),
        Output("board-vin", "children"),
        Output("board-vout", "children"),
        Output("board-iout", "children")
    ],
    [
        Input("refresh", "n_clicks"),
        Input("position-updater", "n_intervals")
    ]
)
def update_scanner_status_cb(n_clicks, n_intervals):
    """Update scanner position and status."""
    return [
        update_scanner_position(),
        [dbc.Label(update_scanner_status())],
        *[[label] for label in update_board_status()]
    ]


@app.callback(
        Output("pause", "children"),
        [Input("pause", "n_clicks")],
)
def pause_scanner(n_clicks):
    if n_clicks is not None:
        if not os.path.isfile('Station/pause'):
            open('Station/pause', 'w').close()
            return "Continue Scanning"
        else:
            os.remove('Station/pause')
            return "Pause Scanning"
    return 'Pause Scanning'


@app.callback(
        Output("reboot", "children"),
        [Input("reboot", "n_clicks")],
)
def reboot_scanner(n_clicks):
    if n_clicks is not None:
        os.system("sudo reboot")
    return 'Reboot Scanner'


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
    fname = f"{config['output_folder']}/{date}/{date}.log"
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
    app.run_server(host='0.0.0.0')
