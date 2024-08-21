from dash import Dash, html
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import numpy as np
import scipy
from datetime import datetime
import geopy.distance
from geopy.geocoders import Nominatim
import plotly.express as px
import plotly.graph_objects as go
import random
import matplotlib.colors as mcolors
from matplotlib.patches import Patch
from matplotlib.colors import LogNorm, Normalize

from meteostat import Point, Daily, Hourly

from datetime import datetime, timedelta


app = Dash()

## read in station data
station_data = pd.read_csv("./data/current_bluebikes_stations.csv",
                           index_col="NAME",
                           skiprows=1)


app.layout = [html.Div(children='Hello World')]

if __name__ == '__main__':
    app.run(debug=True)
