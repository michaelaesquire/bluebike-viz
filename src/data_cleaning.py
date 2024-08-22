import pandas as pd
from datetime import datetime
import geopy.distance


station_data = pd.read_csv("../data/current_bluebikes_stations.csv",
                           index_col="NAME",
                           skiprows=1)

# set name of data
month = "202402"
data_name = month+ "-bluebikes-tripdata"
bike_data = pd.read_csv("../data/rawtripdata/" + data_name +".csv", index_col = 0).dropna()

# make a column that combines start and end info
bike_data["Start End"] = bike_data["start_station_name"] + " to " + bike_data["end_station_name"]

# some have times in a different format - find a way to dynamically check?
start_time = bike_data.iloc[0]['started_at']
# if there's a period, then it has miliseconds, if not
if "." in start_time:
    conversion = "%Y-%m-%d %H:%M:%S.%f"
else:
    conversion = "%Y-%m-%d %H:%M:%S"

triplens = dict()
tripdist = dict()
starthours = dict()
timeofday = dict()

for rideid in bike_data.index:
    start_time = bike_data.loc[rideid]['started_at']
    end_time = bike_data.loc[rideid]['ended_at']

    diff = (datetime.strptime(end_time, conversion) - datetime.strptime(start_time, conversion)).total_seconds()
    triplens[rideid] = diff
    starthour = datetime.strptime(start_time, conversion).hour
    starthours[rideid] = starthour

    #  startlat = bike_data.loc[rideid]['start_lat']
    coords_1 = (bike_data.loc[rideid]['start_lat'], bike_data.loc[rideid]['start_lng'])
    coords_2 = (bike_data.loc[rideid]['end_lat'], bike_data.loc[rideid]['end_lng'])
    tripdist[rideid] = geopy.distance.geodesic(coords_1, coords_2).miles

# add on the new columns
bike_data["Trip Length"] = triplens
bike_data["Distance Between Stations"] = tripdist
bike_data["Start Hour"] = starthours


# time of day categories
time_of_day_dict = {
    0:"Night",
    1:"Night",
    2:"Night",
    3:"Night",
    4:"Night",
    5:"Morning",
    6:"Morning",
    7:"Morning",
    8:"Morning",
    9:"Morning",
    10:"Morning",
    11:"Lunch",
    12:"Lunch",
    13:"Lunch",
    14:"Evening",
    15:"Evening",
    16:"Evening",
    17:"Evening",
    18:"Evening",
    19:"Evening",
    20:"Evening",
    21:"Night",
    22:"Night",
    23:"Night",
    24:"Night",
}

bike_data["Trip Length (min)"] = bike_data["Trip Length"]/60

bike_data["Time of Day"] = [time_of_day_dict[x] for x in bike_data["Start Hour"]]

# use station data for this last bit
# get station locations based on averages
# station_locations = pd.read_csv("../data/geospacial_station_data_" + month + ".csv",
#                                 index_col=0)
# # this has the station data
# combined_station_data = station_locations.merge(station_data,
#                                                 left_index=True, right_index=True, how = "left")
# station_to_city = combined_station_data.to_dict()["City"]
#
# bike_data["Start City"] = [station_to_city[x] for  x in bike_data["start_station_name"]]
# bike_data["End City"] = [station_to_city[x] for  x in bike_data["end_station_name"]]

# save as cleaned
bike_data.to_csv("../data/tripdata/" + data_name + "_cleaned.csv")