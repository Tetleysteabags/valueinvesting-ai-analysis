import json
import hashlib
import os

def load_cache(cache_file):
    return json.load(open(cache_file)) if os.path.exists(cache_file) else {}

def save_cache(cache, cache_file):
    with open(cache_file, "w") as f:
        json.dump(cache, f)

def get_cache_key(messages):
    return hashlib.sha256(json.dumps(messages, sort_keys=True).encode()).hexdigest()