import os
import yaml
import subprocess
import numpy as np
import xarray as xr
import pandas as pd
import streamlit as st
from collections import deque
import plotly.express as px
from datetime import datetime
from streamlit_autorefresh import st_autorefresh
from math import radians, degrees, sin, cos, asin, atan2, tan

# =============================================================================
# Configuration & Setup
# =============================================================================
st.set_page_config(page_title="Scanner Dashboard", layout="wide", initial_sidebar_state="expanded")
#set refresh time in miliseconds

plot_items = ["SO2", "O3", "Ring", "average_intensity", "fit_quality"]

# Cache the config loading
@st.cache_data
def load_config():
    config_data = {}
    
    # Load Main Settings
    try:
        with open('Station/station_settings.yml', 'r') as ymlfile:
            config_data = yaml.load(ymlfile, Loader=yaml.FullLoader)
            config_data['output_folder'] = '/home/uom/Results' 
    except FileNotFoundError:
        config_data = {"station_name": "Unknown Station", "output_folder": "./Results"}

    # Load Location Settings
    try:
        with open('Station/location.yml', 'r') as ymlfile:
            loc = yaml.load(ymlfile, Loader=yaml.FullLoader)
            config_data['lat'] = loc.get('Lat', 0.0)
            config_data['lon'] = loc.get('Lon', 0.0)
            config_data['alt'] = loc.get('Alt', 0.0) # Assume 0 if not specified
    except FileNotFoundError:
        config_data['lat'], config_data['lon'], config_data['alt'] = 0.0, 0.0, 0.0

    return config_data

config = load_config()

# =============================================================================
# Helper Functions
# =============================================================================
def calc_intersection(scanner_lat, scanner_lon, scan_angle, scanner_alt, plume_alt, bearing):
    """
    Project a scanner measurement to the plume altitude plane.
    """
    R = 6371000.0
    alpha = radians(90.0 - float(scan_angle))  # from zenith -> from horizontal
    d = (plume_alt - scanner_alt) * tan(abs(alpha))  # horizontal distance (planar approx)
    if float(scan_angle) > 90:  # flip direction if over-vertical
        bearing = (bearing + 180) % 360
    lat1, lon1, bearing = map(radians, [scanner_lat, scanner_lon, bearing])
    ang_dist = d / R
    lat2 = asin(sin(lat1)*cos(ang_dist) + cos(lat1)*sin(ang_dist)*cos(bearing))
    lon2 = lon1 + atan2(sin(bearing)*sin(ang_dist)*cos(lat1),
                        cos(ang_dist) - sin(lat1)*sin(lat2))
    return degrees(lat2), degrees(lon2)

def get_scanner_status():
    try:
        with open("Station/status.txt", 'r') as r:
            status_time, status_text = r.readline().split(' - ')
            status_time = datetime.strptime(
                status_time, "%Y-%m-%d %H:%M:%S.%f"
            ).strftime("%Y-%m-%d %H:%M:%S")
    except Exception as e:
        status_text, status_time = f'Unknown ({e})', '???'
    return status_text, status_time

def get_board_status():
    try:
        output = subprocess.run(
            "/home/uom/OpenSO2/utility/read_board_status.sh",
            capture_output=True
        )
        board_data = output.stdout.decode('utf-8').strip().split(' | ')
        print(board_data)

        return {
            "temp": f"{board_data[0].split(' / ')[0]}",
            "vin": f"{board_data[1]} V",
            "vout": f"{board_data[2]} V",
            "iout": f"{board_data[3]} A"
        }
    except Exception as e:
        print(e)
        return {"temp": "- °C", "vin": "- V", "vout": "- V", "iout": "- A"}

