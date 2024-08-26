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
import matplotlib.colors as mcolors
from matplotlib import colormaps
#from matplotlib.patches import Patch
#from matplotlib.colors import LogNorm, Normalize
import json
#from meteostat import Point, Daily, Hourly

#from datetime import datetime, timedelta


app = Dash()

server = app.server

## read in station data
station_data = pd.read_csv("../data/current_bluebikes_stations.csv",
                           index_col="NAME",
                           skiprows=1)
threshold = 8

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

# start mapbox
maptoken = open(".mapbox").read()
px.set_mapbox_access_token(maptoken)

# read and format data
month = "202407"
data_name = month + "-bluebikes-tripdata"
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

# get the stations in order of most used
most_used_order = combined_station_data.sort_values("Number of Rides Started", ascending=False).index


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

styles = {
    'pre': {
        'border': 'thin lightgrey solid',
        'overflowX': 'scroll'
    }
}
#### This works for rn
app.layout = html.Div(
    [
        html.H3("Bluebikes data"),
        html.P(
            "Click on a station to see all of the destinations from that station. (min " + str(threshold) + " trips)"
        ),
        # html.P(
        #     "Select origin station."
        # ),
        # dcc.Dropdown(
        #     id="type",
        #     options=list(most_used_order),
        #     value=most_used_order[0],
        #     clearable=False,
        # ),
   #     dcc.Graph(id="graph"),
        dcc.Graph(id="graph2"),
       # html.Div(className='row', children=[
       #  html.Div([
       #      dcc.Markdown("""
       #          **Hover Data**
       #
       #          Click on points in the graph.
       #      """),
       #      html.Pre(id='click-data', style=styles['pre'])
       #  ], className='three columns')]
       #           )


    ]
)


@app.callback(
    Output('graph2', 'figure'),
    Input('graph2', 'clickData'))
def display_bike_trips(clickData):

    fig = px.scatter_mapbox(combined_station_data.reset_index(),
                            lat="lat",
                            lon="lng",
                            hover_name="index",
                            color_discrete_map=city_pal,
                            color="City",
                            hover_data="index",
                            size="Number of Rides Started",
                            zoom=11,
                            height=800,
                            width=1000)

    if clickData is not None:

        if isinstance(clickData["points"][0]["customdata"], str):
            target_station = clickData["points"][0]["customdata"]
        else:
            target_station = clickData["points"][0]["customdata"][0]

        trips_to = bike_data.loc[bike_data["start_station_name"] == target_station]["end_station_name"].value_counts()
        norm_trip2 = NormalizeData(trips_to)
        cmap = colormaps["magma"]
        trips_to = trips_to.loc[trips_to > threshold]
        start_station = target_station
        for trip in reversed(trips_to.index):
            trip_text = trip + " (" + str(trips_to[trip]) + " trips)"
            end_station = trip
            fig.add_trace(go.Scattermapbox(
                name=strtobr(trip_text),
                mode="lines",
                opacity=0.8,
                customdata=[start_station, end_station],
                lon=[combined_station_data.loc[start_station]["Long"], combined_station_data.loc[end_station]["Long"]],
                lat=[combined_station_data.loc[start_station]["Lat"], combined_station_data.loc[end_station]["Lat"]],
                hovertext=strtobr(trip_text),
                line={'width': np.floor(trips_to[trip] / 10 + 1),
                      "color": mcolors.rgb2hex(cmap(norm_trip2[trip]))},
                showlegend=False
            ),

            )
    return fig



# @app.callback(
#     Output("graph", "figure"),
#     Input("type", "value"),
# )
#
# def generate_chart(target_station):
#     ## read in data
#     # current config to July 2024
#
#     fig = px.scatter_mapbox(combined_station_data.reset_index(),
#                             lat="lat",
#                             lon="lng",
#                             hover_name="index",
#                             color_discrete_map=city_pal,
#                             color="City",
#                             hover_data=["index", "Number of Rides Started"],
#                             # color_continuous_scale=color_scale,
#                             size="Number of Rides Started",
#                             zoom=11,
#                             height=800,
#                             width=1000)
#     # fig.update_traces(
#     #     hovertemplate=None,
#     #     hoverinfo='skip'
#     # )
#
#     trips_to = bike_data.loc[bike_data["start_station_name"] == target_station]["end_station_name"].value_counts()
#     norm_trip2 = NormalizeData(trips_to)
#     cmap = colormaps["magma"]
#     trips_to = trips_to.loc[trips_to > 8]
#     start_station = target_station
#     for trip in reversed(trips_to.index):
#         trip_text = trip + " (" + str(trips_to[trip]) + " trips)"
#         end_station = trip
#         fig.add_trace(go.Scattermapbox(
#             name=strtobr(trip_text),
#             mode="lines",
#             opacity=0.8,
#             customdata=[start_station, end_station],
#             lon=[combined_station_data.loc[start_station]["Long"], combined_station_data.loc[end_station]["Long"]],
#             lat=[combined_station_data.loc[start_station]["Lat"], combined_station_data.loc[end_station]["Lat"]],
#             hovertext=strtobr(trip_text),
#             line={'width': np.floor(trips_to[trip] / 10 + 1),
#                   "color": mcolors.rgb2hex(cmap(norm_trip2[trip]))},
#             showlegend=False
#             ),
#
#         )
#
#     # fig.update_layout(mapbox_style="open-street-map")
#     #fig.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0})
#     # fig.update_traces(mode="lines", hovertemplate=None)
#     # fig.update_layout(hovermode="x")
#
#     # fig.show()
#
#     return fig

if __name__ == '__main__':
    app.run(debug=True)
