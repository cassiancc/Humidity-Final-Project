# TODO - Matthias - Automatically make Accuweather requests every 24 hours.
# TODO - Cassian - Improve dashboard design
# TODO - Cassian - Make location data configurable in frontend.
# TODO - Matthias - Build function to handle location data change.

# Standard imports
import time
import adafruit_dht
import board
import json
import urllib.request
from flask import Flask, render_template

# Setup Flask app and DHT device.
app = Flask(__name__)
temp = 5

dhtEnabled = False

if dhtEnabled == True:
    dht_device = adafruit_dht.DHT22(board.D4)


def readAPIKey():
    with open(f"key.txt", 'r') as f:
        return f.read()
                
#Define API and location variables.
API = readAPIKey()

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
def processRainData():
    # 2. Request current percipitation.
    data = loadData("current")
    currentData = processCurrentData(data)
    # 3. Request future percipitation.
    data = loadData("future")
    futureData = processFutureData(data)
    if (currentData + futureData) == 0:
        return "It is not currently raining"
    elif (currentData):
        return "It is currently raining."
    elif (futureData):
        return "It is predicted to rain in the next 24 hours."

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
        print("Data not cached")
        # data = requestData(requestTo)
    return data

@app.route('/')
def index():
    data = loadData("recent")
    if dhtEnabled == True:
        try:
            temperature_c = dht_device.temperature
            temperature_f = temperature_c * (9 / 5) + 32
            humidity = dht_device.humidity
            print("Temp:{:.1f} C / {:.1f} F    Humidity: {}%".format(temperature_c, temperature_f, humidity))
        except RuntimeError as err:
            print(err.args[0])
            time.sleep(2.0)
            temperature_c = 0
            temperature_f = 0
    else:
        temperature_f = "60"
    # TODO - READ DATE FROM JSON, BEAUTIFY
    date = "2024-04-26T14:00:00-04:00"
    # TODO - READ AND PAD ICON ID FROM JSON
    icon = "01"
    return render_template('index.html', temp=processOutsideTemperature(data), rain=processRainData(), local=temperature_f, datetime=date, icon=icon)

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5500)
    