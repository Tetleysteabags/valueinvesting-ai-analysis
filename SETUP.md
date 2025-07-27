# Setup Guide for Value Investing AI

## 1. API Keys Setup

You need to set up your API keys before running the script. Create a `.env` file in the project root with your API keys:

```bash
# Create .env file
touch .env
```

Add the following to your `.env` file:

```
# FMP API Key (Free tier: 250 calls/day)
FMP_API_KEY=your_fmp_api_key_here

# OpenAI API Key
OPENAI_API_KEY=your_openai_api_key_here
```

### Getting API Keys:

1. **FMP API Key**: 
   - Go to https://financialmodelingprep.com/
   - Sign up for a free account
   - Get your API key from the dashboard

2. **OpenAI API Key**:
   - Go to https://platform.openai.com/
   - Sign up/login and get your API key

## 2. Running the Test Script

The test script is optimized for the FMP free tier (250 calls/day limit):

```bash
# Activate virtual environment
source venv/bin/activate

# Run the test script
python test_run.py
```

This will process 35 well-known stocks using approximately 280 API calls (within your daily limit).

## 3. Understanding the Results

The script will:
- Fetch financial data for each stock
- Apply value investing criteria (P/E < 10, P/B < 1.5, D/E < 1, ROE > 12%)
- Generate AI insights for qualifying stocks
- Save results to `test_analysis.csv`

## 4. Full Analysis (Optional)

To run analysis on your full stock list (1000+ stocks), you'll need to:
- Upgrade to a paid FMP plan, or
- Run the analysis over multiple days (process ~30 stocks per day)

## 5. Troubleshooting

- **API Key Errors**: Make sure your `.env` file is in the project root
- **Rate Limiting**: The script includes built-in rate limiting for FMP API
- **Cache**: Results are cached to avoid duplicate API calls

## 6. Output Files

- `test_analysis.csv`: Main results file
- `stock_selection.log`: Detailed logs
- `cache/`: Cached API responses
- `openai_cache.json`: Cached OpenAI responses 