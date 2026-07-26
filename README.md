# Value Investing and AI Analysis

## Overview
Automated value-investing research tool: screens the FMP stock universe against configurable quantitative thresholds, layers OpenAI-based qualitative analysis (earnings-call and sentiment read) on top, and validates candidate strategies with a parameter-optimizing backtesting framework (Sharpe ratio, alpha vs. SPY, drawdown, transaction-cost modeling) before any of it touches real capital. See Backtesting Framework and Example Results below for the actual methodology and output.

## Features
- **Financial Data Integration**: Fetch comprehensive financial data using Financial Modeling Prep (FMP) API
- **Value Investing Screening**: Apply configurable value investing thresholds (strict, moderate, conservative, relaxed)
- **AI-Powered Analysis**: Analyze earnings calls and financial data using OpenAI GPT models
- **Historical Data Management**: Store and manage historical price data for backtesting
- **Comprehensive Backtesting Framework**: 
  - Portfolio rebalancing strategies
  - Position management with profit targets and stop losses
  - Transaction cost modeling
  - Performance metrics calculation (Sharpe ratio, alpha, drawdown)
  - Parameter optimization with grid search
- **Strategy Performance Analysis**: 
  - Real-time monitoring and progress tracking
  - Trade logging and analysis
  - Benchmark comparison (SPY)
  - Visualization of performance metrics
- **Robust Data Handling**: 
  - Automatic checkpointing and resume capability
  - Rate limiting and caching for API efficiency
  - Error handling and validation

## Prerequisites
- Python 3.10+
- OpenAI API key
- Financial Modeling Prep (FMP) API key

## Required API keys
- `OPENAI_API_KEY`: OpenAI API key for AI analysis
- `FMP_API_KEY`: Financial Modeling Prep API key for financial data

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
├── config.py # Configuration settings and thresholds
├── run_full_pipeline_strict.py # Full pipeline with strict criteria
├── utils/
│ ├── logging_setup.py # Logging configuration
│ ├── cache.py # Caching utilities
│ └── monitoring.py # Real-time monitoring system
├── services/
│ ├── openai_service.py # OpenAI API integration
│ ├── fmp_client.py # Centralized FMP API client
│ ├── stock_service_v2.py # Enhanced stock data fetching
│ └── historical_data_service.py # Historical data management
├── analysis/
│ ├── financial_analysis.py # Financial calculations
│ ├── value_analysis.py # Value investing logic
│ └── backtesting.py # Comprehensive backtesting framework
├── tests/
│ ├── debug_backtest.py # Backtesting validation
│ └── test_core_functionality.py # Core functionality tests
└── tickers/
    └── stock_tickers.json # Stock universe
</pre>

## Value Investing Criteria

The tool screens stocks based on configurable criteria levels:

### Strict Criteria
- P/E Ratio < 8
- Price-to-Book < 1.0
- Debt-to-Equity < 0.5
- Return on Equity > 15%

### Moderate Criteria (Default)
- P/E Ratio < 12
- Price-to-Book < 1.5
- Debt-to-Equity < 1.0
- Return on Equity > 12%

### Conservative Criteria
- P/E Ratio < 15
- Price-to-Book < 2.0
- Debt-to-Equity < 1.5
- Return on Equity > 10%

### Relaxed Criteria
- P/E Ratio < 20
- Price-to-Book < 3.0
- Debt-to-Equity < 2.0
- Return on Equity > 8%

## Usage

### Quick Start

1. **Run the full pipeline with strict criteria**:
```bash
python run_full_pipeline_strict.py
```

2. **Run backtesting on existing results**:
```bash
python tests/debug_backtest.py
```

### Backtesting Framework

The system includes a comprehensive backtesting framework with the following features:

#### Basic Backtesting
```python
from analysis.backtesting import backtest_value_strategy

result = backtest_value_strategy(
    tickers=['AAPL', 'MSFT', 'GOOGL'],
    start_date='2023-01-01',
    end_date='2025-06-30',
    rebalance_freq='ME',  # Monthly end
    initial_capital=100000
)
```

#### Parameter Optimization
```python
from analysis.backtesting import optimize_parameters

results = optimize_parameters(
    tickers=ticker_list,
    start_date='2023-01-01',
    end_date='2025-06-30',
    initial_capital=100000
)
```

#### Strategy Features
- **Rebalancing**: Monthly, quarterly, or custom frequency
- **Position Management**: 
  - Profit targets (20-35%)
  - Stop losses (-6% to -10%)
  - Trailing stops (6-10%)
  - ROE exit thresholds
- **Risk Management**:
  - Maximum positions (20-40)
  - Position sizing (5-10% per position)
  - Transaction costs and slippage
- **Advanced Features**:
  - 15-day SMA entry filter
  - Dynamic cash buffer (5% when gains > 20%)
  - SPY benchmark comparison

### Full Analysis Pipeline

1. **Stock Screening**:
```bash
python analysis/value_analysis.py --criteria strict --max-openai-calls 50
```

2. **Backtesting with Optimized Parameters**:
```bash
python run_optimized_backtest.py
```

## Output and Results

### Screening Results
- CSV file with qualifying stocks and financial metrics
- AI-generated insights for each stock
- Automatic checkpointing for resume capability

### Backtesting Results
- **Performance Metrics**: Total return, annualized return, Sharpe ratio, max drawdown
- **Trade Analysis**: Number of trades, win rate, average holding period
- **Risk Metrics**: Volatility, alpha vs SPY, transaction costs
- **Visualizations**: Portfolio value curves, relative performance charts
- **Trade Logs**: Detailed CSV files with all trades and exits

### Example Results
```
📊 Final Results:
   • Total Return: 2.77%
   • Annualized Return: 1.85%
   • Volatility: 7.01%
   • Sharpe Ratio: 0.01
   • Max Drawdown: -11.16%
   • Total Trades: 580
   • Win Rate: 8.28%
   • Alpha vs SPY: -27.95%
```

## Configuration

### Environment Variables
- `OPENAI_API_KEY`: Required for AI analysis
- `FMP_API_KEY`: Required for financial data
- `LOG_LEVEL`: Optional logging level (DEBUG, INFO, WARNING, ERROR)

### Backtesting Parameters
- `initial_capital`: Starting portfolio value
- `max_positions`: Maximum number of concurrent positions
- `position_size`: Target allocation per position
- `exit_profit_target`: Profit target for position exits
- `trailing_stop`: Trailing stop percentage
- `exit_loss_stop`: Stop loss percentage
- `rebalance_freq`: Rebalancing frequency ('ME', 'Q', '15D', 'W')

## Error Handling and Robustness

- **API Rate Limiting**: Built-in rate limiting and caching for FMP API
- **Resume Capability**: Automatic checkpointing allows resuming from interruptions
- **Data Validation**: Comprehensive validation of financial data quality
- **Error Recovery**: Graceful handling of API failures and network issues
- **Monitoring**: Real-time progress tracking and performance monitoring

## Performance Optimization

- **Batch Processing**: Efficient batch API calls to minimize rate limits
- **Caching**: Intelligent caching of API responses
- **Pre-fetching**: Historical data pre-fetched for backtesting efficiency
- **Parallel Processing**: Optimized for large stock universes

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Security Notes

- Never commit your `.env` file
- Keep your API keys secure
- Use the provided `.gitignore` file
- Monitor API usage to stay within limits

## Acknowledgments

- **OpenAI** for GPT models and AI analysis capabilities
- **Financial Modeling Prep (FMP)** for comprehensive financial data
- **Pandas** and **NumPy** for data analysis and backtesting calculations
- **Matplotlib** and **Seaborn** for performance visualization
