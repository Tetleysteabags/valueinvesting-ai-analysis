# Combined Value Investing Backtesting System

This directory contains a comprehensive backtesting system that combines the best features from both the custom implementation and VectorBT-based approach.

## Files

- `combined_backtesting.py` - Main backtesting system with both implementations
- `test_combined_backtesting.py` - Test script to verify functionality
- `backstesting_vectorbt.py` - Original custom backtesting implementation
- `vectorbt.py` - Original VectorBT-based implementation

## Features

### Multi-Factor Value Strategy
- **Value Factor**: Low P/E ratios (ranked by percentile)
- **Quality Factor**: High ROE (ranked by percentile)
- **Momentum Factor**: 12-month price momentum (ranked by percentile)
- **Combined Score**: Equal-weighted average of all three factors

### Risk Management
- **Profit Target**: 25% gain exit
- **Stop Loss**: 10% loss exit
- **Trailing Stop**: 8% trailing stop for profitable positions
- **Position Sizing**: Equal-weighted allocation (20 positions max)

### Transaction Costs
- **Commission**: 0.1% per trade
- **Slippage**: 0.05% per trade
- **Total Cost**: 0.15% per transaction

### Rebalancing
- **Frequency**: Monthly rebalancing (configurable)
- **Universe**: Top 20 stocks by combined factor score
- **Rebalancing Band**: 20% tolerance to reduce turnover

## Usage

### Basic Usage

```python
from combined_backtesting import run_combined_backtest, print_backtest_results

# Define your tickers
tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "META", "NVDA"]

# Run VectorBT backtest
vbt_result = run_combined_backtest(
    tickers=tickers,
    start_date="2023-01-01",
    end_date="2024-12-31",
    use_vectorbt=True
)

# Run Custom backtest
custom_result = run_combined_backtest(
    tickers=tickers,
    start_date="2023-01-01",
    end_date="2024-12-31",
    use_vectorbt=False
)

# Print results
print_backtest_results(vbt_result)
print_backtest_results(custom_result)
```

### Advanced Usage

```python
from combined_backtesting import CustomValueInvestingBacktester, VectorBTBacktester

# Custom implementation with custom parameters
custom_bt = CustomValueInvestingBacktester(
    initial_capital=200_000.0,
    max_positions=15,
    transaction_cost=0.002,  # 0.2% commission
    slippage=0.001,          # 0.1% slippage
    profit_target=0.30,      # 30% profit target
    stop_loss=-0.15,         # 15% stop loss
    trailing_stop=0.10       # 10% trailing stop
)

result = custom_bt.run_backtest(
    tickers=tickers,
    start_date="2023-01-01",
    end_date="2024-12-31",
    rebalance_freq="ME"  # Monthly rebalancing
)

# VectorBT implementation
vbt_bt = VectorBTBacktester(
    initial_capital=200_000.0,
    max_positions=15,
    transaction_cost=0.002,
    slippage=0.001,
    profit_target=0.30,
    stop_loss=-0.15,
    trailing_stop=0.10
)

vbt_result = vbt_bt.run_backtest(
    tickers=tickers,
    start_date="2023-01-01",
    end_date="2024-12-31",
    rebalance_freq="ME"
)
```

## Performance Metrics

The system calculates comprehensive performance metrics:

- **Total Return**: Overall portfolio return
- **Annualized Return**: Annualized return rate
- **Max Drawdown**: Maximum portfolio decline
- **Sharpe Ratio**: Risk-adjusted return measure
- **Volatility**: Annualized standard deviation
- **Win Rate**: Percentage of profitable trades
- **Number of Trades**: Total number of trades executed
- **Average Holding Period**: Average days per trade
- **Transaction Costs**: Total fees paid
- **Alpha**: Excess return vs SPY benchmark

## BacktestResult Object

The system returns a `BacktestResult` object with the following attributes:

```python
@dataclass
class BacktestResult:
    strategy_name: str
    start_date: datetime
    end_date: datetime
    initial_capital: float
    final_capital: float
    total_return: float
    annualized_return: float
    max_drawdown: float
    sharpe_ratio: float
    volatility: float
    num_trades: int
    win_rate: float
    avg_holding_period: float
    transaction_costs: float
    portfolio_values: pd.Series
    cash_history: pd.Series
    position_values_sum: pd.Series
    trades_df: Optional[pd.DataFrame]
    benchmark_return: float
    alpha: float
```

## Key Differences Between Implementations

### VectorBT Implementation
- **Pros**: Faster execution, built-in optimizations, comprehensive statistics
- **Cons**: Less detailed position tracking, limited customization
- **Best for**: Large-scale backtesting, parameter optimization

### Custom Implementation
- **Pros**: Detailed position tracking, full customization, transparent logic
- **Cons**: Slower execution, more complex code
- **Best for**: Detailed analysis, custom risk management, educational purposes

## Testing

Run the test script to verify functionality:

```bash
cd ValueInvesting-AI-Analysis/analysis
python test_combined_backtesting.py
```

## Dependencies

Required packages:
- `pandas`
- `numpy`
- `vectorbt`
- `dataclasses`
- `pathlib`

Make sure all services are properly configured:
- `HistoricalDataService`
- `FundamentalService`
- `trading_days_aligner`

## Configuration

The system uses Financial Modeling Prep (FMP) for data fetching, as configured in the services. Ensure your FMP API key is properly set up in the configuration files.

## Example Output

```
============================================================
BACKTEST RESULTS: Multi-Factor Value (VectorBT)
============================================================
Period: 2023-01-01 to 2024-12-31
Initial Capital: $100,000.00
Final Capital: $125,450.30
Total Return: 25.45%
Annualized Return: 12.73%
Max Drawdown: -8.23%
Sharpe Ratio: 1.245
Volatility: 10.21%
Number of Trades: 156
Win Rate: 58.33%
Avg Holding Period: 45.2 days
Transaction Costs: $1,234.56
Benchmark Return: 18.45%
Alpha: 6.99%
============================================================
``` 