import requests
import pandas as pd
import datetime
import time
import os
from pathlib import Path

# Configuration
BASE_URL = "https://www.deribit.com/api/v2/"
DATA_DIR = Path("./data/App3_Data")
OUTPUT_FILE = DATA_DIR / "volatility_data.csv"
CURRENCY = "BTC"

# Ensure data directory exists
DATA_DIR.mkdir(parents=True, exist_ok=True)

def fetch_instruments():
    """Fetch all BTC option instruments from Deribit"""
    params = {
        "currency": CURRENCY,
        "kind": "option",
        "expired": "false"
    }
    
    try:
        res = requests.get(BASE_URL + "public/get_instruments", params=params)
        res.raise_for_status()
        return res.json()["result"]
    except requests.exceptions.RequestException as e:
        print(f"Error fetching instruments: {e}")
        return None

def get_current_btc_price():
    """Get current BTC index price"""
    try:
        ticker_res = requests.get(BASE_URL + "public/get_index", params={"currency": CURRENCY}).json()
        return ticker_res["result"]["BTC"]
    except requests.exceptions.RequestException as e:
        print(f"Error fetching current BTC price: {e}")
        return None

def extract_iv_data(option_list, option_type):
    """Extract implied volatility data for a list of options"""
    iv_data = []
    for opt in option_list:
        try:
            summary = requests.get(BASE_URL + "public/ticker", 
                                 params={"instrument_name": opt["instrument_name"]}).json()
            result = summary.get("result")
            if result:
                iv = result.get("mark_iv")
                if iv is not None and iv > 0:
                    iv_data.append({
                        "timestamp": datetime.datetime.now().isoformat(),
                        "expiry_date": datetime.datetime.fromtimestamp(opt["expiration_timestamp"] / 1000).date().isoformat(),
                        "expiry_timestamp": opt["expiration_timestamp"],
                        "strike": opt["strike"],
                        "implied_volatility": iv,
                        "option_type": option_type,
                        "instrument_name": opt["instrument_name"]
                    })
        except requests.exceptions.RequestException as e:
            pass
        time.sleep(0.01)  # Rate limiting
    return iv_data

def save_to_csv(data, filename):
    """Save data to CSV, appending if file exists"""
    df = pd.DataFrame(data)
    
    if os.path.exists(filename):
        existing_df = pd.read_csv(filename)
        combined_df = pd.concat([existing_df, df], ignore_index=True)
        combined_df.to_csv(filename, index=False)
    else:
        df.to_csv(filename, index=False)

def main():
    print(f"{datetime.datetime.now()} - Starting data collection...")
    
    # Fetch current BTC price for reference
    btc_price = get_current_btc_price()
    print(f"Current BTC Price: {btc_price or 'Unknown'}")
    
    # Fetch all instruments
    all_options = fetch_instruments()
    if not all_options:
        return
    
    # Get unique expiries
    expiries = sorted(list(set(opt["expiration_timestamp"] for opt in all_options)))
    print(f"Found {len(expiries)} unique expiration dates")
    
    # Process each expiry
    all_iv_data = []
    for expiry_ts in expiries:
        expiry_date = datetime.datetime.fromtimestamp(expiry_ts / 1000).date()
        print(f"Processing expiry: {expiry_date}")
        
        calls = [opt for opt in all_options 
                if opt["option_type"] == "call" and opt["expiration_timestamp"] == expiry_ts]
        puts = [opt for opt in all_options 
               if opt["option_type"] == "put" and opt["expiration_timestamp"] == expiry_ts]
        
        call_data = extract_iv_data(calls, "call")
        put_data = extract_iv_data(puts, "put")
        
        all_iv_data.extend(call_data)
        all_iv_data.extend(put_data)
    
    # Save to CSV
    if all_iv_data:
        save_to_csv(all_iv_data, OUTPUT_FILE)
        print(f"Saved {len(all_iv_data)} data points to {OUTPUT_FILE}")
    else:
        print("No IV data collected in this run")
    
    print("Data collection complete\n")

if __name__ == "__main__":
    main()