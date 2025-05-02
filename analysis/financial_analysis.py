from config import THRESHOLDS

def meets_value_criteria(data):
    try:
        print(f"Checking: {data['pe_ratio']} < {THRESHOLDS['pe']} and {data['price_to_book_ratio']} < {THRESHOLDS['pb']} and {data['de_ratio']} < {THRESHOLDS['de']} and {data['roe_ratio']} > {THRESHOLDS['roe']}")
        return (
            data['pe_ratio'] is not None and data['pe_ratio'] < THRESHOLDS["pe"] and
            data['price_to_book_ratio'] is not None and data['price_to_book_ratio'] < THRESHOLDS["pb"] and
            data['de_ratio'] is not None and data['de_ratio'] < THRESHOLDS["de"] and
            data['roe_ratio'] is not None and data['roe_ratio'] > THRESHOLDS["roe"]
        )
    except KeyError as e:
        print(f"Missing key in data: {e}")
        return None
