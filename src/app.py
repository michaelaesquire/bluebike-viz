from dash import Dash, html, dcc, Input, Output
import pandas as pd
#import seaborn as sns
#import matplotlib.pyplot as plt
import numpy as np
#import scipy
#from datetime import datetime
#import geopy.distance
#from geopy.geocoders import Nominatim
import plotly.express as px
import plotly.graph_objects as go
#import random
#import matplotlib.colors as mcolors
#from matplotlib.patches import Patch
#from matplotlib.colors import LogNorm, Normalize

#from meteostat import Point, Daily, Hourly

#from datetime import datetime, timedelta


app = Dash()

## read in station data
station_data = pd.read_csv("../data/current_bluebikes_stations.csv",
                           index_col="NAME",
                           skiprows=1)


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


#### This works for rn


app.layout = html.Div(
    [
        html.H4("Airports"),
        html.P(
            "px.scatter_geo is used to plot points on globe across geolocations while "
            "px.scatter_mapbox is used to plot points on map across geolocations."
        ),
        dcc.Graph(id="graph"),
        html.P(
            "Enter the type of graph you want to plot: (scatter_geo or scatter_mapbox)"
        ),
        dcc.Dropdown(
            id="type",
            options=["202407", "202402"],
            value="202407",
            clearable=False,
        ),
    ]
)

@app.callback(
    Output("graph", "figure"),
    Input("type", "value"),
)
def generate_chart(values):
    ## read in data
    # current config to July 2024
    month = values
    data_name = values + "-bluebikes-tripdata"
    bike_data = pd.read_csv("../data/tripdata/" + data_name + "_cleaned.csv", index_col=0).dropna()

    # get station locations based on averages
    station_locations = pd.read_csv("../data/geospacial_station_data_" + month + ".csv",
                                    index_col=0)
    # this has the station data
    combined_station_data = station_locations.merge(station_data,
                                                    left_index=True, right_index=True, how="left")
    # combine city data w ride data
    station_to_city = combined_station_data.to_dict()["City"]

    bike_data["Start City"] = [station_to_city[x] for x in bike_data["start_station_name"]]
    bike_data["End City"] = [station_to_city[x] for x in bike_data["end_station_name"]]

    # times of day
    times_of_day = bike_data["Time of Day"].unique()
    combined_station_data["Number of Rides Started"] = bike_data["start_station_name"].value_counts()
    # if there wasn't any rides started, it'll be nan -> fix
    combined_station_data["Number of Rides Started"] = combined_station_data["Number of Rides Started"].fillna(0)

    for daytime in times_of_day:
        combined_station_data["Number of Rides Started at " + daytime] = \
        bike_data.loc[bike_data["Time of Day"] == daytime]["start_station_name"].value_counts()
        combined_station_data["Number of Rides Started at " + daytime] = combined_station_data[
            "Number of Rides Started at " + daytime].fillna(0)

    threshold = 180
    moved = bike_data.loc[bike_data["start_station_name"] != bike_data["end_station_name"]]
    larger_trips = moved["Start End"].value_counts()[moved["Start End"].value_counts() > threshold]

    norm_trip = NormalizeData(larger_trips)

    fig = px.scatter_mapbox(combined_station_data.reset_index(),
                            lat="lat",
                            lon="lng",
                            hover_name="index",
                            color="City",
                            hover_data=["index", "Number of Rides Started at Morning"],
                            # color_continuous_scale=color_scale,
                            size="Number of Rides Started at Morning",
                            zoom=11,
                            height=800,
                            width=1000)
    fig.update_traces(
        hovertemplate=None,
        hoverinfo='skip'
    )

    for trip in larger_trips.index:
        trip_text = trip + " (" + str(larger_trips[trip]) + " trips)"

        start_station = bike_data.loc[bike_data["Start End"] == trip]["start_station_name"].iloc[0]
        end_station = bike_data.loc[bike_data["Start End"] == trip]["end_station_name"].iloc[0]
        fig.add_trace(go.Scattermapbox(
            name=strtobr(trip_text),
            mode="lines",
            lon=[combined_station_data.loc[start_station]["Long"], combined_station_data.loc[end_station]["Long"]],
            lat=[combined_station_data.loc[start_station]["Lat"], combined_station_data.loc[end_station]["Lat"]],
            hovertext=strtobr(trip_text),
            line={'width': (norm_trip[trip] + .3) * 12},
            showlegend=False),

        )

    # fig.update_layout(mapbox_style="open-street-map")
    fig.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0})
    # fig.update_traces(mode="lines", hovertemplate=None)
    # fig.update_layout(hovermode="x")

    # fig.show()

    return fig

if __name__ == '__main__':
    app.run(debug=True)
