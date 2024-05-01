# Standard imports
import time, datetime, threading, json, urllib.request, os
from flask import Flask, render_template, request, url_for, redirect

# Setup Flask app
app = Flask(__name__)
# Prevent forms from being used outside of the dashboard's intended use.
app.config['SECRET_KEY'] = os.urandom(24).hex()    
temp = 5
# Default to Farenheit
units = "F"
# Above maxTemp we suggest to close doors and turn on the AC
maxTemp = 80
# Below minTemp we close doors, between we open doors.
minTemp = 65
# Refresh Accuweather whenever the page is accessed - mostly for debugging.
refreshOnAccess = False
# Maximum chance of rain.
precipitationProbabilityMax = 70
# User's ZIP code
zip_code = None


@app.route('/settings/', methods=('GET', 'POST'))
def create():
    if request.method == 'POST':
        if 'metric' in request.form:
            global units
            units = "C"
        else:
            units = "F"
        if "zip" in request.form:
            if request.form["zip"] != "":
                print(f"Zip value {request.form['zip']}")
                global zip_code
                zip_code = request.form['zip']
        if "mintemp" in request.form:
            if request.form["mintemp"] != "":
                global minTemp
                minTemp = float(request.form["mintemp"])
        if "maxtemp" in request.form:
            if request.form["maxtemp"] != "":
                global maxTemp
                maxTemp = float(request.form["maxtemp"])
        if "maxrain" in request.form:
            if request.form["maxrain"] != "":
                global precipitationProbabilityMax
                precipitationProbabilityMax = float(request.form["maxrain"])
        return redirect(url_for('index'))
    return render_template('settings.html')




@app.route('/reload/', methods=('GET', 'POST'))
def reloadFrontend():
    if request.method == 'POST':
        refreshAccuWeather()
        return redirect(url_for('index'))



# While testing, allow for disabling DHT-22 to prevent crashes.
dhtEnabled = True

# Set up DHT-22
if dhtEnabled == True:
    import adafruit_dht
    import board
    try:
        dht_device = adafruit_dht.DHT22(board.D4)
    except RuntimeError as err:
        print(err)
        dhtEnabled = False

def readAPIKey():
    with open(f"key.txt", 'r') as f:
        return f.read()
                
#Define API and location variables.
API = readAPIKey()

COUNTRY_CODE = None
LOCATION_CODE = None
apiurl = "http://dataservice.accuweather.com/currentconditions/v1/%s?apikey=%s" % (LOCATION_CODE, API)


# Lock for refreshing AccuWeather data
lock = threading.Lock()

# Functions that handle requesting data from AccuWeather
def accuweather(endpoint):
    # 1 - Request location code from ZIP code and country code.
    if endpoint == "location":
        apiurl = "http://dataservice.accuweather.com/locations/v1/postalcodes/%s/search?apikey=%s&q=%s&details=true" % (COUNTRY_CODE, API, zip_code)
    
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
    if units == "C":
        unitType = "Metric"
    else:
        unitType = "Imperial"
    inchesRained = data[0]["PrecipitationSummary"]["Past24Hours"][unitType]["Value"]
    if inchesRained > 0.15:
        substantialRain = True
    return substantialRain

# Process weather data from last 24 hours.
def processOutsideTemperature(data):
    # Find inches rained in the last 24 hours.
    if units == "C":
        unitType = "Metric"
    else:
        unitType = "Imperial"
    temperature = data[0]["Temperature"][unitType]["Value"]
    return temperature

# Find Accuweather Icon to represent the weather.
def findOutsideIcon(data):
    icon = data[0]["WeatherIcon"]
    icon = f'{icon:02}'
    return icon

# Find date of Accuweather data.
def findDate(data):
    date = data[0]["LocalObservationDateTime"]
    return date

# Find Accuweather weather text.
def findWeatherText(data):
    text = data[0]["WeatherText"]
    return text



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

