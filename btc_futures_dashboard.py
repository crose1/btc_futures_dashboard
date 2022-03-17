import os
import pandas as pd
import numpy as np
import datetime

import json
import matplotlib.pyplot as plt

import requests

import asyncio
import websockets
import json
from threading import Thread

import dash
import dash_table
from dash import dcc
from dash import html
import plotly.express as px
from dash.dependencies import Input, Output
import dash_table.FormatTemplate as FormatTemplate
from dash_table.Format import Format, Group

'''Global Variables - define which futures we use'''
futureslist = ['BTC-25MAR22',  'BTC-24JUN22', 'BTC-30SEP22',  'BTC-PERPETUAL'] #'BTC-31DEC21','BTC-28JAN22',

channelslist = ['ticker.BTC-25MAR22.100ms', 'ticker.BTC-28JAN22.100ms', 'ticker.BTC-24JUN22.100ms', 'ticker.BTC-30SEP22.100ms', 'ticker.BTC-31DEC21.100ms', 'ticker.BTC-PERPETUAL.100ms']


'''Message that we send to asynchronously connect to Deribit''' 
msg = {"jsonrpc": "2.0",
      "method": "public/subscribe",
      "id": 42,
      "params": {
        "channels": channelslist}
    }


'''Parse expiry date from futures contract name '''
def GrabDateFromName(instrumentname):
    if pd.isnull(instrumentname):
        return ("","","","","","")

    instrumentname2 = instrumentname[4:]
    
    posfinder = instrumentname2.find("-")
    if posfinder == -1:
        contractdate = instrumentname2
        if instrumentname2 =="SPOT":
            expirydate = 0
        elif instrumentname2 =="PERPETUAL":
            expirydate = datetime.datetime.today()
        else:
            expirydate = datetime.datetime.strptime(instrumentname2,"%d%b%y")
    if posfinder > -1:
        contractdate = instrumentname2[0:posfinder]
        expirydate = datetime.datetime.strptime(instrumentname2[0:posfinder],"%d%b%y")

    return (contractdate, expirydate)

'''Function to query deribit for Open Interest'''
def DBDataGrabber(method, params):
    # method = Deribit function
    # params = params in dictionary format
    dbloop = True
    while dbloop:
        try:
            webdata = requests.get("https://test.deribit.com/api/v2/public/"+method,params)
            dbloop = False
        except Exception as e:
            print('Error in DBDataGrabber: ')
            print(e)
    return webdata.json()

'''Extract data from call to Deribit for Open Interest Tab'''
def GrabOIData():
    oi_dict = {}
    for eachfut in futureslist:
        oi_dict[eachfut] = {}
        db_dat = DBDataGrabber("ticker",{"instrument_name": eachfut})
        if 'result' in db_dat.keys():
            oi_dict[eachfut]['value'] = db_dat["result"]["open_interest"]
            oi_dict[eachfut]['date'] = GrabDateFromName(eachfut)[1].date()
        
    oi_df = pd.DataFrame.from_dict(oi_dict,orient='index').reset_index()
    oi_df.columns = ['Future', 'Open Interest', 'Expiry Date']
    oi_df = oi_df.sort_values('Expiry Date')
    return oi_df

oi_df = GrabOIData()

'''
The below function connects asynchronously via web socket to Deribit and continously extracts prices on futures and 
perpetual BTC (which we use in place of spot BTC prices)


'''
futuresprices = {}
live_oi = {}
live_spot = []
connection_status = {}
connection_status['status'] = 'Connecting'
async def call_api(msg):
    async with websockets.connect('wss://test.deribit.com/ws/api/v2') as websocket:
        await websocket.send(msg) 
        while True:
            if not websocket.open:
                connection_status['status'] = 'Reconnecting'
                try:
                    print('Websocket is NOT connected. Reconnecting...')
                    websocket = await websockets.connect('wss://test.deribit.com/ws/api/v2')
                    await websocket.send(msg)
                except Exception as e:
                    print(e)
                    print('Unable to reconnect, trying again.')
            if websocket.open:
                try:
                   connection_status['status'] = 'Connected'
                   response = await websocket.recv()
                   response_json = json.loads(response)
                   if 'result' in response_json.keys():
                       print("Successfully subscribed")
                   if not 'result' in response_json.keys():
                        if response_json["params"]["channel"] in channelslist:
                           expirydate, contractdate = GrabDateFromName(response_json["params"]["channel"][7:-6])
                           futuresprices[contractdate.date()] = {}
                           futuresprices[contractdate.date()]['price'] = response_json["params"]["data"]["mark_price"]
                           futuresprices[contractdate.date()]['contract'] = expirydate
                           if expirydate == 'PERPETUAL':
                               response_time = datetime.datetime.fromtimestamp(response_json["params"]["data"]["timestamp"]/1000.0)
                               live_spot.append(
                                   {'time':response_time,'price': response_json["params"]["data"]["mark_price"]}
                                                  )
                               #Limit the size of live spot - very inefficient removal method
                               if len(live_spot) > 2000:
                                   del live_spot[0]
                
                except Exception as e:
                    connection_status['status'] = 'Reconnecting'
                    print(e)
                    print('Error receiving message from websocket.')
  
