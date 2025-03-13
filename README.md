# Value Investing and AI Analysis

## Overview
This project automates the stock selection process for value investing by fetching financial data, analyzing sentiment and earnings calls using OpenAI, and applying value investing criteria to identify potential investment opportunities.

## Features
- Fetch financial data for stock tickers
- Perform sentiment analysis on stock-related news
- Analyze earnings calls
- Apply value investing thresholds
- Output results to a CSV file

## Prerequisites
- Required Python packages:
- concurrent.futures.ThreadPoolExecutor: For concurrent execution.
- openai: For accessing OpenAI's API.
- logging: For logging information.
- pandas: For data manipulation.
- requests: For making HTTP requests.
- stocksymbol.StockSymbol: For retrieving stock symbols.

## Required API keys
- fmp_key: Financial Modeling Prep API key.
- news_api_key: News API key.
- openai_api_key: OpenAI API key.
- api_key: Stock symbol API key for StockSymbol.

## Setup
1. Clone the repository:
   ```bash
   git clone https://github.com/tetleysteabags/valueinvesting-ai-analysis.git
   cd valueinvesting-ai-analysis
2. Set up accounts and required APIs
3. Determine the country and stock exchanges you want to focus on
4. Set value investor thresholds based on what you're interested in
5. Fetches key metrics, historical prices, income statements, shares float, and ratios data for stock tickers using the Financial Modeling Prep API.


The script requires several API keys:
```
Financial Modeling Prep API Key (FMP)
News API Key
OpenAI API Key
StockSymbol API Key
```

**Acknowledgments:**
```
Financial Modeling Prep for providing the financial data API.
OpenAI for providing the language model API.
```
