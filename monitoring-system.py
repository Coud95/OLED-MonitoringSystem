import time
import datetime

import Adafruit_GPIO.SPI as SPI
import Adafruit_SSD1306

from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont

import subprocess

import time, uuid, urllib, urllib2
import hmac, hashlib
from base64 import b64encode
import json
import threading

RST = None
DC = 23
SPI_PORT = 0
SPI_DEVICE = 0

disp = Adafruit_SSD1306.SSD1306_128_64(rst=RST)

disp.begin()
disp.clear()
disp.display()

width = disp.width
height = disp.height
image = Image.new('1', (width, height))
draw = ImageDraw.Draw(image)
draw.rectangle((0, 0, width, height), outline=0, fill=0)

padding = -2
top = padding
bottom = height - padding
x = 0

dateTimeFont = ImageFont.truetype('fonts/GenericMobileSystem.ttf', 24)
dataFont = ImageFont.truetype('fonts/GenericMobileSystem.ttf', 19)
descFont = ImageFont.truetype('fonts/Nintendo-DS-BIOS.ttf', 16)
degree_sign= u'\N{DEGREE SIGN}'

def prepare_request():
    url = 'https://weather-ydn-yql.media.yahoo.com/forecastrss'
    method = 'GET'
    app_id = ''
    consumer_key = ''
    consumer_secret = ''
    concat = '&'
    query = {'location': 'cracow', 'format': 'json', 'u': 'c'}
    oauth = {
        'oauth_consumer_key': consumer_key,
        'oauth_nonce': uuid.uuid4().hex,
        'oauth_signature_method': 'HMAC-SHA1',
        'oauth_timestamp': str(int(time.time())),
        'oauth_version': '1.0'
    }
    merged_params = query.copy()
    merged_params.update(oauth)
    sorted_params = [k + '=' + urllib.quote(merged_params[k], safe='') for k in sorted(merged_params.keys())]
    signature_base_str = method + concat + urllib.quote(url, safe='') + concat + urllib.quote(concat.join(sorted_params), safe='')

    composite_key = urllib.quote(consumer_secret, safe='') + concat
    oauth_signature = b64encode(hmac.new(composite_key, signature_base_str, hashlib.sha1).digest())

    oauth['oauth_signature'] = oauth_signature
    auth_header = 'OAuth ' + ', '.join(['{}="{}"'.format(k, v) for k, v in oauth.iteritems()])

    url = url + '?' + urllib.urlencode(query)
    request = urllib2.Request(url)
    request.add_header('Authorization', auth_header)
    request.add_header('X-Yahoo-App-Id', app_id)
    return request

request = prepare_request()
response = urllib2.urlopen(request).read()

def authentication():
    global request
    threading.Timer(86400.0, authentication).start()
    request = prepare_request()

authentication()

def call_api():
    global response
    threading.Timer(900.0, call_api).start()
    response = urllib2.urlopen(request).read()

call_api()

def display_weather_info():
    parsed_json = json.loads(response)
    current_temperature = parsed_json['current_observation']['condition']['temperature']
    forecast = parsed_json['forecasts'][0]
    low = forecast['low']
    high = forecast['high']
    current_description = parsed_json['current_observation']['condition']['text']
    forecast_description = forecast['text']
    current_code = parsed_json['current_observation']['condition']['code']
    weather_icon = Image.open('weather-icons/' + str(current_code) + '.ppm').convert('1')
    draw = ImageDraw.Draw(weather_icon)

    draw.text((x, top), str(now.strftime("%H:%M ")) + str(current_temperature) + degree_sign + "C", font=dateTimeFont, fill=255)
    draw.text((x, top + 17), "C:" + current_description, font=descFont, fill=255)
    draw.text((x, top + 29), "F:" + forecast_description, font=descFont, fill=255)
    draw.text((x, top + 48), "L:" + str(low) + " H:" + str(high), font=dataFont, fill=255)

    disp.image(weather_icon)
    disp.display()


def display_raspberry_info():
    draw.text((x, top), str(now.strftime("%H:%M %d-%m")), font=dateTimeFont, fill=255)

    t_file = open('/sys/class/thermal/thermal_zone0/temp')
    temp = float(t_file.read())
    temp_c = int(temp / 1000)
    draw.text((x, top + 15), str("CPU sensor: ") + str(temp_c) + degree_sign + "C", font=dataFont, fill=255)

    cmd = "top -bn1 | grep load | awk '{printf \"CPU load: %.2f\", $(NF-2)}'"
    cpu_usage = subprocess.check_output(cmd, shell=True, universal_newlines=True)
    draw.text((x, top + 27), str(cpu_usage), font=dataFont, fill=255)

    cmd = "free -m | awk 'NR==2{printf \"RAM: %s/%sMB\", $3,$2}'"
    ram = subprocess.check_output(cmd, shell=True, universal_newlines=True)
    draw.text((x, top + 39), str(ram), font=dataFont, fill=255)

    cmd = "df -h | awk '$NF==\"/\"{printf \"Disk: %d/%dGB\", $3,$2}'"
    disk_usage = subprocess.check_output(cmd, shell=True, universal_newlines=True)
    draw.text((x, top + 51), str(disk_usage), font=dataFont, fill=255)


while True:
    draw.rectangle((0, 0, width, height), outline=0, fill=0)
    now = datetime.datetime.now()
    if datetime.time(7, 50) < now.time() < datetime.time(23, 50):
        display_raspberry_info()
        disp.image(image)
        disp.display()
        time.sleep(10)
        display_weather_info()
    else:
        disp.image(image)
        disp.display()
    time.sleep(10)