'''Wrapper function to run asyncronous function within a thread'''                         
def async_main_wrapper():
    # asyncio.run(call_api(json.dumps(msg)))
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    # # Side note: Apparently, async() will be deprecated in 3.4.4.
    # # See: https://docs.python.org/3.4/library/asyncio-task.html#asyncio.async
    tasks = asyncio.gather(
        call_api(json.dumps(msg))
    )

    try:
        loop.run_until_complete(tasks)
    except KeyboardInterrupt:
        print("Caught keyboard interrupt. Canceling tasks...")
        tasks.cancel()
        loop.run_forever()
        tasks.exception()
    finally:
        loop.close()

'''
Below we have all the code for our dashboard

First we define the initial layout of the Dash app
Then we have two callback functions which update our data
The futures chart updates every 500ms
The open interest table updates on pressing the refresh button

### To kill the app use ctrl+command+c in the console
'''

'''Interval for how often to refresh futures prices and spot price '''
refresh_interval =0.5*1000 # in milliseconds
app = dash.Dash(__name__)

app.layout = html.Div(children=[
    html.H1(children='BTC Dashboard'),
    html.H3(children='Example framework in DASH for visualising live updating data'),
    dcc.Tabs([
        dcc.Tab(label='Live Futures Curve', children=[
            html.Div(children=[
                dcc.Graph(id='live-futures-graph'),
                html.Div(id='connection-status'),
                html.Div(id='live-futures-dt'),
                
            ]),
            dcc.Interval(
                    id='interval-futures',
                    interval=refresh_interval,
                    n_intervals=0
                ),
        ]),
        dcc.Tab(label='Live BTC Price', children=[
            html.Div(children=[
                html.H3(children='''
                    NOTE: Using BTC-PERP prices as replacement for live pricing data (proof of concept)
                    '''),
                dcc.Graph(id='live-spot-graph'),
                html.Div(id='live-spot-dt'),
                dcc.Interval(
                    id='interval-spot',
                    interval=refresh_interval,
                    n_intervals=0
                ),
                
            ])
        ]),
        dcc.Tab(label='Futures Open Interest', children=[
            html.Div(children=[
                dash_table.DataTable(
                    id='table',
                    data=oi_df.to_dict('records'),
                    columns=[
                        dict(id='Future', name='Contract Name', type='text'), 
                        dict(id='Open Interest', name='Open Interest', type='numeric', format=Format().group(True)), 
                        dict(id='Expiry Date', name='Expiry Date', type='datetime')
                        ],
                    
                    style_cell={'textAlign': 'right'},
                    style_as_list_view=True,
                    ),
                html.Button('Refresh Open Interest', id='refresh-button', n_clicks=0),
                html.Div(id='open_interest_dt')
            ])
            
        ]),
        
    ]),
])

                        
# Multiple components can update everytime interval gets fired.
'''Continuously update futures prices''' 
@app.callback(Output('live-futures-graph', 'figure'),
              Output('live-futures-dt', 'children'),
              Output('connection-status', 'children'),
              Input('interval-futures', 'n_intervals'))
def update_futures_live(n):
    
    # Reload futures price data from latest futuresprices dictionary
    futurespricetable = pd.DataFrame.from_dict(futuresprices, orient="index").sort_index().reset_index()
    futurespricetable.columns = ['Date','Price USD','Contract']

    # Update the connection status
    status = 'Futures Prices: ' + str(connection_status['status'])

    last_updated = 'Last Updated: ' + datetime.datetime.now().time().strftime('%H:%M:%S.%f')[:-5]
    # Create the futures graph
    fig_future = px.line(futurespricetable,
                  x='Date',
                  y='Price USD',
                  text="Price USD",
                  # color='Contract',
                  labels={"Date": "Contract Expiry Date",
                     "Price USD": "Contract Price USD",
                     "Contract": "Contract"},
                  markers=True
                  )
    fig_future.update_traces(
        textposition='{} {}'.format('bottom', 'right'),
        texttemplate = "%{y:$,.2f}"
        )
    fig_future.update_xaxes(showgrid=True, ticklabelmode="instant", dtick="M1", tickformat="%b<br>%Y")

    return fig_future, last_updated, status


'''Continously update the spot price '''
@app.callback(Output('live-spot-graph', 'figure'),
              Output('live-spot-dt', 'children'),
              Input('interval-spot', 'n_intervals'))
def update_spot_live(n):
    
    # Reload futures price data from latest futuresprices dictionary
    
    spotpricetable = pd.DataFrame([i for i in live_spot])
    spotpricetable.columns = ['Time','Price USD']

    last_updated = 'Last Updated: ' + datetime.datetime.now().time().strftime('%H:%M:%S.%f')[:-5]
    
    # Create the spot graph
    fig_spot = px.line(spotpricetable,
                        x='Time',
                        y='Price USD')
    

    return fig_spot, last_updated


'''Refresh the open interest tab on button press '''
@app.callback(Output('table','data'),
              Output('open_interest_dt','children'),
              Input('refresh-button', 'n_clicks'))
def refresh_oi(n):
    oi_df = GrabOIData()
    oi_dict = oi_df.to_dict('records')
    last_updated = 'Last Updated: ' + datetime.datetime.now().time().strftime('%H:%M:%S.%f')[:-5]
    return oi_dict, last_updated

'''
Below is our function to run both Dash and the Async function for extracting data. 
In order for both to be run concurrently, we run them on different 'threads'
- Note in python these are likely not the same a true threads
'''

if __name__ == '__main__':
    # run all async in one thread
    th = Thread(target=async_main_wrapper)
    th.start()
    # run Flask server in another thread
    app.run_server(host="0.0.0.0", port=8080, debug=True)
    th.join()


