from flask import Flask, render_template

app = Flask(__name__)
temp = 5


# CIT 381 - Spring 2024
# Author: Cassian Godsted
# Created: April 16th, 2024
# Lab 10, Part 3 - Determines whether or not irrigation is needed based on data from AccuWeather. This data is then logged, displayed, and activates a relay.

# Standard imports
import json
import time
import urllib.request


#Define API and location variables.
API = ""
COUNTRY_CODE = "us"
LOCATION_CODE = "17810_PC"
ZIP_CODE = 41076
apiurl = "http://dataservice.accuweather.com/currentconditions/v1/%s?apikey=%s" % (LOCATION_CODE, API)

# Functions that handle requesting data from AccuWeather
def accuweather(endpoint):
    # 1 - Request location code from ZIP code and country code.
    if endpoint == "location":
        apiurl = "http://dataservice.accuweather.com/locations/v1/postalcodes/%s/search?apikey=%s&q=%s&details=true" % (COUNTRY_CODE, API, ZIP_CODE)
    
    # 2 - Request current conditions for a location code.
    elif endpoint == "current":
        apiurl = "http://dataservice.accuweather.com/currentconditions/v1/%s?apikey=%s&details=true" % (LOCATION_CODE, API)

    # 3 - Request conditions of the last 24 hours for a location code.
    elif endpoint == "recent":
        apiurl = "http://dataservice.accuweather.com/currentconditions/v1/%s/historical/24?apikey=%s&details=true" % (LOCATION_CODE, API)
    # 4 - Requests five day forecast for a location code
    elif endpoint == "future":
        apiurl = "http://dataservice.accuweather.com/forecasts/v1/daily/5day/%s?apikey=%s&details=true" % (LOCATION_CODE, API)

    # Make request
    with urllib.request.urlopen(apiurl) as url:
        data = json.loads(url.read().decode())
        return data


# Main function.
def processLabData():
    # 1. Request percipitation in the last 24 hours.
    data = requestData("recent")
    recentData = processRecentData(data)
    # 2. Request current percipitation.
    data = requestData("current")
    currentData = processCurrentData(data)
    # 3. Request future percipitation.
    data = requestData("future")
    futureData = processFutureData(data)
    if (recentData + currentData + futureData) == 0:
        print("Irrigating")
    elif (recentData):
        print("Not irrigating, as it has rained enough in the last 24 hours.")
        # thelcd.lcd_display_string("Not Irrigating", 2)
    elif (currentData):
        print("Not irrigating, as it is currently raining.")  
    elif (futureData):
        print("Not irrigating, as it is predicted to rain in the next 24 hours.")
    

# Process weather data from last 24 hours.
def processRecentData(data):
    substantialRain = False
    # Find inches rained in the last 24 hours.
    inchesRained = data[0]["PrecipitationSummary"]["Past24Hours"]["Imperial"]["Value"]
    # thelcd.lcd_display_string(f"Rain: {inchesRained}in")
    if inchesRained > 0.15:
        substantialRain = True
    return substantialRain

# Process weather data from last 24 hours.
def processOutsideTemperature(data):
    # Find inches rained in the last 24 hours.
    temperature = data[0]["Temperature"]["Imperial"]["Value"]
    return temperature


# Process current weather data
def processCurrentData(data):
    # Find if its currently raining. In this case, any rain is "substantial rain."
    substantialRain = data[0]["HasPrecipitation"]
    return substantialRain

# Process current weather data
def processFutureData(data):
    substantialRain = False
    # Find percentage chance of rain and amount of rain estimated.
    precipitationProbability = data["DailyForecasts"][0]["Day"]["PrecipitationProbability"]
    inchesRained = data["DailyForecasts"][0]["Day"]["TotalLiquid"]["Value"]
    # Chance of Precipitation needs to be higher than 70% to be considered substantial.
    if precipitationProbability > 70:
        # Amount of rain needs to be more than 0.15 inches to be considered substantial.
        if inchesRained > 0.15:
            substantialRain = True
    return substantialRain

# Requests weather data from AccuWeather and store it as JSON.
def requestData(requestTo):
    data = accuweather(requestTo)
    with open(f"{requestTo}.json", 'w') as f:
        json.dump(data, f, indent=2) 
        return data
        
# Test code that reads weather from local files.
def loadData(requestTo):
    try:
        with open(f"{requestTo}.json", 'r') as f:
            data = json.load(f)
            return data
    # If requested weather data is not cached, request it from Accuweather.
    except:
        data = requestData(requestTo)
    return data

@app.route('/')
def index():
    data = requestData("recent")
    temp = processOutsideTemperature(data)
    return render_template('index.html', temp=temp)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
    