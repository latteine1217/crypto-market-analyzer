The issue with missing Open Interest (OI) data has been resolved.

**Root Cause:**
The collector was successfully connecting to Binance, but the API response (via CCXT) did not contain the USD value (`openInterestValue`) or the price, which resulted in `open_interest_usd` being stored as `NULL` in the database. The dashboard relies on this USD value for the charts.

**Fix Implemented:**
1.  **Enhanced Collector Logic:** Modified `collector-py/src/connectors/open_interest_collector.py` to automatically fetch the current ticker price if the USD value is missing. It now calculates `open_interest_usd = open_interest * price` as a fallback.
2.  **Immediate Collection:** Updated `collector-py/src/main.py` to trigger Open Interest collection immediately upon startup (instead of waiting for the first 5-minute interval).

**Verification:**
- Verified that `open_interest_usd` is now being correctly populated in the database.
- Restarted the `crypto_collector` service to apply the changes.

The Open Interest charts on the dashboard should now be displaying data correctly.