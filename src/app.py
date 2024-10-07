from dash import Dash, html, dcc, Input, Output, dash_table, callback_context
import dash_daq as daq
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import matplotlib.colors as mcolors
from matplotlib import colormaps
import zipfile
import requests
import io
import xml.etree.ElementTree as ET
import json

# TODO: Dropdown for day of the week?
# TODO: Allow clicking on table to select station
#     Output(dtable,'active_cell'),
#     Output(dtable, "selected_cells"),
#     return None, []


app = Dash(__name__)
server = app.server

threshold = 8
cmap = colormaps["magma"]

# color palette
city_pal = {"Boston":"#e6194B",
            "Cambridge":"#4363d8",
            "Somerville":"#f58231",
            "Salem":"#a9a9a9",
            "Brookline":"#42d4f4",
            "Everett":"#ffe119",
            "Medford":"#808000",
            "Watertown":"#469990",
            "Chelsea":"#f032e6",
            "Arlington":"#9A6324",
            "Revere":"#000075",
            "Malden":"#800000",
            "Hingham":"#a9a9a9",
            "Newton":"#911eb4",
           }

month_mapping = {
    "01": "January", "02": "February", "03": "March", "04": "April",
    "05": "May", "06": "June", "07": "July", "08": "August",
    "09": "September", "10": "October", "11": "November", "12": "December"
}

styles = {
    'pre': {
        'border': 'thin lightgrey solid',
        'overflowX': 'scroll'
    }
}

# start mapbox
maptoken = open(".mapbox").read()
px.set_mapbox_access_token(maptoken)

# functions for formatting
def replacer(s, newstring, index, nofail=False):
    # raise an error if index is outside of the string
    if not nofail and index not in range(len(s)):
        raise ValueError("index outside given string")
    # if not erroring, but the index is still not in the correct range..
    if index < 0:  # add it to the beginning
        return newstring + s
    if index > len(s):  # add it to the end
        return s + newstring

    # insert the new string between "slices" of the original
    return s[:index] + newstring + s[index + 1:]


def strtobr(string, every=25):
    idxes = []
    if len(string) < every:
        return string
    else:
        for i in range(every, len(string), every):
            nearest_space = string.find(" ", i)
            if nearest_space > 0:
                idxes.append(nearest_space)
        for j in reversed(idxes):
            string = replacer(string, "<br>", j)

        return string

def NormalizeData(data):
    return (data - np.min(data)) / (np.max(data) - np.min(data))

def get_all_tripdata(s3url):
    response = requests.get(s3url)
    root = ET.fromstring(response.content)
    s3files = []
    for contents in root.findall('{http://s3.amazonaws.com/doc/2006-03-01/}Contents'):
        key = contents.find('{http://s3.amazonaws.com/doc/2006-03-01/}Key').text
        s3files.append(key)

    tripfiles = {}
    for file in s3files:
        if "bluebikes-tripdata" in file:
            year = file[0:4]
            month = file[4:6]
            tripfiles[month_mapping[month] + " " + str(year)] = s3url+"/"+file
    return tripfiles


def get_bike_data(s3path):
    pattern = r'\s(\d{2}):'
    r = requests.get(s3path)
    z = zipfile.ZipFile(io.BytesIO(r.content))
    for name in z.namelist():
        if "__MACOSX" not in name:
            csv_extract = name

    # look to get column names
    if "start_station_name" in pd.read_csv(z.open(csv_extract),nrows=2).columns:
        kept_cols = ["ride_id", "start_station_name", "end_station_name","started_at"]
        bike_df = pd.read_csv(z.open(csv_extract), usecols=kept_cols).dropna()
    else:
        kept_cols = ["start station name", "end station name","starttime"]
        bike_df = pd.read_csv(z.open(csv_extract), usecols=kept_cols).dropna()
        # rename to make consistent going forward
        bike_df.rename(columns={"start station name":"start_station_name",
                                "end station name":"end_station_name",
                                "starttime":"started_at"
                                },inplace=True)

    # removes trips to own station
    bike_df = bike_df.loc[bike_df["start_station_name"] != bike_df["end_station_name"]]
    bike_df["start hour"] = bike_df['started_at'].str.extract(pattern, expand=True).astype(int)

    return bike_df

