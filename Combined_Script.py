#!/usr/bin/env python
# coding: utf-8

# In[15]:


import requests
from bs4 import BeautifulSoup
from sqlalchemy import create_engine
from lxml import html
import json
import pandas as pd
import re
import seaborn as sns
import datetime
from datetime import timedelta
import numpy as np
import pytz

# In[16]:


airport_code = ['LAS', 'LAX', 'CHI', 'SFO', 'ORL', 'DEN', 'DCA', 'SEA', 'BOS']

day_delta = datetime.timedelta(days=1)
start_date = datetime.date(2018, 12, 22)
end_date = start_date + 11*day_delta

url_list = []

for airport in airport_code:
    for i in range((end_date - start_date).days):
        day = start_date + i*day_delta
        url = 'https://www.kayak.com/flights/NYC-' + str(airport) + '/' + str(day) + '?sort=bestflight_a&fs=stops=0'
        url_list.append(url)


# In[17]:


def create_flight_price_text(flight_url):
    r = requests.get('https://www.kayak.com')
    layer1Cookies = r.cookies

    flight_search_xhr = 'https://www.kayak.com/s/horizon/flights/results/FlightSearchPoll'

    params1 = {
        'searchId':'',
        'poll':'true',
        'pollNumber':'0',
        'applyFilters':'true',
        'filterState':'',
        'useViewStateFilterState':'false',
        'pageNumber':'1',
        'append':'false',
        'pollingId':'593601',  #interesting. explore further
        'requestReason':'POLL',
        'isSecondPhase':'false',
        'textAndPageLocations':'bottom,right',
        'displayAdPageLocations':'none',
        'existingAds':'false',
        'activeLeg':'-1',
        'view':'list',
        'renderPlusMinusThreeFlex':'false',
        'renderAirlineStopsMatrix':'false',
        'renderFlexHeader':'true',
        'tab':'flights',
        'pageOrigin':'F..FD..M0',
        'src':'',
        'searchingAgain':'',
        'c2s':'',
        'po':'',
        'personality':'',
        'provider':'',
        'isMulticity':'false',
        'flex_category':'exact',
        'oneway':'false',
        'nearby_origin':'false',
        'nearby_destination':'false',
        'countrySearch':'false',
        'travelers':'1',
        'adults':'1',
        'seniors':'0',
        'youth':'0',
        'child':'0',
        'seatInfant':'0',
        'lapInfant':'0',
        'cabin':'e',
        'cabinDisplayType':'Economy',
        'vertical':'flights',
        'url':flight_url,
        'id':'',
        'navigateToResults':'false',
        'ajaxts':'',
        'scriptsMetadata':'',
        'stylesMetadata':'',
    }
    
    headers = {
        'Host': 'www.kayak.com',
        'User-Agent': 'Chrome/63 (Macintosh; Intel Mac OS X 10.11; rv:57.0) Gecko/20100101 Firefox/57.0',
        'Accept': '*/*',
        'Accept-Language': 'en-US,en;q=0.5',
        'Referer': flight_url,
        'Content-Type': 'application/x-www-form-urlencoded',
        'X-CSRF': 'kAqI1NgGh$DJnEUpiSDOWpdQXzlgAwG8EVOCd$gXO08-hpumC4oNpaOjz15GO_q9a5FdZPonpC2kF4CBYjEPh14',
        'X-RequestId': 'flights#frontdoor#Ag$s9g',
        'X-Requested-With': 'XMLHttpRequest',
        'Content-Length': '1094'
    }


    result = requests.post(flight_search_xhr, headers = headers, data = params1, cookies = layer1Cookies)
    text = result.json()
    text = BeautifulSoup(text['content'], 'html.parser')
    return text;


# In[18]:


