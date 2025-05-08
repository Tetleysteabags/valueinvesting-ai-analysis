import pytest
import requests
from services.fmp_client import (
    get_profile, get_balance_sheet,
    get_income_statement, get_cash_flow, get_historical_price
)

class DummyResponse:
    def __init__(self, json_data):
        self._json = json_data
    def raise_for_status(self):
        pass
    def json(self):
        return self._json

@pytest.fixture(autouse=True)
def patch_requests(monkeypatch):
    def fake_get(url, params):
        if "profile" in url:
            return DummyResponse([{"symbol":"AAPL","price":150.0,"marketCap":200e9}])
        if "balance-sheet-statement" in url:
            return DummyResponse([{"totalAssets":300e9,"totalLiabilities":100e9}])
        if "income-statement" in url:
            return DummyResponse([{"revenue":100e9,"netIncome":10e9}])
        if "cash-flow-statement" in url:
            return DummyResponse([{"operatingCashFlow":12e9,"freeCashFlow":5e9}])
        if "historical-price-eod" in url:
            return DummyResponse([{"date":"2025-05-01","close":145.0}])
        raise ValueError("Unmocked URL "+url)
    monkeypatch.setattr(requests, "get", fake_get)

def test_get_profile():
    p = get_profile("AAPL")
    assert p["symbol"] == "AAPL"
    assert p["price"] == 150.0

def test_get_balance_sheet():
    bs = get_balance_sheet("AAPL")
    assert "totalAssets" in bs and bs["totalAssets"] == 300e9

def test_get_income_statement():
    inc = get_income_statement("AAPL")
    assert inc["revenue"] == 100e9

def test_get_cash_flow():
    cf = get_cash_flow("AAPL")
    assert cf["freeCashFlow"] == 5e9

def test_get_historical_price():
    hist = get_historical_price("AAPL")
    assert isinstance(hist, list)
    assert hist[0]["date"] == "2025-05-01"
