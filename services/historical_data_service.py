#!/usr/bin/env python3
"""
Historical Data Service for Value Investing AI Backtesting.
Fetches, stores, and manages historical stock data using FMP API.
"""

import os
import json
import time
import logging
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import sqlite3
from pathlib import Path
import threading
from dotenv import load_dotenv
from services.fmp_client import client as fmp_client

# Load environment variables
load_dotenv()

class HistoricalDataService:
    """Service for managing historical stock data using FMP API."""
    
    def __init__(self, data_dir: str = "data", db_path: str = "data/historical_data.db"):
        self.data_dir = Path(data_dir)
        self.db_path = Path(db_path)
        self.data_dir.mkdir(exist_ok=True)
        
        # FMP Configuration
        self.FMP_API_KEY = os.getenv("FMP_API_KEY")
        self.FMP_BASE = "https://financialmodelingprep.com/api/v3"
        
        # Initialize database
        self._init_database()
        
        # Thread safety
        self.lock = threading.Lock()
        
    def _init_database(self):
        """Initialize SQLite database for historical data."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS historical_prices (
                    ticker TEXT,
                    date TEXT,
                    open REAL,
                    high REAL,
                    low REAL,
                    close REAL,
                    adj_close REAL,
                    volume INTEGER,
                    dividends REAL,
                    stock_splits REAL,
                    PRIMARY KEY (ticker, date)
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS value_screens (
                    ticker TEXT,
                    screen_date TEXT,
                    pe_ratio REAL,
                    price_to_book REAL,
                    debt_to_equity REAL,
                    roe REAL,
                    market_cap REAL,
                    current_price REAL,
                    meets_criteria BOOLEAN,
                    PRIMARY KEY (ticker, screen_date)
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS backtest_results (
                    strategy_name TEXT,
                    start_date TEXT,
                    end_date TEXT,
                    initial_capital REAL,
                    final_capital REAL,
                    total_return REAL,
                    annualized_return REAL,
                    max_drawdown REAL,
                    sharpe_ratio REAL,
                    num_trades INTEGER,
                    win_rate REAL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.commit()
    
    def _fmp_get(self, endpoint: str, params: dict = None):
        """Delegate to shared FMP client."""
        return fmp_client.get(endpoint, params=params)
    
    def fetch_historical_data(self, ticker: str, period: str = "5y", 
                            source: str = "fmp") -> Optional[pd.DataFrame]:
        """
        Fetch historical data for a ticker using FMP API.
        
        Args:
            ticker: Stock ticker symbol
            period: Time period ('1y', '2y', '5y', '10y', 'max')
            source: Data source (only 'fmp' supported)
            
        Returns:
            DataFrame with historical OHLCV data
        """
        try:
            if source != "fmp":
                raise ValueError("Only FMP source is supported")
            
            return self._fetch_fmp_data(ticker, period)
                
        except Exception as e:
            logging.error(f"Error fetching historical data for {ticker}: {e}")
            return None
    
    def _fetch_fmp_data(self, ticker: str, period: str) -> Optional[pd.DataFrame]:
        """Fetch historical data using FMP API."""
        try:
            # Map period to FMP format
            period_map = {
                "1y": "1year",
                "2y": "2years", 
                "5y": "5years",
                "10y": "10years",
                "max": "max"
            }
            
            fmp_period = period_map.get(period, "5years")
            
            # Fetch historical data from FMP
            data = self._fmp_get(f"historical-price-full/{ticker}", {"serietype": "line"})
            
            if not data or 'historical' not in data:
                logging.warning(f"No historical data found for {ticker}")
                return None
            
            # Convert to DataFrame
            df = pd.DataFrame(data['historical'])
            
            if df.empty:
                logging.warning(f"Empty historical data for {ticker}")
                return None
            
            # Standardize column names
            df = df.rename(columns={
                'date': 'Date',
                'open': 'Open',
                'high': 'High', 
                'low': 'Low',
                'close': 'Close',
                'adjClose': 'Adj Close',
                'volume': 'Volume'
            })
            
            # Add ticker column
            df['ticker'] = ticker
            
            # Convert date to datetime
            df['Date'] = pd.to_datetime(df['Date'])
            
            # Sort by date (oldest first)
            df = df.sort_values('Date')
            
            # Save to database
            self._save_to_database(ticker, df)
            
            logging.info(f"✅ Successfully fetched {len(df)} records for {ticker}")
            return df
            
        except Exception as e:
            logging.error(f"Error fetching FMP data for {ticker}: {e}")
            return None
    
    def _save_to_database(self, ticker: str, df: pd.DataFrame):
        """Save historical data to SQLite database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Prepare data for insertion
                data_to_insert = []
                for _, row in df.iterrows():
                    data_to_insert.append((
                        ticker,
                        row['Date'].strftime('%Y-%m-%d'),
                        row.get('Open', None),
                        row.get('High', None),
                        row.get('Low', None),
                        row.get('Close', None),
                        row.get('Adj Close', None),
                        row.get('Volume', None),
                        0,  # dividends (not available in FMP free tier)
                        0   # stock_splits (not available in FMP free tier)
                    ))
                
                # Insert data (replace if exists)
                conn.executemany("""
                    INSERT OR REPLACE INTO historical_prices 
                    (ticker, date, open, high, low, close, adj_close, volume, dividends, stock_splits)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, data_to_insert)
                
                conn.commit()
                logging.info(f"Saved {len(data_to_insert)} records for {ticker}")
                
        except Exception as e:
            logging.error(f"Error saving data to database for {ticker}: {e}")
    
    def get_historical_data(self, ticker: str, start_date: str = None, 
                          end_date: str = None) -> Optional[pd.DataFrame]:
        """
        Get historical data from database.
        
        Args:
            ticker: Stock ticker symbol
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            
        Returns:
            DataFrame with historical data
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                query = "SELECT * FROM historical_prices WHERE ticker = ?"
                params = [ticker]
                
                if start_date:
                    query += " AND date >= ?"
                    params.append(start_date)
                
                if end_date:
                    query += " AND date <= ?"
                    params.append(end_date)
                
                query += " ORDER BY date"
                
                df = pd.read_sql_query(query, conn, params=params)
                
                if df.empty:
                    return None
                
                # Convert date column to datetime
                df['date'] = pd.to_datetime(df['date'])
                df = df.set_index('date')
                
                return df
                
        except Exception as e:
            logging.error(f"Error retrieving historical data for {ticker}: {e}")
            return None
    
    def save_value_screen(self, ticker: str, screen_date: str, data: Dict):
        """Save value screening results to database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO value_screens 
                    (ticker, screen_date, pe_ratio, price_to_book, debt_to_equity, 
                     roe, market_cap, current_price, meets_criteria)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    ticker,
                    screen_date,
                    data.get('pe_ratio'),
                    data.get('price_to_book'),
                    data.get('de_ratio'),
                    data.get('roe_ratio'),
                    data.get('market_cap'),
                    data.get('current_price'),
                    data.get('meets_criteria', False)
                ))
                
                conn.commit()
                
        except Exception as e:
            logging.error(f"Error saving value screen for {ticker}: {e}")
    
    def get_value_screens(self, start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """Get value screening results from database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                query = "SELECT * FROM value_screens"
                params = []
                
                if start_date or end_date:
                    query += " WHERE"
                    if start_date:
                        query += " screen_date >= ?"
                        params.append(start_date)
                    if end_date:
                        if start_date:
                            query += " AND"
                        query += " screen_date <= ?"
                        params.append(end_date)
                
                query += " ORDER BY screen_date DESC"
                
                df = pd.read_sql_query(query, conn, params=params)
                return df
                
        except Exception as e:
            logging.error(f"Error retrieving value screens: {e}")
            return pd.DataFrame()
    
    def save_backtest_result(self, strategy_name: str, start_date: str, end_date: str,
                           initial_capital: float, final_capital: float, 
                           total_return: float, annualized_return: float,
                           max_drawdown: float, sharpe_ratio: float,
                           num_trades: int, win_rate: float):
        """Save backtest results to database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO backtest_results 
                    (strategy_name, start_date, end_date, initial_capital, final_capital,
                     total_return, annualized_return, max_drawdown, sharpe_ratio, 
                     num_trades, win_rate)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    strategy_name, start_date, end_date, initial_capital, final_capital,
                    total_return, annualized_return, max_drawdown, sharpe_ratio,
                    num_trades, win_rate
                ))
                
                conn.commit()
                
        except Exception as e:
            logging.error(f"Error saving backtest result: {e}")
    
    def get_backtest_results(self, strategy_name: str = None) -> pd.DataFrame:
        """Get backtest results from database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                query = "SELECT * FROM backtest_results"
                params = []
                
                if strategy_name:
                    query += " WHERE strategy_name = ?"
                    params.append(strategy_name)
                
                query += " ORDER BY created_at DESC"
                
                df = pd.read_sql_query(query, conn, params=params)
                return df
                
        except Exception as e:
            logging.error(f"Error retrieving backtest results: {e}")
            return pd.DataFrame()
    
    def get_available_tickers(self) -> List[str]:
        """Get list of tickers with historical data."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("SELECT DISTINCT ticker FROM historical_prices")
                return [row[0] for row in cursor.fetchall()]
                
        except Exception as e:
            logging.error(f"Error retrieving available tickers: {e}")
            return []
    
    def get_data_summary(self) -> Dict:
        """Get summary of available data."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Get ticker count
                ticker_count = conn.execute("SELECT COUNT(DISTINCT ticker) FROM historical_prices").fetchone()[0]
                
                # Get date range
                date_range = conn.execute("SELECT MIN(date), MAX(date) FROM historical_prices").fetchone()
                
                # Get total records
                total_records = conn.execute("SELECT COUNT(*) FROM historical_prices").fetchone()[0]
                
                return {
                    'ticker_count': ticker_count,
                    'date_range': date_range,
                    'total_records': total_records
                }
                
        except Exception as e:
            logging.error(f"Error getting data summary: {e}")
            return {}

# Global instance
historical_data_service = HistoricalDataService()

if __name__ == "__main__":
    # Test the service
    service = HistoricalDataService()
    
    # Fetch some test data
    df = service.fetch_historical_data("AAPL", period="1y")
    if df is not None:
        print(f"Fetched {len(df)} records for AAPL")
        print(df.head())
    
    # Get summary
    summary = service.get_data_summary()
    print(f"Data summary: {summary}") 