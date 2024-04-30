# CIT 381 Final Project


Install
```
git clone https://github.com/cassiancc/Humidity-Final-Project
cd Humidty-Final project
python3 -m venv env
source env/bin/activate
python3 -m pip install adafruit-circuitpython-dht
pip install -r requirements.txt
pip install flask
python3 humidity.py
```

You'll need to provide an Accuweather API key as key.txt for the service to work. 

## Create service
Create a service file named humidity.
```bash
sudo nano /etc/systemd/system/humidity.service
```
Add the following content to the file.
```
[Unit]
Description = Humidity final project
After = network.target

[Service]
Type = simple
ExecStart=/home/cassian/final-project/env/bin/python3 /home/cassian/final-project/humidity.py
WorkingDirectory=/home/cassian/final-project
User = cassian
Group = cassian
Restart = on-failure
SyslogIdentifier = humidity
RestartSec = 5
TimeoutStartSec = infinity

[Install]
WantedBy = multi-user.target
```
Start the service
```bash
systemctl enable humidity

systemctl daemon-reload

systemctl start humidity
```
