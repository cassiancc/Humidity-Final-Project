# TODO - Cassian - Improve dashboard design
# TODO - Cassian - Make location data configurable in frontend.

# Standard imports
import time
import datetime
import threading
import json
import urllib.request
from flask import Flask, render_template

# Setup Flask app and DHT device.
app = Flask(__name__)
temp = 5

dhtEnabled = True

if dhtEnabled == True:
    import adafruit_dht
    import board
    dht_device = adafruit_dht.DHT22(board.D4)

def readAPIKey():
    with open(f"key.txt", 'r') as f:
        return f.read()
                
#Define API and location variables.
API = readAPIKey()

COUNTRY_CODE = None
LOCATION_CODE = None
ZIP_CODE = None
apiurl = "http://dataservice.accuweather.com/currentconditions/v1/%s?apikey=%s" % (LOCATION_CODE, API)

# TODO Below should be configurable through dashboard
refreshOnAccess = False
precipitationProbabilityMax = 70
# Above maxTemp we suggest to close doors and turn on the AC
maxTemp = 80
# Between minTemp and maxTemp we open doors
minTemp = 65
# Below minTemp we close doors

# Lock for refreshing AccuWeather data
lock = threading.Lock()

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

    # 5 - Requests 1 hour forecast for a location code
    elif endpoint == "future1hour":
        apiurl = "http://dataservice.accuweather.com/forecasts/v1/hourly/1hour/%s?apikey=%s&details=true" % (LOCATION_CODE, API)

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
        return "It is not currently raining."
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

def findOutsideIcon(data):
    icon = data[0]["WeatherIcon"]
    icon = f'{icon:02}'
    return icon

# Process current weather data
def processCurrentData(data):
    # Find if its currently raining. In this case, any rain is "substantial rain."
    substantialRain = data[0]["HasPrecipitation"]
    return substantialRain

# Process future weather data
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

# Get future temperature from 1 hour forecast
def getFutureTemperature1Hour(data):
    return data[0]["Temperature"]["Value"]

# Get substantial rain from 1 hour forecast
def getFutureSubstantialRain(data):
    # Find percentage chance of rain and amount of rain estimated.
    precipitationProbability = data[0]["PrecipitationProbability"]
    # Chance of Precipitation needs to be higher than max to be considered substantial.
    return precipitationProbability > precipitationProbabilityMax

def getCurrentZipAndCountryCode():
    with urllib.request.urlopen("https://ipapi.co/json") as url:
        data = json.loads(url.read().decode())
    global COUNTRY_CODE
    global ZIP_CODE
    COUNTRY_CODE = data["country_code"].lower()
    ZIP_CODE = data["postal"]

def setLocationCode(countryCode: str, zipCode: str):
    global COUNTRY_CODE
    global ZIP_CODE
    global LOCATION_CODE
    COUNTRY_CODE = countryCode
    ZIP_CODE = zipCode
    data = loadData("location")
    LOCATION_CODE = data[0]["Key"]

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
        data = requestData(requestTo)
    return data

# Logic to decide whether to open or close doors
def updateDoors():
    accuWeatherDataCurrent = loadData("current")
    raining = processCurrentData(accuWeatherDataCurrent)
    # within the next hour
    currentTemp = processOutsideTemperature(accuWeatherDataCurrent)
    doors = ""
    # Determine whether to open/close doors right now
    if raining:
        doors = closeDoors(reason="It is currently raining")
    elif currentTemp > maxTemp:
        doors = closeDoors(reason="The current temperature is too hot")
    elif currentTemp < minTemp:
        doors = closeDoors(reason="The current temperature is too cold")
    else:
        doors = openDoors(reason="The current temperature is preferred")
    return doors
# Logic to decide whether to open or close doors

def updateFutureDoors():
    accuWeatherDataFuture = loadData("future1hour")
    # within the next hour
    willRain = getFutureSubstantialRain(accuWeatherDataFuture)
    futureTemp = getFutureTemperature1Hour(accuWeatherDataFuture)
    Fdoors = ""
    # Determine whether to open/close doors in 1 hour
    if willRain:
        Fdoors = warnCloseDoors(reason="It is likely to rain within the next hour")
    elif futureTemp > maxTemp:
         Fdoors = warnCloseDoors(reason="The future temperature is too hot")
    elif futureTemp < minTemp:
         Fdoors = warnCloseDoors(reason="The future temperature is too cold")
    else:
         Fdoors = warnOpenDoors(reason="The future temperature is preferred")
    return Fdoors

# TODO Display these messages on webpage

def openDoors(reason: str):
    return f"{reason}. You should open your doors and windows now. "

def closeDoors(reason: str):
    return f"{reason}. You should close your doors and windows now. "

def warnOpenDoors(reason: str):
    return f"{reason}. You should open your doors and windows within the next hour."

def warnCloseDoors(reason: str):
    return f"{reason}. You should close your doors and windows within the next hour. "

# TODO Activatable through dashboard
# Refresh AccuWeather data
def refreshAccuWeather():
    lock.acquire()
    requestData("recent")
    requestData("current")
    requestData("future")
    requestData("future1hour")
    print("AccuWeather data refreshed")
    updateDoors()
    lock.release()

# Refresh AccuWeather data every hour
def refreshAccuWeatherLoop():
    now = datetime.datetime.now()
    # Calculate seconds left until next hour mark
    secUntilHour = (60 * 60) - (now.second + now.minute * 60)
    print(f"Will refresh data in {secUntilHour / 60:.2f} minutes")
    time.sleep(secUntilHour)
    while True:
        refreshAccuWeather()
        time.sleep(60 * 60)

# Create thread to run AccuWeather refresh data loop
def startRefreshLoop():
    threading.Thread(target=refreshAccuWeatherLoop, daemon=True).start()

@app.route('/')
def index():
    if refreshOnAccess:
        refreshAccuWeather()
    data = loadData("recent")
    if dhtEnabled == True:
        try:
            temperature_c = dht_device.temperature
            temperature_f = temperature_c * (9 / 5) + 32
            humidity = dht_device.humidity
            print("Temp:{:.1f} C / {:.1f} F    Humidity: {}%".format(temperature_c, temperature_f, humidity))
        except RuntimeError as err:
            print(err.args[0])
            temperature_c = 0
            temperature_f = 0
            humidity = 0
            time.sleep(3.0)
            temperature_c = dht_device.temperature
            temperature_f = temperature_c * (9 / 5) + 32
            humidity = dht_device.humidity
            print("Temp:{:.1f} C / {:.1f} F    Humidity: {}%".format(temperature_c, temperature_f, humidity))
            
    else:
        temperature_f = "60"
    # TODO - READ DATE FROM JSON, BEAUTIFY
    date = "2024-04-26T14:00:00-04:00"
    # TODO - READ AND PAD ICON ID FROM JSON
    return render_template('index.html', temp=processOutsideTemperature(data), insideHumidity=humidity, doors=updateDoors(), Fdoors=updateFutureDoors(), rain=processRainData(), local=temperature_f, datetime=date, icon=findOutsideIcon(data))

if __name__ == '__main__':
    getCurrentZipAndCountryCode()
    startRefreshLoop()
    app.run(debug=False, host='0.0.0.0', port=5500)
    