def get_scanner_position_fig():
    """Reads the current scanner position and returns a Plotly polar figure."""
    try:
        scanner_pos = np.loadtxt('Station/scanner_position.txt')
        if scanner_pos.size > 1:
            scanner_pos = scanner_pos[0]
        scanner_pos = float(scanner_pos)
    except Exception:
        scanner_pos = np.nan

    positionfig = px.line_polar(
        r=[0, 1], theta=[0, scanner_pos], start_angle=90,
        template="plotly_dark", title='Current Scanner Position',
        markers=True
    )
    
    tickvals = np.concatenate([
        [x for x in np.arange(270, 360, 10)],
        [x for x in np.arange(0, 91, 10)],
        [180]
    ])
    ticktext = [str(x) for x in np.arange(-90, 91, 10)] + ['Home']
    
    positionfig.update_layout(
        polar=dict(
            radialaxis=dict(range=[0, 1], showticklabels=False, ticks='', showgrid=False),
            angularaxis=dict(tickmode='array', tickvals=tickvals, ticktext=ticktext)
        ),
        margin=dict(l=20, r=20, t=40, b=20)
    )
    return positionfig

def get_log_text(date_str):
    fname = f"{config.get('output_folder', './Results')}/{date_str}/{date_str}.log"
    try:
        with open(fname, "r") as r:
            # deque will efficiently pull only the last 200 lines into memory
            last_lines = deque(r, maxlen=500)
            
            # Join the lines back into a single string for the text_area
            return "".join(last_lines)
    except FileNotFoundError:
        return f"Log file {fname} not found!"

@st.cache_data(ttl=5) 
def load_scan_data(date_str, plot_param):
    fpath = config["output_folder"]
    folder_path = f"{fpath}/{date_str}/so2"
    
    try:
        scan_fnames = os.listdir(folder_path)
        scan_fnames.sort()
    except FileNotFoundError:
        return pd.DataFrame(), pd.DataFrame()

    plot_data = {'Scan Time (UTC)': [], 'Scan Angle (deg)': [], plot_param: []}
    last_scan_df = pd.DataFrame()

    for fname in scan_fnames:
        try:
            scan_ds = xr.load_dataset(f"{folder_path}/{fname}")
        except pd.errors.EmptyDataError:
            continue
        except Exception:
            continue

        scan_times = pd.date_range(
            scan_ds.scan_start_time,
            scan_ds.scan_end_time,
            periods=len(scan_ds.angle)
        )
        
        plot_data['Scan Time (UTC)'].extend(scan_times)
        plot_data['Scan Angle (deg)'].extend(scan_ds.angle.data)
        plot_data[plot_param].extend(scan_ds[plot_param].data)
        
        last_scan_df = pd.DataFrame({
            'Scan Angle (deg)': scan_ds.angle.data,
            plot_param: scan_ds[plot_param].data
        })

    paramdf = pd.DataFrame(plot_data)
    paramdf = paramdf[paramdf["Scan Time (UTC)"].notna()]
    paramdf = paramdf.fillna(0)
    
    return last_scan_df, paramdf

@st.cache_data(ttl=5)
def load_pointing_data(date_str):
    # Updated path: {home}/Results/{datestamp}/pointing/
    pointing_base_dir = os.path.join(config.get('output_folder', './Results'), date_str, 'pointing')
    
    try:
        # Find all subdirectories (these will be your HHMM folders)
        subdirs = [f.path for f in os.scandir(pointing_base_dir) if f.is_dir()]
        
        if not subdirs:
            return pd.DataFrame() # No folders found
            
        # Sort them alphabetically to automatically grab the latest HHMM folder
        subdirs.sort()
        latest_folder = subdirs[-1]
        
        csv_path = os.path.join(latest_folder, 'pointing_so2.csv')
        
        if not os.path.exists(csv_path):
            return pd.DataFrame() # No CSV in the latest folder
            
        # Load the data
        df = pd.read_csv(csv_path)
        
        # Ensure Plotly treats the Timestamp column as proper datetime objects
        if 'Timestamp' in df.columns:
            df['Timestamp'] = pd.to_datetime(df['Timestamp'])
            
        return df
        
    except FileNotFoundError:
        # The base /{datestamp}/pointing/ folder doesn't exist yet
        return pd.DataFrame()
    except Exception as e:
        return pd.DataFrame()
