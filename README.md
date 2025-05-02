# Value Investing and AI Analysis

## Overview
This project automates the stock selection process for value investing by fetching financial data, analyzing sentiment and earnings calls using OpenAI, and applying value investing criteria to identify potential investment opportunities.

## Features
- Fetch financial data for stock tickers
- Apply value investing thresholds
- Analyze earnings calls and other data using OpenAI
- Output results to a CSV file

## Prerequisites
- Python 3.10+
- OpenAI API key

## Required API keys
- openai_api_key: OpenAI API key.

## Installation

1. Clone the repository:
```bash
git clone [your-repo-url]
cd ValueInvesting-AI-Analysis
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install required packages:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
   - Copy `.env.template` to `.env`
   - Add your API keys to `.env`


## Project Structure
<pre>
├── main.py # Main entry point
├── config.py # Configuration settings
├── utils/
│ ├── logging_setup.py # Logging configuration
│ └── cache.py # Caching utilities
├── services/
│ ├── openai_service.py # OpenAI API integration
│ └── stock_service.py # Stock data fetching
└── analysis/
├── financial_analysis.py # Financial calculations
└── value_analysis.py # Value investing logic
</pre>

## Value Investing Criteria

The tool screens stocks based on the following criteria:
- P/E Ratio < 10
- Price-to-Book < 1.5
- Debt-to-Equity < 1
- Return on Equity > 12%

These can be changed based on your requirements.

## Usage

1. Ensure your `.env` file is set up with required API keys
2. Run the analysis:
```bash
python main.py
```

The script will:
- Load stock tickers from `stock_tickers.json`
- Analyze each stock against value investing criteria
- Generate AI insights for qualifying stocks
- Save results to CSV with automatic checkpointing
- Log progress and errors to `stock_selection.log`

## Output

The analysis generates a CSV file containing:
- Basic stock information (symbol, company name, price)
- Financial metrics (P/E, P/B, D/E, ROE, etc.)
- AI-generated insights:
  - Sentiment analysis
  - Earnings call summary
  - Stock insights
  - Value investing perspective

## Error Handling

- Automatic retry for API failures
- Logging of errors to `stock_selection.log`
- Resumable processing from last checkpoint
- Validation of data quality and completeness

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## Security Notes

- Never commit your `.env` file
- Keep your API keys secure
- Use the provided `.gitignore` file

## Acknowledgments

- OpenAI for GPT-3.5 API
- yfinance for financial data