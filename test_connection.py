#!/usr/bin/env python3
"""
Simple test script to verify Coinbase API connection.
Run this before using the main liquidation script.
"""

import json
import sys
from coinbase.rest import RESTClient
from requests.exceptions import HTTPError


def test_coinbase_connection():
    """Test the Coinbase API connection."""
    print("[TEST] Testing Coinbase API connection...")
    
    try:
        # Load API credentials
        with open('cdp_api_key.json', 'r') as f:
            credentials = json.load(f)
        
        api_key_name = credentials['name']
        private_key = credentials['privateKey']
        
        print(f"[SUCCESS] API key loaded: {api_key_name[:50]}...")
        
        # Initialize client
        client = RESTClient(api_key=api_key_name, api_secret=private_key)
        print("[SUCCESS] REST client initialized")
        
        # Test API connection by getting portfolio (like the main script)
        portfolios = client.get_portfolios()
        if not portfolios.portfolios:
            print("[ERROR] No portfolios found")
            return False
            
        portfolio_id = portfolios.portfolios[0].uuid
        print(f"[SUCCESS] Using portfolio: {portfolio_id}")
        
        # Get portfolio breakdown to find actual crypto holdings
        breakdown = client.get_portfolio_breakdown(portfolio_id)
        breakdown_list = breakdown.breakdown.spot_positions
        
        # Filter for assets with non-zero balances
        assets_with_balance = []
        total_usd_value = 0
        
        for asset in breakdown_list:
            balance_value = float(asset.total_balance_crypto)
            usd_value = float(asset.total_balance_fiat)
            
            if balance_value > 0:
                assets_with_balance.append({
                    'currency': asset.asset,
                    'balance': balance_value,
                    'usd_value': usd_value
                })
                total_usd_value += usd_value
        
        print(f"[SUCCESS] API connection successful! Found {len(assets_with_balance)} assets with balances")
        print(f"[SUCCESS] Total portfolio value: ${total_usd_value:.2f} USD")
        
        # Show asset summary (top holdings)
        print("\n[INFO] Top Holdings Summary:")
        # Sort by USD value (descending)
        sorted_assets = sorted(assets_with_balance, key=lambda x: x['usd_value'], reverse=True)
        
        for asset in sorted_assets[:10]:  # Show top 10 holdings
            print(f"  - {asset['currency']}: {asset['balance']} = ${asset['usd_value']:.2f}")
        
        if len(sorted_assets) > 10:
            remaining_value = sum(a['usd_value'] for a in sorted_assets[10:])
            print(f"  ... and {len(sorted_assets) - 10} more assets worth ${remaining_value:.2f}")
            
        # Show liquidation value (excluding USDC and USD)
        liquidation_assets = [a for a in sorted_assets if a['currency'] not in ['USDC', 'USD']]
        liquidation_value = sum(a['usd_value'] for a in liquidation_assets)
        calculated_total = sum(a['usd_value'] for a in sorted_assets)
        
        # Find USDC and USD specifically
        usdc_asset = next((a for a in sorted_assets if a['currency'] == 'USDC'), None)
        usd_asset = next((a for a in sorted_assets if a['currency'] == 'USD'), None)
        
        print(f"\n[INFO] Verification: {len(sorted_assets)} assets total ${calculated_total:.2f} USD")
        
        print(f"\n[INFO] Assets NOT liquidated (kept as stablecoin/fiat):")
        if usdc_asset:
            print(f"  - USDC: {usdc_asset['balance']} = ${usdc_asset['usd_value']:.2f}")
        if usd_asset:
            print(f"  - USD: {usd_asset['balance']} = ${usd_asset['usd_value']:.2f}")
        
        stablecoin_total = (usdc_asset['usd_value'] if usdc_asset else 0) + (usd_asset['usd_value'] if usd_asset else 0)
        print(f"  - Stablecoin/Fiat total: ${stablecoin_total:.2f}")
        
        print(f"\n[INFO] Liquidation value (crypto only): ${liquidation_value:.2f} USD from {len(liquidation_assets)} crypto assets")
        
        print("\n[SUCCESS] Connection test successful! You can now run the liquidation script.")
        return True
        
    except FileNotFoundError:
        print("[ERROR] cdp_api_key.json file not found")
        print("   Make sure the API key file is in the current directory")
        return False
        
    except json.JSONDecodeError:
        print("[ERROR] Invalid JSON in cdp_api_key.json")
        print("   Check the file format")
        return False
        
    except HTTPError as e:
        print(f"[ERROR] Coinbase API Error: {e}")
        print("   Check your API key permissions and try again")
        return False
        
    except Exception as e:
        print(f"[ERROR] Unexpected error: {str(e)}")
        return False


if __name__ == "__main__":
    success = test_coinbase_connection()
    sys.exit(0 if success else 1)

