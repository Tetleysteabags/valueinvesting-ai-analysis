# Value Investing AI - Test Suite

This folder contains all the test scripts for the Value Investing AI project.

## 🚀 Quick Start

Run the interactive test runner:
```bash
python tests/run_all_tests.py
```

## 📁 Test Files Overview

### 🔧 Setup & Validation Tests

| File | Purpose | API Calls | Description |
|------|---------|-----------|-------------|
| `test_env.py` | Validate environment | 0 | Check API keys and environment setup |
| `check_free_tier.py` | Test FMP endpoints | ~10 | Verify which FMP free tier endpoints work |

### 📊 Data Fetching Tests

| File | Purpose | API Calls | Description |
|------|---------|-----------|-------------|
| `simple_test.py` | Basic functionality | 24 | Test with 3 major stocks (AAPL, MSFT, GOOGL) |
| `value_stocks_test.py` | Value stock analysis | 80 | Test with value-oriented stocks |
| `moderate_value_test.py` | Relaxed criteria | 40 | Test with more flexible value criteria |
| `test_free_tier_run.py` | Full analysis | 280 | Complete analysis with 35 test stocks |

### 🧪 Unit Tests

| File | Purpose | API Calls | Description |
|------|---------|-----------|-------------|
| `test_stock_service.py` | Stock service tests | 0 | Unit tests for stock data fetching |
| `tests_fmp_client.py` | FMP client tests | 0 | Unit tests for FMP API client |

## 🎯 Recommended Test Sequence

### For First-Time Setup:
1. `test_env.py` - Verify your API keys work
2. `check_free_tier.py` - Confirm FMP free tier access
3. `simple_test.py` - Basic functionality test

### For Value Stock Analysis:
1. `value_stocks_test.py` - Test with value-oriented stocks
2. `moderate_value_test.py` - Try with relaxed criteria

### For Full Analysis:
1. `test_free_tier_run.py` - Complete analysis (uses ~280 API calls)

## ⚠️ API Call Limits

**FMP Free Tier**: 250 calls/day
- `simple_test.py`: 24 calls (9.6% of daily limit)
- `value_stocks_test.py`: 80 calls (32% of daily limit)
- `moderate_value_test.py`: 40 calls (16% of daily limit)
- `test_free_tier_run.py`: 280 calls (112% of daily limit - **exceeds limit**)

## 🛠️ Rate Limiting Solutions

If you hit rate limits, the system includes:
- **Increased delays**: 8-11 seconds between calls
- **Caching**: Results cached for 24 hours
- **Retry logic**: Automatic retries with exponential backoff
- **Minimal data service**: Uses fewer API calls per stock

## 📊 Expected Results

### Value Investing Criteria (Strict):
- P/E Ratio < 10
- Price/Book < 1.5
- ROE > 12%
- Debt/Equity < 1

### Value Investing Criteria (Moderate):
- P/E Ratio < 15
- Price/Book < 2.5
- ROE > 10%
- Debt/Equity < 1.5

## 🔍 Troubleshooting

### Common Issues:

1. **"Invalid FMP API key"**
   - Check your `.env` file
   - Verify API key is correct
   - Run `test_env.py` to validate

2. **Rate limiting errors**
   - Wait 1-2 hours before retrying
   - Use smaller test files
   - Check your daily API call count

3. **Missing data**
   - Some stocks may not have complete data
   - Free tier has limited endpoint access
   - Try different stocks

### Getting Help:
- Check the main project README
- Review the logs for specific error messages
- Start with `simple_test.py` to verify basic functionality

## 📈 Test Results

Test results are saved as CSV files in the project root:
- `simple_test_results.csv`
- `value_stocks_results.csv`
- `moderate_value_results.csv`
- `test_results.csv`

## 🎯 Next Steps

After running tests:
1. Review the CSV results
2. Analyze stocks that meet your criteria
3. Consider upgrading to FMP paid tier for more data
4. Customize the value criteria in `config.py` 