# =============================================================================
# App Layout & UI
# =============================================================================
st.title(f"🌋 {config.get('station_name', 'Scanner')} Dashboard")
st.markdown("---")

# ---------------------------------------------------------
# Sidebar Controls
# ---------------------------------------------------------
with st.sidebar:
    st.header("Dashboard Settings")
    
    # 1. Create a dropdown with sensible interval options (0 = off)
    refresh_rate = st.selectbox(
        "Auto-Refresh Rate",
        options=[0, 5, 10, 30, 60, 300],
        format_func=lambda x: "Off (Manual Only)" if x == 0 else f"Every {x} seconds",
        index=1 # Defaults to 5 seconds
    )
    
    # 2. Trigger the autorefresh dynamically if it is greater than 0
    if refresh_rate > 0:
        st_autorefresh(interval=refresh_rate * 1000, key="dashboard_refresh")

    st.markdown("---")

    st.header("Hardware Controls")
    if st.button("Refresh Data Now", type="primary"):
        st.rerun()
        
    st.markdown("---")
    if st.button("Reboot Pi", type="secondary"):
        st.warning("Rebooting system...")
        os.system("sudo reboot")
    
    st.markdown("---")
    st.header("Data Viewer Controls")
    selected_date = st.date_input("Select Date", datetime.now().date())
    selected_param = st.selectbox("Plot Parameter", plot_items, index=0)
    
    col1, col2 = st.columns(2)
    clim_lo = col1.number_input("Lower Limit", value=None, placeholder="Auto")
    clim_hi = col2.number_input("Upper Limit", value=None, placeholder="Auto")

    st.markdown("---")
    st.header("Projection Controls")
    
    # Initialize the default values in session state ONLY if they don't exist yet
    if "plume_alt" not in st.session_state:
        st.session_state.plume_alt = 900.0
    if "plume_az" not in st.session_state:
        st.session_state.plume_az = 180.0
    # Bind the inputs directly to the session state using 'key'
    st.number_input("Plume Altitude (m a.s.l)", step=100.0, key="plume_alt")
    st.number_input("Scan Plane Azimuth (deg)", step=5.0, key="plume_az")
# ---------------------------------------------------------
# Main Content Area: Hardware Status
# ---------------------------------------------------------
st.subheader("Current Hardware Status")

status_text, status_time = get_scanner_status()
board_stats = get_board_status()

col_metrics, col_polar = st.columns([2, 1])

with col_metrics:
    st.info(f"**Status:** {status_text} (at {status_time})")
    
    m1, m2 = st.columns(2)
    m1.metric("Temperature", board_stats["temp"])
    m2.metric("Voltage In (Vin)", board_stats["vin"])
    
    m3, m4 = st.columns(2)
    m3.metric("Voltage Out (Vout)", board_stats["vout"])
    m4.metric("Current Out (Iout)", board_stats["iout"])

with col_polar:
    st.plotly_chart(get_scanner_position_fig(), width='stretch')

st.markdown("---")

# ---------------------------------------------------------
# Plots
# ---------------------------------------------------------
st.subheader(f"{selected_param} Scan Data")
date_str = selected_date.strftime("%Y-%m-%d")

with st.spinner('Loading scan data...'):
    last_scan_df, paramdf = load_scan_data(date_str, selected_param)

if paramdf.empty:
    st.warning(f"No scan data found for {date_str} in `{config['output_folder']}/{date_str}/so2`")