def getPricePrediction(flight_url):
    prediction_url = "https://www.kayak.com/s/horizon/flights/results/FlightPricePredictionAction"
    flight_search_html = requests.get(flight_url)

    s_id = re.compile(r'searchID=(\w+)')
    matches = s_id.finditer(str(create_flight_price_text(url)))
    searchId = ""
    for m in matches:
        searchId = m.group(1)

    token = re.compile(r"""\"formtoken\":\"(.+)\"\,""")
    matches = token.finditer(flight_search_html.text)
    formtoken = ""
    for m in matches:
        formtoken = m.group(1)
        
    headers = {
        'Host': 'www.kayak.com',
        'User-Agent': 'Chrome/63 (Macintosh; Intel Mac OS X 10.11; rv:57.0) Gecko/20100101 Firefox/57.0',
        'Accept': '*/*',
        'Accept-Language': 'en-US,en;q=0.5',
        'Referer': flight_url,
        'Content-Type': 'application/x-www-form-urlencoded',
        'X-CSRF': 'kAqI1NgGh$DJnEUpiSDOWpdQXzlgAwG8EVOCd$gXO08-hpumC4oNpaOjz15GO_q9a5FdZPonpC2kF4CBYjEPh14',
        'X-RequestId': 'flights#frontdoor#Ag$s9g',
        'X-Requested-With': 'XMLHttpRequest',
        'Content-Length': '1094'
    }
    params = {
        'searchId': searchId,
        'formtoken': formtoken
    }
    
    headers = {
        'Host': 'www.kayak.com',
        'User-Agent': 'Chrome/63 (Macintosh; Intel Mac OS X 10.11; rv:57.0) Gecko/20100101 Firefox/57.0',
        'Accept': '*/*',
        'Accept-Language': 'en-US,en;q=0.5',
        'Referer': flight_url,
        'Content-Type': 'application/x-www-form-urlencoded',
        'X-CSRF': 'kAqI1NgGh$DJnEUpiSDOWpdQXzlgAwG8EVOCd$gXO08-hpumC4oNpaOjz15GO_q9a5FdZPonpC2kF4CBYjEPh14',
        'X-RequestId': 'flights#frontdoor#Ag$s9g',
        'X-Requested-With': 'XMLHttpRequest',
        'Content-Length': '1094'
    }

    
    advice = requests.post(prediction_url, headers=headers, data=params)
    return advice.json()['infoText']


# In[31]:


def get_prices_times(text):
    doc = html.fromstring(str(text))
    flights = doc.xpath('//div[@class="Base-Results-HorizonResult Flights-Results-FlightResultItem phoenix-rising sleek rp-contrast "]')
    
    result = []
    for f in flights:
        price_info = f.get('aria-label')
        time_info = f.xpath('.//div//div//div//div[@class="col-info result-column"]')[0]
        time = time_info.xpath('.//div//div//ol//li//div//div//div//div//span//span[@class="depart-time base-time"]')[0].text
        am_pm = time_info.xpath('.//div//div//ol//li//div//div//div//div//span//span[@class="time-meridiem meridiem"]')[0].text
        airline = time_info.xpath('.//div//div//ol//li//div//div//div//div[@class="bottom"]')[0].text
        
        regex_price = re.compile(r'(\$)(\d*)',re.VERBOSE)
        matches_price = regex_price.finditer(price_info)
        for match in matches_price:
            clean_price = match.group(2)
            entry = {
                'price' : clean_price,
                'time' : time + am_pm,
                'airline' : airline
            }
            result.append(entry)
        
    return result


# In[ ]:





# In[20]:


def get_flights(html):
    flights = html.find_all('li', 'flight')
    result = []
    for f in flights:
        info = str(f.find('div', 'bottom'))
        info = info.replace('<div class="bottom">', '')
        info = info.replace("</div>", '')
        result.append(info)
        
    return result


# In[21]:


conn_string = 'mysql://{user}:{password}@{host}/'.format(
                host = '35.237.252.223',
                user = 'root',
                password = 'x3rGjkz93e6CIkd7')
engine = create_engine(conn_string)
con = engine.connect()


# In[22]:


insert_template = '''
INSERT IGNORE INTO kayak.flight(
    Airline, Price,
    Date, Time,
    Timestamp,
    Destination,
    Prediction)
    VALUES (%s, %s, %s, %s, %s, %s, %s)
'''


# In[35]:


for url in url_list:
    date_loc = re.compile(r'([A-Z]{3})/([\d-]{10})')
    dl = date_loc.finditer(url)
    date = ""
    destination = ""
    for match in dl:
        #destination #departure date
        date = match.group(2)
        destination = match.group(1)
        
    #timestamp
    fetch_time = pd.datetime.now(tz=pytz.timezone('EST'))
    price_dict = get_prices_times(create_flight_price_text(url))
#    flight_list = get_flights(create_flight_price_text(url))
    advice = getPricePrediction(url)
    
    for i in range(0, len(price_dict)):
#         price_dict[i]['airline'] = flight_list[i]
        price_dict[i]['prediction'] = advice
        
        query_parameters = (price_dict[i]['airline'], int(price_dict[i]['price']), date, price_dict[i]['time'],
                        fetch_time, destination, advice)
        engine.execute(insert_template, query_parameters)


# In[13]:



# In[ ]:




