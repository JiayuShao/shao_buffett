"""Polling intervals and scheduled job times."""

from datetime import time
from config.constants import POLL_INTERVALS

# Scheduled times (Eastern Time)
MORNING_BRIEFING_TIME = time(9, 30)    # 9:30 AM ET
EVENING_SUMMARY_TIME = time(16, 15)    # 4:15 PM ET
WEEKLY_RESEARCH_DAY = 4                # Friday (0=Monday)
WEEKLY_RESEARCH_TIME = time(18, 0)     # 6:00 PM ET

# Polling intervals in seconds
NEWS_POLL_INTERVAL = POLL_INTERVALS["news"]           # 5 min
ANALYST_POLL_INTERVAL = POLL_INTERVALS["analyst"]      # 1 hour
EARNINGS_POLL_INTERVAL = POLL_INTERVALS["earnings"]    # 30 min
MACRO_POLL_INTERVAL = POLL_INTERVALS["macro"]          # 1 hour
SEC_FILING_POLL_INTERVAL = POLL_INTERVALS["sec_filings"]  # 1 hour
PRICE_ALERT_INTERVAL = POLL_INTERVALS["price_alerts"]  # 30 sec
CACHE_CLEANUP_INTERVAL = 3600                          # 1 hour
