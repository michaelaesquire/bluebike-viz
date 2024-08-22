import pandas as pd
from geopy.geocoders import Nominatim

#initialize geolocator
geolocator = Nominatim(user_agent='c.michaela.olson@gmail.com')

station_data = pd.read_csv("../data/current_bluebikes_stations.csv", index_col="NAME",skiprows=1)

# set name of data
month = "202402"
data_name = month + "-bluebikes-tripdata"
bike_data = pd.read_csv("../data/rawtripdata/" + data_name +".csv", index_col = 0).dropna()

all_stations = list(set(pd.concat([bike_data["end_station_name"],bike_data["start_station_name"]])))


all_starts = bike_data.loc[bike_data["start_station_name"].isin(all_stations)].drop_duplicates(subset="start_station_name")[["start_station_name","start_lat","start_lng"]].set_index("start_station_name")
all_starts.rename(columns={"start_lat":"lat","start_lng":"lng"},inplace=True)
all_ends = bike_data.loc[bike_data["end_station_name"].isin(all_stations)].drop_duplicates(subset="end_station_name")[["end_station_name","end_lat","end_lng"]].set_index("end_station_name")
all_ends.rename(columns={"end_lat":"lat","end_lng":"lng"},inplace=True)

# take the mean of the varied options
station_locations = pd.concat([all_starts,all_ends]).reset_index().groupby("index").mean()

# don't need to re-run this regularly and query the server
#location = geolocator.reverse(station_locations.loc[" Broadway and Cabot"])
all_locations = dict()
for station in station_locations.index:
    location = geolocator.reverse(station_locations.loc[station][["lat","lng"]])
    all_locations[station] = location.raw['address']


# don't need to re-run this regularly and query the server
station_locations["Full Location"] = all_locations

cities = dict()
zipcodes = dict()
for key in all_locations:
    if "city" in all_locations[key].keys():
        cities[key] = all_locations[key]["city"]
    else:
        cities[key] = all_locations[key]["town"]
    try:
        zipcodes[key] = all_locations[key]["postcode"]
    except:
        print(key)
        zipcodes[key] = "No zip code"

station_locations["City"] = cities
station_locations["Zipcode"] = zipcodes
# overwrite for ashmont T stop

station_locations.loc["Ashmont T Stop", "Zipcode"] = "02124"

station_locations.to_csv("../data/geospacial_station_data_" + month + ".csv")