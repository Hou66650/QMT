import os
import sys
from pathlib import Path

os.environ["MARKET_DATA_PROVIDER"] = "mock"
os.environ["WATCHLIST_FILE"] = str(Path(__file__).parent / ".watchlist-test.json")
sys.path.insert(0, str(Path(__file__).parents[1]))
