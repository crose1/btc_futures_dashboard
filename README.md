# Bitcoin Flask Dashboard

The goal of this project is to build a simple dashboard showing a live updating BTC futures curve, live chart of BTC perpetual price, and a table of the open interest in different BTC futures contracts.

Data is sourced from Deribit, accessed via an asynchronous websocket for live data and via API calls for open interest.

Figures are visualised using DASH to quickly mock up a simple dashboard with multiple tabs.

# How to run the dashboard

Download the btc_futures_dashboard.py file and run using terminal or your preferred IDE.

The dashboard should run locally on http://0.0.0.0:8080/ which is accessable through your browser.

To stop the app from running use control+command+c on macOS or control+alt+c on windows