else:
    c_min = clim_lo if clim_lo is not None else paramdf[selected_param].min()
    c_max = clim_hi if clim_hi is not None else paramdf[selected_param].max()

    #Label Formatting ---
    if selected_param == "SO2":
        axis_label = "SO<sub>2</sub> molecules cm<sup>-2</sup>"
    elif selected_param == "O3":
        axis_label = "O<sub>3</sub> molecules cm<sup>-2</sup>"
    else:
        axis_label = selected_param # Fallback for Ring, fit_quality, etc.

    # --- Plot 1: Full Day Scan Map (Time vs Angle) ---
    fig_map = px.scatter(
        paramdf, x="Scan Time (UTC)", y="Scan Angle (deg)",
        color=selected_param, range_color=[c_min, c_max], 
        template="plotly_dark", title='Full Day Scan Map (Angle vs Time)',
        labels={selected_param: axis_label}
    )
    
# --- Plot 2: Geographic Projection of Last Scan ---
    lats, lons = [], []
    scan_lat, scan_lon, scan_alt = config['lat'], config['lon'], config['alt']
    
    for ang in last_scan_df['Scan Angle (deg)']:
        proj_lat, proj_lon = calc_intersection(
            scan_lat, scan_lon, ang, scan_alt, 
            st.session_state.plume_alt, 
            st.session_state.plume_az   
        )
        lats.append(proj_lat)
        lons.append(proj_lon)
        
    last_scan_df['Latitude'] = lats
    last_scan_df['Longitude'] = lons

    # Create the map with NO default internet style
    fig_proj = px.scatter_mapbox(
        last_scan_df, lat="Latitude", lon="Longitude", 
        color=selected_param, range_color=[c_min, c_max],
        color_continuous_scale="plasma",
        zoom=13, # Set default zoom to one of our downloaded levels
        center=dict(lat=scan_lat, lon=scan_lon),
        title=f"Last Scan Projected to {st.session_state.plume_alt}m (Azimuth: {st.session_state.plume_az}°)",
        labels={selected_param: axis_label}
    )
    
    # Force Plotly to use our locally hosted offline tiles
    fig_proj.update_layout(
        mapbox_style="white-bg",
        mapbox_layers=[
            {
                "below": 'traces',
                "sourcetype": "raster",
                # The port (8501) must match whatever port Streamlit is running on!
                "source": ["http://localhost:8501/app/static/tiles/{z}/{x}/{y}.png"]
            }
        ],
        margin={"r":0,"t":40,"l":0,"b":0}
    )

    # --- Plot 3: Standard Last Scan Profile ---
    fig_last_scan = px.line(
        last_scan_df, x="Scan Angle (deg)", y=selected_param, 
        template="plotly_dark", title='Last Scan Profile',
        labels={selected_param: axis_label}
    )

    # Render Charts
    st.plotly_chart(fig_map, width='stretch')
    
    col_plot1, col_plot2 = st.columns(2)
    with col_plot1:
        st.plotly_chart(fig_proj, width='stretch')
    with col_plot2:
        st.plotly_chart(fig_last_scan, width='stretch')

st.markdown("---")

st.subheader("Pointing Spectra")

with st.spinner('Loading pointing data...'):
    # Pass date_str into the function so it knows which day's folder to look in
    pointing_df = load_pointing_data(date_str)

if pointing_df.empty:
    st.info(f"No pointing data currently available in `{config.get('output_folder')}/{date_str}/pointing/`")
else:
    # Generate Plotly figure with error bars
    fig_pointing = px.scatter(
        pointing_df, 
        x="Timestamp", 
        y="SO2", 
        error_y="SO2_err",
        template="plotly_dark",
        title="Latest Pointing SO2 Time Series",
        labels={selected_param: axis_label}
    )
    
    # Force Plotly to draw lines connecting our scatter markers
    fig_pointing.update_traces(mode='lines+markers')
    
    # Ensure it spans the full width of the dashboard
    st.plotly_chart(fig_pointing, use_container_width=True)

st.markdown("---")
# ---------------------------------------------------------
# Expandable Log Viewer 
# ---------------------------------------------------------
st.subheader("Station Logs")
with st.expander(f"View Logs for {selected_date}", expanded=False):
    log_content = get_log_text(date_str)
    st.text_area("Log Output", log_content, height=300, disabled=True, label_visibility="hidden")