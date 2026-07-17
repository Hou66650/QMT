import os
import sys
from pathlib import Path

os.environ["MARKET_DATA_PROVIDER"] = "mock"
os.environ["WATCHLIST_FILE"] = str(Path(__file__).parent / ".watchlist-test.json")
os.environ["PAPER_TRADING_FILE"] = str(Path(__file__).parent / ".paper-trading-test.json")
sys.path.insert(0, str(Path(__file__).parents[1]))