ORIGIN_DESTINATION = "Number of Rides Started"

def get_ride_sum(geospacial_data, month_bike_data):
    grouped_data = geospacial_data.copy()
    if ORIGIN_DESTINATION == "Number of Rides Started":
        grouped_data[ORIGIN_DESTINATION] = month_bike_data["start_station_name"].value_counts()
    else:
        grouped_data[ORIGIN_DESTINATION] = month_bike_data["end_station_name"].value_counts()
    grouped_data[ORIGIN_DESTINATION] = grouped_data[ORIGIN_DESTINATION].fillna(0)

    return grouped_data

def get_ordered_rides(geospacial_w_rides):
    if ORIGIN_DESTINATION == "Number of Rides Started":
        station_direction = "Origin Station"
    else:
        station_direction = "End Station"
    sorted_rides = geospacial_w_rides.reset_index()[["index", ORIGIN_DESTINATION]].copy().sort_values(
        ORIGIN_DESTINATION,
        ascending=False).rename(columns={"index": station_direction, ORIGIN_DESTINATION: "Trips"})
    sorted_rides = sorted_rides.loc[sorted_rides["Trips"] > 0]
    return sorted_rides


# read and format data
indexurl = "https://s3.amazonaws.com/hubway-data"
tripdata = get_all_tripdata(indexurl)

# set a starting month value - going with most recent
tripmonth = list(tripdata.keys())[-1]
bike_data = get_bike_data(tripdata[tripmonth])

# get station locations based on averages
station_locations = pd.read_csv("../data/geospacial_station_data.csv",
                                index_col=0, usecols=["index","lat","lng","City"])


# get the stations with the most rides
combined_station_data  = get_ride_sum(station_locations,bike_data)
ordered_rides = get_ordered_rides(combined_station_data)

## separate dash variable for table view
dtable = dash_table.DataTable(
    sort_action="native",
    page_size=10,
    style_table={"overflowX": "auto"},
    style_cell={
        'textAlign': 'left'
    }
)


#### Setup for the app
app.layout = html.Div(
    [
        html.H2("Visualization of Bluebikes trip data"),
        html.H4("Developed by Michaela Olson"),
        html.P(
            "Select a month of Bluebike trip data to view, then click on a station to see all of the destinations from that station (minimum of " + str(threshold) + " trips for visualization). Toggle the slider to change from visualizing stations by trips originating from the station to trips ending at the station."
        ),
        dcc.Dropdown(
            id="year-dropdown",
            options=list(reversed(tripdata.keys())),
            value=tripmonth,
            clearable=False,
        ),
        dcc.RangeSlider(0, 24, 1, value=[0, 24], id='hour-range'),
        daq.BooleanSwitch(id='origin-destination-switch', on=False,
                          label="Off = Number of trips originating from station. On = Number of trips ending at station.",
                          labelPosition="top"
                          ),
        html.Div(id = "graph-container",
                 children=[
                    dcc.Graph(id="graph2"),
                    dcc.Loading(
                        id="loading-1",
                        type="default",
                        children=html.Div(id="loading-output-1")
                    )
                 ]
        ),
        html.Div(
            html.Pre(id='click-data', style=styles['pre'])
        ),
        dtable,
        html.Div([
            html.Footer("Code publicly available at ", style={"display":"inline"}),
            html.A("github.com/michaelaesquire/bluebike-viz",href="https://github.com/michaelaesquire/bluebike-viz")
            ]
        ),
        html.Div([
            html.Footer("Bluebikes trip data publicly available at ", style={"display":"inline"}),
            html.A("bluebikes.com/system-data",href="https://bluebikes.com/system-data")
            ]
        )
    ]
)