# Get country code and zip code from IP
def getCurrentLocationCodes():
    if not os.path.exists("location.json"):
        with urllib.request.urlopen("https://ipapi.co/json") as url:
            data = json.loads(url.read().decode())
            setLocationCode(countryCode=data["country_code"].lower(), zipCode=data["postal"])
    else:
        global LOCATION_CODE
        global COUNTRY_CODE
        global zip_code
        data = loadData("location")
        LOCATION_CODE = data[0]["Key"]
        COUNTRY_CODE = data[0]["Country"]["ID"].lower()
        zip_code = data[0]["PrimaryPostalCode"]

# Set location code from country and zip code
def setLocationCode(countryCode: str, zipCode: str):
    global COUNTRY_CODE
    global zip_code
    global LOCATION_CODE
    COUNTRY_CODE = countryCode
    zip_code = zipCode
    try:
        data = requestData("location")
        LOCATION_CODE = data[0]["Key"]
    except:
        data = 41076
        LOCATION_CODE = "17810_PC"

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

# Logic to decide whether to open or close doors based off future data
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

def openDoors(reason: str):
    return f"{reason}. You should open your doors and windows now. "

def closeDoors(reason: str):
    return f"{reason}. You should close your doors and windows now. "

def warnOpenDoors(reason: str):
    return f"{reason}. You should open your doors and windows within the next hour."

def warnCloseDoors(reason: str):
    return f"{reason}. You should close your doors and windows within the next hour. "

# Refresh AccuWeather data
def refreshAccuWeather():
    lock.acquire()
    try:
        requestData("recent")
        requestData("current")
        requestData("future")
        requestData("future1hour")
        print("AccuWeather data refreshed")
    except:
        print("Unauthorized!")
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

def readDHT(read):
    if dhtEnabled == True:
        if read == "F":
            try:
                temperature_c = dht_device.temperature
                temperature_f = temperature_c * (9 / 5) + 32
                with open("dhtf.json", 'w') as f:
                    json.dump(temperature_f, f, indent=2) 
                temperature_f = f'{temperature_f:.1f}°F'
                return temperature_f
            except RuntimeError as err:
                print(err)
                with open("dhtf.json", 'r') as f:
                    temperature_f = json.load(f)
                    temperature_f = f'{temperature_f:.1f}°F'
                    return temperature_f
        elif read == "C":
            try:
                temperature_c = dht_device.temperature
                with open("dhtc.json", 'w') as f:
                    json.dump(temperature_c, f, indent=2) 
                temperature_c = f'{temperature_c:.1f}°C'
                return temperature_c
            except RuntimeError as err:
                print(err)
                with open("dhtc.json", 'r') as f:
                    temperature_c = json.load(f)
                    temperature_c = f'{temperature_c:.1f}°C'
                    return temperature_c
        elif read == "H":
            try:
                humidity = f'{dht_device.humidity:.1f}'
                with open("dhth.json", 'w') as f:
                    json.dump(humidity, f, indent=2) 
                return humidity
            except RuntimeError as err:
                print(err)
                with open("dhth.json", 'r') as f:
                    humidity = json.load(f)
                    return humidity            
    else:
        return 60

# Display data on Dashboard
@app.route('/')
def index():
    if refreshOnAccess:
        refreshAccuWeather()
    data = loadData("recent")
    current = loadData("current")
    temperature = f'{processOutsideTemperature(current):.1f}°{units}'

    return render_template('index.html', zip_code=zip_code, temp=temperature, insideHumidity=readDHT("H"), doors=updateDoors(), Fdoors=updateFutureDoors(), rain=processRainData(), local=readDHT(units), datetime=findDate(data), text=findWeatherText(current), icon=findOutsideIcon(current))

if __name__ == '__main__':
    getCurrentLocationCodes()
    startRefreshLoop()
    app.run(debug=False, host='0.0.0.0', port=5500)
    