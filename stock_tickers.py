# import the json files
import json

# load the json files
with open('amex_tickers.json', 'r') as f:
    amex_tickers = json.load(f)
with open('nasdaq_tickers.json', 'r') as f:
    nasdaq_tickers = json.load(f)
with open('nyse_tickers.json', 'r') as f:
    nyse_tickers = json.load(f)

# Combine and deduplicate
stock_tickers = list(set(amex_tickers + nasdaq_tickers + nyse_tickers))
    
# save the json files
with open('stock_tickers.json', 'w') as f:
    json.dump(stock_tickers, f)