@app.callback(
    Output('graph2', 'figure'),
    Output(dtable, "data"),
    Output("loading-output-1", "children"),
    Output('click-data', 'children'),
    Input('graph2', 'clickData'),
    Input("year-dropdown", "value"),
    Input("origin-destination-switch","on"),
    Input('hour-range', 'value')
  #  Input(dtable, 'active_cell')
)
def display_bike_trips(clickData, yearval, origin_destination, hour_range):
    global tripmonth
    global bike_data
    global combined_station_data
    global ordered_rides
    global ORIGIN_DESTINATION

    # find out what was changed for the callback
    ctx = callback_context
    clicked = ctx.triggered[0]['prop_id'].split('.')[0]

    if origin_destination:
        ORIGIN_DESTINATION = "Number of Rides Ended"
    else:
        ORIGIN_DESTINATION = "Number of Rides Started"
    # print(clicked == "")
    num_trips_formatted = "{0:,.0f}".format(bike_data.shape[0])
   # if clicked_cell is not None:
        #print(ordered_rides.iloc[clicked_cell['row'],clicked_cell['column']])
    #if clicked == "origin-destination-switch":
    combined_station_data = get_ride_sum(station_locations,
                                         bike_data.loc[bike_data["start hour"].between(hour_range[0],hour_range[1])])
    ordered_rides = get_ordered_rides(combined_station_data)

    # this means the year was changed - do callback based on that
    if clicked == "year-dropdown":
        # means read in new data
        tripmonth = yearval
        # del bike_data
        # gc.collect()

        bike_data = get_bike_data(tripdata[tripmonth])
        num_trips_formatted = "{0:,.0f}".format(bike_data.shape[0])
        # add on the number of rides from the month
        combined_station_data  = get_ride_sum(station_locations,
                                              bike_data.loc[bike_data["start hour"].between(hour_range[0],hour_range[1])])
        ordered_rides = get_ordered_rides(combined_station_data)

    printstr = num_trips_formatted + " total trips in " + tripmonth
    fig = px.scatter_mapbox(combined_station_data.loc[combined_station_data[ORIGIN_DESTINATION]>0].reset_index(),
                            lat="lat",
                            lon="lng",
                            hover_name="index",
                            color_discrete_map=city_pal,
                            color="City",
                            hover_data="index",
                            size=ORIGIN_DESTINATION,
                            zoom=11,
                        #    height=600,
                          #  width=1000
                            )
    # this is the callback for a click
    if clicked == "graph2":
        if isinstance(clickData["points"][0]["customdata"], str):
            start_station = clickData["points"][0]["customdata"]
        else:
            start_station = clickData["points"][0]["customdata"][0]


        if origin_destination:
            trips_to = bike_data.loc[(bike_data["end_station_name"] == start_station) & bike_data["start hour"].between(hour_range[0],hour_range[1])]["start_station_name"].value_counts()
            ordered_rides = trips_to.reset_index().rename(columns={"start_station_name": "Trip Origin Station",
                                                                   "count": "Trips"})
            printstr = "Destination: " + start_station + " (" + str(
                int(combined_station_data.loc[start_station, ORIGIN_DESTINATION])) + " total trips)"

        else:
            trips_to = bike_data.loc[(bike_data["start_station_name"] == start_station) & bike_data["start hour"].between(hour_range[0],hour_range[1])]["end_station_name"].value_counts()
            ordered_rides = trips_to.reset_index().rename(columns={"end_station_name": "Trip Destination Station",
                                                                   "count": "Trips"})
            printstr = "Origin: " + start_station + " (" + str(
                int(combined_station_data.loc[start_station, ORIGIN_DESTINATION])) + " total trips)"

        norm_trip2 = NormalizeData(trips_to)
        trips_to_above = trips_to.loc[trips_to > threshold]

        for trip in reversed(trips_to_above.index):
            trip_text = trip + " (" + str(trips_to_above[trip]) + " trips)"
            end_station = trip
            fig.add_trace(go.Scattermapbox(
                name=strtobr(trip_text),
                mode="lines",
                opacity=0.8,
                customdata=[start_station, end_station],
                lon=[combined_station_data.loc[start_station]["lng"], combined_station_data.loc[end_station]["lng"]],
                lat=[combined_station_data.loc[start_station]["lat"], combined_station_data.loc[end_station]["lat"]],
                hovertext=strtobr(trip_text),
                line={'width': np.floor(trips_to_above[trip] / 10 + 1),
                      "color": mcolors.rgb2hex(cmap(norm_trip2[trip]))},
                showlegend=False
            ),

            )

    fig.update_layout(
        margin={"l":30, "r": 30, "t":30, "b":20},
    )
    return fig, ordered_rides.to_dict("records"), None, printstr


if __name__ == '__main__':
    app.run(debug=True)
