import pytest
import os
import json
import time
from unittest.mock import Mock, patch
from services.stock_service import (
    RateLimiter,
    BatchProcessor,
    fetch_stock_data,
    fetch_stock_data_batch,
    validate_response_data,
    validate_api_key,
    clear_cache
)

# Test data
MOCK_PROFILE_DATA = [{
    "symbol": "AAPL",
    "price": 197.49,
    "mktCap": 2949671142000,
    "companyName": "Apple Inc."
}]

MOCK_KEY_METRICS = [{
    "peRatioTTM": 30.44,
    "pbRatioTTM": 44.33,
    "roeTTM": 151.31,
    "marketCapTTM": 2949671142000,
    "enterpriseValueOverEBITDATTM": 21.75,
    "freeCashFlowYieldTTM": 0.0334,
    "dividendYieldTTM": 0.0051,
    "payoutRatioTTM": 0.1574
}]

MOCK_RATIOS = [{
    "returnOnEquityTTM": 151.31,
    "returnOnAssetsTTM": 29.37,
    "netProfitMarginTTM": 24.30,
    "operatingProfitMarginTTM": 31.81,
    "grossProfitMarginTTM": 46.63,
    "debtEquityRatioTTM": 1.47,
    "currentRatioTTM": 0.82,
    "quickRatioTTM": 0.78,
    "cashRatioTTM": 0.19,
    "interestCoverageTTM": 0
}]

@pytest.fixture
def mock_response():
    """Fixture for mocking API responses."""
    def _mock_response(data, status_code=200):
        mock = Mock()
        mock.json.return_value = data
        mock.status_code = status_code
        return mock
    return _mock_response

@pytest.fixture
def rate_limiter():
    """Fixture for RateLimiter instance."""
    return RateLimiter(max_requests=5, window_size=60)

@pytest.fixture
def batch_processor():
    """Fixture for BatchProcessor instance."""
    return BatchProcessor()

class TestRateLimiter:
    def test_rate_limiter_initialization(self, rate_limiter):
        """Test RateLimiter initialization."""
        assert rate_limiter.max_requests == 5
        assert rate_limiter.window_size == 60
        assert len(rate_limiter.requests) == 0

    def test_rate_limiter_wait(self, rate_limiter):
        """Test rate limiter wait functionality."""
        # Fill up the rate limiter
        for _ in range(5):
            rate_limiter.wait_if_needed()
        
        # Should have 5 requests
        assert len(rate_limiter.requests) == 5
        
        # Next request should wait
        start_time = time.time()
        rate_limiter.wait_if_needed()
        elapsed = time.time() - start_time
        
        # Should have waited at least a small amount
        assert elapsed > 0

class TestBatchProcessor:
    def test_batch_processor_initialization(self, batch_processor):
        """Test BatchProcessor initialization."""
        assert batch_processor.retry_queue.empty()
        assert len(batch_processor.processed_tickers) == 0
        assert len(batch_processor.failed_tickers) == 0

    @patch('services.stock_service.fetch_stock_data')
    def test_process_ticker_success(self, mock_fetch, batch_processor):
        """Test successful ticker processing."""
        mock_fetch.return_value = {"pe_ratio": 30.44}
        result = batch_processor.process_ticker("AAPL")
        
        assert result == {"AAPL": {"pe_ratio": 30.44}}
        assert "AAPL" in batch_processor.processed_tickers
        assert "AAPL" not in batch_processor.failed_tickers

    @patch('services.stock_service.fetch_stock_data')
    def test_process_ticker_failure(self, mock_fetch, batch_processor):
        """Test failed ticker processing."""
        mock_fetch.return_value = None
        result = batch_processor.process_ticker("INVALID")
        
        assert result is None
        assert "INVALID" in batch_processor.failed_tickers
        assert "INVALID" not in batch_processor.processed_tickers
        assert not batch_processor.retry_queue.empty()

