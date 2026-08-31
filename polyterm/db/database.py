"""SQLite database manager for persistent storage"""

import sqlite3
import json
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from contextlib import contextmanager

from .models import Wallet, Trade, Alert, MarketSnapshot, ArbitrageOpportunity, ResolutionOutcome
