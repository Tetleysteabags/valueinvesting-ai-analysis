import logging

def setup_logging():
    logging.basicConfig(
        filename='stock_selection.log',
        level=logging.INFO,
        format='%(asctime)s %(levelname)s %(message)s'
    )
    logging.getLogger().addHandler(logging.StreamHandler())