class TestDataValidation:
    def test_validate_profile_data(self):
        """Test profile data validation."""
        assert validate_response_data(MOCK_PROFILE_DATA, "profile/AAPL") is True
        
        # Test invalid data
        invalid_data = [{"symbol": "AAPL"}]  # Missing required fields
        assert validate_response_data(invalid_data, "profile/AAPL") is False

    def test_validate_key_metrics(self):
        """Test key metrics validation."""
        assert validate_response_data(MOCK_KEY_METRICS, "key-metrics-ttm/AAPL") is True
        
        # Test partial data (should be valid if any required field is present)
        partial_data = [{"peRatioTTM": 30.44}]  # Only one required field
        assert validate_response_data(partial_data, "key-metrics-ttm/AAPL") is True

    def test_validate_ratios(self):
        """Test ratios validation."""
        assert validate_response_data(MOCK_RATIOS, "ratios-ttm/AAPL") is True
        
        # Test partial data (should be valid if any required field is present)
        partial_data = [{"returnOnEquityTTM": 151.31}]  # Only one required field
        assert validate_response_data(partial_data, "ratios-ttm/AAPL") is True

class TestAPIKeyValidation:
    @patch('services.stock_service.requests.get')
    def test_validate_api_key_success(self, mock_get, mock_response):
        """Test successful API key validation."""
        mock_get.return_value = mock_response(MOCK_PROFILE_DATA)
        assert validate_api_key() is True

    @patch('services.stock_service.requests.get')
    def test_validate_api_key_failure(self, mock_get, mock_response):
        """Test failed API key validation."""
        mock_get.return_value = mock_response({}, status_code=401)
        assert validate_api_key() is False

class TestCacheManagement:
    def test_cache_operations(self, tmp_path):
        """Test cache operations."""
        # Set up test cache directory
        os.environ['CACHE_DIR'] = str(tmp_path)
        
        # Test cache clearing
        clear_cache()
        assert not os.path.exists(os.path.join(tmp_path, "stock_data_cache.json"))
        
        # Test cache saving and loading
        test_data = {"AAPL": {"pe_ratio": 30.44}}
        with open(os.path.join(tmp_path, "stock_data_cache.json"), 'w') as f:
            json.dump(test_data, f)
        
        # Verify cache exists
        assert os.path.exists(os.path.join(tmp_path, "stock_data_cache.json"))

@pytest.mark.integration
class TestIntegration:
    @patch('services.stock_service._fmp_get')
    def test_fetch_stock_data(self, mock_fmp_get):
        """Test complete stock data fetching."""
        # Mock all API responses with minimal valid data
        mock_fmp_get.side_effect = [
            MOCK_PROFILE_DATA,
            [{"totalDebt": 1000, "cashAndCashEquivalents": 500, "totalStockholdersEquity": 2000}],  # balance_sheet
            [{"revenue": 5000, "netIncome": 1000}],  # income_stmt
            [{"freeCashFlow": 300, "operatingCashFlow": 400}],  # cash_flow
            MOCK_KEY_METRICS,
            MOCK_RATIOS,
            [{"rating": "Buy", "targetPrice": 200}],  # sentiment
            [{"revenueGrowth": 0.1, "netIncomeGrowth": 0.05, "epsGrowth": 0.08}]  # growth
        ]
        
        data = fetch_stock_data("AAPL")
        assert data is not None
        assert data.get("pe_ratio") == 30.44
        assert data.get("market_cap") == 2949671142000
        assert data.get("roe") == 151.31

    @patch('services.stock_service.fetch_stock_data')
    def test_fetch_stock_data_batch(self, mock_fetch):
        """Test batch processing of multiple stocks."""
        # Mock successful responses
        mock_fetch.return_value = {
            "pe_ratio": 30.44,
            "market_cap": 2949671142000,
            "roe": 151.31
        }
        
        results = fetch_stock_data_batch(["AAPL", "MSFT", "GOOGL"])
        assert len(results) == 3
        assert all(ticker in results for ticker in ["AAPL", "MSFT", "GOOGL"])
        assert all(isinstance(data, dict) for data in results.values()) 