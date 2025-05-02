# main.py
import json
from utils.logging_setup import setup_logging
from analysis.value_analysis import run_stock_analysis

def main():
    # Set up logging
    setup_logging()
    
    # Load stock symbols
    with open('tickers/stock_tickers.json', 'r') as f:
        symbol_list_us = json.load(f)
    
    # Run analysis
    run_stock_analysis(symbol_list_us)

if __name__ == "__main__":
    main()