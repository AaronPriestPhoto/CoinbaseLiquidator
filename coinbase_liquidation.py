#!/usr/bin/env python3
"""
Coinbase Cryptocurrency Liquidation Script

This script connects to Coinbase and liquidates all cryptocurrencies except USDC to USD.
Features:
- Trial run mode (default) to preview actions without executing
- Live mode flag to actually execute trades
- Minimum threshold to avoid dust transactions
- CSV report generation for all transactions
- Safety checks and confirmations

Usage:
    python coinbase_liquidation.py --trial  # Preview what will be sold (default)
    python coinbase_liquidation.py --live   # Actually execute the liquidation
    python coinbase_liquidation.py --live --min-threshold 10.0  # Set minimum USD value
"""

import os
import sys

# Ensure the script works from any working directory (useful for StreamDeck buttons)
script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

import argparse
import csv
import json
import logging
import sys
import time
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

import pandas as pd
from coinbase.rest import RESTClient
from requests.exceptions import HTTPError


class CoinbaseLiquidationBot:
    def __init__(self, api_key_path: str = "cdp_api_key.json", min_threshold: float = 0.01):
        """
        Initialize the liquidation bot.
        
        Args:
            api_key_path: Path to the Coinbase API key JSON file
            min_threshold: Minimum USD value to consider for liquidation (default: $0.01)
        """
        self.min_threshold = min_threshold
        self.client = None
        self.api_key_path = api_key_path
        self.setup_logging()
        
    def setup_logging(self):
        """Setup logging configuration."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('liquidation.log'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def load_api_credentials(self) -> bool:
        """Load API credentials from JSON file."""
        try:
            with open(self.api_key_path, 'r') as f:
                credentials = json.load(f)
            
            # Extract the API key name and private key
            api_key_name = credentials['name']
            private_key = credentials['privateKey']
            
            # Initialize the Coinbase REST client
            self.client = RESTClient(api_key=api_key_name, api_secret=private_key)
            self.logger.info("Successfully loaded Coinbase API credentials")
            return True
            
        except FileNotFoundError:
            self.logger.error(f"API key file not found: {self.api_key_path}")
            return False
        except json.JSONDecodeError:
            self.logger.error(f"Invalid JSON in API key file: {self.api_key_path}")
            return False
        except Exception as e:
            self.logger.error(f"Error loading API credentials: {str(e)}")
            return False
    
    def get_accounts(self) -> List[Dict]:
        """Get all trading accounts from Coinbase."""
        try:
            response = self.client.get_accounts()
            accounts = response.accounts
            self.logger.info(f"Retrieved {len(accounts)} total accounts from Coinbase")
            return accounts
        except HTTPError as e:
            self.logger.error(f"Error getting accounts: {e}")
            return []
        except Exception as e:
            self.logger.error(f"Unexpected error getting accounts: {str(e)}")
            return []
    
    def get_portfolio_balances(self) -> List[Dict]:
        """Get balances from portfolio breakdown (more accurate than individual accounts)."""
        balances = []
        
        try:
            # Get portfolio
            portfolios = self.client.get_portfolios()
            if not portfolios.portfolios:
                self.logger.error("No portfolios found")
                return []
                
            portfolio_id = portfolios.portfolios[0].uuid
            self.logger.info(f"Using portfolio: {portfolio_id}")
            
            # Get portfolio breakdown
            breakdown = self.client.get_portfolio_breakdown(portfolio_id)
            
            # The breakdown contains spot_positions, futures_positions, etc.
            # We want spot_positions for regular crypto
            breakdown_list = breakdown.breakdown.spot_positions
            self.logger.info(f"Processing {len(breakdown_list)} portfolio assets...")
            
            for asset in breakdown_list:
                try:
                    currency = asset.asset
                    balance_value = float(asset.total_balance_crypto)
                    usd_value = float(asset.total_balance_fiat)
                    
                    # Only include assets with non-zero balances
                    if balance_value > 0 and usd_value >= self.min_threshold:
                        balances.append({
                            'account_id': asset.account_uuid,
                            'currency': currency,
                            'balance': balance_value,
                            'currency_code': currency,
                            'usd_value': usd_value
                        })
                        self.logger.info(f"Found balance: {balance_value} {currency} = ${usd_value:.2f}")
                        
                except Exception as e:
                    self.logger.warning(f"Error processing asset {asset.asset}: {str(e)}")
                    continue
            
            self.logger.info(f"Completed processing. Found {len(balances)} assets with non-zero balances.")
            return balances
            
        except Exception as e:
            self.logger.error(f"Error getting portfolio breakdown: {str(e)}")
            return []

    def process_accounts_for_balances(self, accounts) -> List[Dict]:
        """Process accounts to extract balances for all non-zero accounts."""
        balances = []
        total_accounts = len(accounts)
        
        self.logger.info(f"Processing {total_accounts} accounts for balances...")
        
        for i, account in enumerate(accounts):
            try:
                # Use the account data directly from get_accounts() - no need for individual API calls
                account_id = account.uuid
                
                # Only include accounts with non-zero balances
                balance_value = float(account.available_balance.get('value', 0))
                if balance_value > 0:
                    balances.append({
                        'account_id': account_id,
                        'currency': account.currency,
                        'balance': balance_value,
                        'currency_code': account.currency
                    })
                    self.logger.info(f"Found balance: {balance_value} {account.currency}")
                
                # Show progress every 10 accounts
                if (i + 1) % 10 == 0:
                    self.logger.info(f"Processed {i + 1}/{total_accounts} accounts...")
                    
            except Exception as e:
                self.logger.warning(f"Error processing account {account.uuid}: {str(e)}")
                continue
        
        self.logger.info(f"Completed processing. Found {len(balances)} accounts with non-zero balances.")
        return balances
    
    def get_account_balances(self) -> List[Dict]:
        """Get account balances for all non-zero accounts."""
        accounts = self.get_accounts()
        return self.process_accounts_for_balances(accounts)
    
    def get_current_prices(self, currencies: List[str]) -> Dict[str, float]:
        """Get current USD prices for given currencies with rate limiting."""
        prices = {}
        total_currencies = len(currencies)
        
        self.logger.info(f"Getting current prices for {total_currencies} currencies...")
        
        for i, currency in enumerate(currencies):
            try:
                # Get the current price for the currency
                product_id = f"{currency}-USD"
                product_response = self.client.get_product(product_id)
                price = float(product_response.price)
                prices[currency] = price
                self.logger.info(f"Got price for {currency}: ${price:.2f}")
                
                # Rate limiting: wait 0.1 seconds between requests to avoid 429 errors
                # Coinbase API allows ~10 requests per second, so 0.1s delay is conservative
                time.sleep(0.1)
                
            except HTTPError as e:
                if e.response.status_code == 429:
                    self.logger.warning(f"Rate limited for {currency}, waiting 2 seconds before retry...")
                    time.sleep(2)
                    try:
                        # Retry once after rate limit
                        product_response = self.client.get_product(product_id)
                        price = float(product_response.price)
                        prices[currency] = price
                        self.logger.info(f"Got price for {currency} on retry: ${price:.2f}")
                    except Exception as retry_e:
                        self.logger.warning(f"Failed to get price for {currency} even after retry: {str(retry_e)}")
                else:
                    self.logger.warning(f"Error getting price for {currency}: {str(e)}")
                continue
            except Exception as e:
                self.logger.warning(f"Error getting price for {currency}: {str(e)}")
                continue
        
        self.logger.info(f"Successfully retrieved prices for {len(prices)}/{total_currencies} currencies")
        return prices
    
    def calculate_liquidation_plan(self, balances: List[Dict]) -> List[Dict]:
        """Calculate what should be liquidated based on current balances."""
        liquidation_plan = []
        
        # Filter out USDC and USD
        currencies_to_liquidate = [b for b in balances 
                                 if b['currency_code'] not in ['USDC', 'USD'] 
                                 and b['balance'] > 0]
        
        if not currencies_to_liquidate:
            self.logger.info("No cryptocurrencies found to liquidate (excluding USDC and USD)")
            return liquidation_plan
        
        # Get current prices only for currencies without pre-calculated USD values
        currencies_needing_prices = [b['currency_code'] for b in currencies_to_liquidate 
                                   if 'usd_value' not in b]
        
        prices = {}
        if currencies_needing_prices:
            self.logger.info(f"Getting prices for {len(currencies_needing_prices)} currencies without pre-calculated USD values...")
            prices = self.get_current_prices(currencies_needing_prices)
        else:
            self.logger.info("All currencies have pre-calculated USD values from portfolio, skipping price API calls.")
        
        for balance in currencies_to_liquidate:
            currency = balance['currency_code']
            amount = balance['balance']
            
            # Use pre-calculated USD value from portfolio breakdown if available
            if 'usd_value' in balance:
                usd_value = balance['usd_value']
                # Get current price for display
                price_per_unit = prices.get(currency, usd_value / amount if amount > 0 else 0)
            else:
                # Fallback to price calculation
                if currency in prices:
                    price_per_unit = prices[currency]
                    usd_value = amount * price_per_unit
                else:
                    self.logger.warning(f"Could not get price for {currency}, skipping")
                    continue
            
            if usd_value >= self.min_threshold:
                liquidation_plan.append({
                    'currency': currency,
                    'amount': amount,
                    'price_per_unit': price_per_unit,
                    'usd_value': usd_value,
                    'account_id': balance['account_id']
                })
            else:
                self.logger.info(f"Skipping {currency} (${usd_value:.2f}) - below minimum threshold (${self.min_threshold})")
        
        return liquidation_plan
    
    def execute_liquidation(self, liquidation_plan: List[Dict], live_mode: bool = False) -> List[Dict]:
        """Execute the liquidation plan."""
        executed_trades = []
        
        if not liquidation_plan:
            self.logger.info("No trades to execute")
            return executed_trades
        
        for trade in liquidation_plan:
            currency = trade['currency']
            amount = trade['amount']
            usd_value = trade['usd_value']
            
            if live_mode:
                try:
                    # Create a market sell order
                    client_order_id = f"liquidation_{currency}_{int(datetime.now().timestamp())}"
                    order = self.client.create_order(
                        product_id=f"{currency}-USD",
                        side="SELL",
                        client_order_id=client_order_id,
                        order_configuration={
                            "market_market_ioc": {
                                "base_size": self._format_amount_for_order(currency, amount)
                            }
                        }
                    )
                    
                    # Get order ID from response (try different possible attributes)
                    order_id = None
                    if hasattr(order, 'order_id'):
                        order_id = order.order_id
                    elif hasattr(order, 'id'):
                        order_id = order.id
                    else:
                        order_id = client_order_id
                    
                    # Debug: Log the full order response
                    self.logger.info(f"[DEBUG] Order response for {currency}: {order}")
                    if hasattr(order, 'status'):
                        self.logger.info(f"[DEBUG] Order status: {order.status}")
                    
                    executed_trades.append({
                        'currency': currency,
                        'amount': amount,
                        'usd_value': usd_value,
                        'order_id': order_id,
                        'status': 'EXECUTED',
                        'timestamp': datetime.now().isoformat()
                    })
                    
                    self.logger.info(f"[SUCCESS] EXECUTED: Sold {amount} {currency} for ~${usd_value:.2f}")
                    
                except Exception as e:
                    error_msg = str(e)
                    if "Invalid product_id" in error_msg:
                        self.logger.warning(f"[SKIP] {currency} has no USD trading pair - skipping")
                        error_msg = "No USD trading pair available"
                    else:
                        self.logger.error(f"[ERROR] FAILED to sell {currency}: {error_msg}")
                    
                    executed_trades.append({
                        'currency': currency,
                        'amount': amount,
                        'usd_value': usd_value,
                        'order_id': None,
                        'status': 'FAILED',
                        'error': error_msg,
                        'timestamp': datetime.now().isoformat()
                    })
            else:
                # Trial mode - just log what would happen
                executed_trades.append({
                    'currency': currency,
                    'amount': amount,
                    'usd_value': usd_value,
                    'order_id': 'TRIAL_MODE',
                    'status': 'TRIAL',
                    'timestamp': datetime.now().isoformat()
                })
                
                self.logger.info(f"[TRIAL] Would sell {amount} {currency} for ~${usd_value:.2f}")
        
        return executed_trades
    
    def _format_amount_for_order(self, currency: str, amount: float) -> str:
        """Format amount for order based on currency precision requirements."""
        import math
        
        # Common precision rules for different cryptocurrencies
        precision_map = {
            # High precision (8 decimals)
            'BTC': 8, 'ETH': 8, 'LTC': 8, 'BCH': 8, 'DOT': 8, 'LINK': 8,
            'UNI': 8, 'AAVE': 8, 'SUSHI': 8, 'CRV': 8, 'YFI': 8, 'COMP': 8,
            'INDEX': 8, 'CVX': 8, 'EIGEN': 8, 'KERNEL': 8, 'ETHFI': 8,
            
            # Medium precision (6 decimals)
            'USDC': 6, 'USDT': 6, 'DAI': 6, 'BUSD': 6, 'TUSD': 6,
            'HOPR': 6, 'OMNI': 6, 'CLANKER': 6, 'LOKA': 6, 'SWELL': 6,
            'FIS': 6, 'PENGU': 6, 'SD': 6, 'GIGA': 6, 'HFT': 6,
            'ALT': 6, 'REZ': 6, 'SXT': 6,
            
            # Low precision (4 decimals)
            'DOGE': 4, 'SHIB': 4, 'PEPE': 4, 'FLOKI': 4, 'BONK': 4, 'WIF': 4,
            'PIRATE': 4, 'POPCAT': 4, 'COOKIE': 4, 'KEYCAT': 4,
            'TURBO': 4, 'DEGEN': 4, 'MOG': 4, 'DOGINME': 4,
            'ALEPH': 4, 'MOODENG': 4, 'AST': 4, 'PRCL': 4, 'PROMPT': 4,
            'PNUT': 4, 'IDEX': 4, 'MDT': 4, 'SYRUP': 4,
            
            # Very low precision (2 decimals)
            'STRK': 2, 'ARB': 2, 'OP': 2, 'MATIC': 2, 'AVAX': 2, 'SOL': 2,
            'ATOM': 2, 'NEAR': 2, 'FTM': 2, 'ONE': 2, 'ALGO': 2,
            
            # Integer precision (0 decimals) - problematic tokens
            'EDGE': 0, 'ZORA': 0,
            
            # Integer precision (0 decimals)
            'XRP': 0, 'XLM': 0, 'ADA': 0, 'TRX': 0, 'EOS': 0, 'XTZ': 0,
        }
        
        # Get precision for this currency, default to 6 decimals
        precision = precision_map.get(currency, 6)
        
        # For integer precision (0 decimals), use floor to avoid insufficient funds
        if precision == 0:
            formatted = str(int(math.floor(amount)))
        else:
            # Format with appropriate precision and use floor to avoid insufficient funds
            multiplier = 10 ** precision
            floored_amount = math.floor(amount * multiplier) / multiplier
            formatted = f"{floored_amount:.{precision}f}"
            
            # Remove trailing zeros and decimal point if not needed
            if '.' in formatted:
                formatted = formatted.rstrip('0').rstrip('.')
        
        return formatted
    
    def generate_csv_report(self, executed_trades: List[Dict], filename: str = None):
        """Generate a CSV report of all executed trades."""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            mode = "trial" if any(trade['status'] == 'TRIAL' for trade in executed_trades) else "live"
            filename = f"coinbase_liquidation_report_{mode}_{timestamp}.csv"
        
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            if executed_trades:
                # Define consistent fieldnames to handle both successful and failed trades
                fieldnames = ['currency', 'amount', 'usd_value', 'order_id', 'status', 'timestamp', 'error']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                
                # Ensure all trades have consistent fields
                for trade in executed_trades:
                    # Add missing fields with None values
                    for field in fieldnames:
                        if field not in trade:
                            trade[field] = None
                    writer.writerow(trade)
        
        self.logger.info(f"[REPORT] CSV report generated: {filename}")
        return filename
    
    def run_liquidation(self, live_mode: bool = False):
        """Main method to run the liquidation process."""
        self.logger.info("[START] Starting Coinbase Liquidation Bot")
        self.logger.info(f"Mode: {'LIVE' if live_mode else 'TRIAL'}")
        self.logger.info(f"Minimum threshold: ${self.min_threshold}")
        
        # Load API credentials
        if not self.load_api_credentials():
            self.logger.error("Failed to load API credentials. Exiting.")
            return False
        
        # Calculate liquidation plan
        self.logger.info("[ANALYSIS] Analyzing current balances...")
        
        # Get balances from portfolio breakdown (more accurate)
        balances = self.get_portfolio_balances()
        
        if not balances:
            self.logger.info("No cryptocurrencies found with non-zero balances.")
            self.logger.info("All your cryptocurrency accounts have zero balance.")
            return True
            
        liquidation_plan = self.calculate_liquidation_plan(balances)
        
        if not liquidation_plan:
            self.logger.info("No cryptocurrencies found to liquidate (excluding USDC and USD).")
            return True
        
        # Display plan
        total_usd_value = sum(trade['usd_value'] for trade in liquidation_plan)
        self.logger.info(f"\n[PLAN] Liquidation Plan Summary:")
        self.logger.info(f"Total cryptocurrencies to liquidate: {len(liquidation_plan)}")
        self.logger.info(f"Total estimated USD value: ${total_usd_value:.2f}")
        
        for trade in liquidation_plan:
            self.logger.info(f"  - {trade['amount']:.8f} {trade['currency']} @ ${trade['price_per_unit']:.2f} = ${trade['usd_value']:.2f}")
        
        # Display prominent total
        self.logger.info(f"\n{'='*60}")
        self.logger.info(f"TOTAL PORTFOLIO VALUE: ${total_usd_value:.2f} USD")
        self.logger.info(f"{'='*60}")
        
        if not live_mode:
            self.logger.info("\n[TRIAL] TRIAL MODE: No actual trades will be executed")
            self.logger.info("Use --live flag to execute actual trades")
        else:
            # Confirmation for live mode
            print(f"\n[WARNING] You are about to liquidate {len(liquidation_plan)} cryptocurrencies worth ~${total_usd_value:.2f}")
            print("This action cannot be undone!")
            confirmation = input("Type 'CONFIRM' to proceed: ")
            
            if confirmation != 'CONFIRM':
                self.logger.info("Liquidation cancelled by user")
                return False
        
        # Execute liquidation
        self.logger.info(f"\n{'Executing' if live_mode else 'Simulating'} liquidation...")
        executed_trades = self.execute_liquidation(liquidation_plan, live_mode)
        
        # Generate CSV report
        csv_filename = self.generate_csv_report(executed_trades)
        
        # Summary
        successful_trades = [t for t in executed_trades if t['status'] in ['EXECUTED', 'TRIAL']]
        failed_trades = [t for t in executed_trades if t['status'] == 'FAILED']
        
        # Calculate total value from successful trades
        total_value = sum(trade.get('usd_value', 0) for trade in successful_trades)
        
        self.logger.info(f"\n[SUMMARY] Liquidation Summary:")
        self.logger.info(f"Successful trades: {len(successful_trades)}")
        if failed_trades:
            self.logger.info(f"Failed trades: {len(failed_trades)}")
        self.logger.info(f"CSV report: {csv_filename}")
        
        if successful_trades:
            self.logger.info(f"\n{'='*60}")
            self.logger.info(f"TOTAL VALUE LIQUIDATED: ${total_value:.2f} USD")
            self.logger.info(f"{'='*60}")
        
        return True


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Coinbase Cryptocurrency Liquidation Bot",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python coinbase_liquidation.py                    # Trial run (default)
  python coinbase_liquidation.py --live            # Execute actual trades
  python coinbase_liquidation.py --live --min-threshold 5.0  # Set $5 minimum
        """
    )
    
    parser.add_argument(
        '--live', 
        action='store_true', 
        help='Execute actual trades (default: trial mode)'
    )
    
    parser.add_argument(
        '--min-threshold', 
        type=float, 
        default=0.01, 
        help='Minimum USD value to consider for liquidation (default: $0.01)'
    )
    
    parser.add_argument(
        '--api-key', 
        default='cdp_api_key.json', 
        help='Path to Coinbase API key JSON file (default: cdp_api_key.json)'
    )
    
    args = parser.parse_args()
    
    # Create and run the liquidation bot
    bot = CoinbaseLiquidationBot(
        api_key_path=args.api_key,
        min_threshold=args.min_threshold
    )
    
    success = bot.run_liquidation(live_mode=args.live)
    
    if success:
        print("\n[SUCCESS] Liquidation process completed successfully!")
    else:
        print("\n[ERROR] Liquidation process failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()

