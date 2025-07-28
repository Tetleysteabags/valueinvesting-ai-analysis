from config import THRESHOLDS
import logging


def meets_value_criteria(data):
    """Return True if a stock meets the strict value criteria.

    Expected field names (v2):
        pe_ratio          : float
        price_to_book     : float
        debt_to_equity    : float
        roe               : float (fraction, not %)
    """
    try:
        roe_display = f"{data.get('roe', 0):.2%}" if data.get('roe') is not None else 'N/A'
        print(
            f"Checking: PE {data.get('pe_ratio', 'N/A')} < {THRESHOLDS['pe']} and "
            f"P/B {data.get('price_to_book', 'N/A')} < {THRESHOLDS['pb']} and "
            f"D/E {data.get('debt_to_equity', 'N/A')} < {THRESHOLDS['de']} and "
            f"ROE {roe_display} > {THRESHOLDS['roe']:.2%}"
        )
        return (
            data.get('pe_ratio') is not None and data['pe_ratio'] < THRESHOLDS['pe'] and
            data.get('price_to_book') is not None and data['price_to_book'] < THRESHOLDS['pb'] and
            data.get('debt_to_equity') is not None and data['debt_to_equity'] < THRESHOLDS['de'] and
            data.get('roe') is not None and data['roe'] > THRESHOLDS['roe']
        )
    except KeyError as e:
        print(f"Missing key in data: {e}")
        return False
