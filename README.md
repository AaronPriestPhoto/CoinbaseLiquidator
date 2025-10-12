# Coinbase Cryptocurrency Liquidation Bot

A Python script to automatically liquidate all cryptocurrencies (except USDC and USD) to USD on Coinbase, with comprehensive safety features, precision handling, and detailed reporting.

## 🚀 Quick Start

### 1. Clone the Repository
```bash
git clone https://github.com/AaronPriestPhoto/CoinbaseLiquidator.git
cd CoinbaseLiquidator
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Test Your Connection
```bash
python test_connection.py
```
This will verify your API key works and show your account balances with a detailed portfolio summary.

### 4. Run Trial Liquidation
```bash
python coinbase_liquidation.py
```
This shows what would be sold without actually doing anything.

## ✨ Features

- 🔍 **Trial Mode (Default)**: Preview all actions without executing trades
- 💰 **Live Mode**: Actually execute liquidation trades
- 🛡️ **Safety Features**: Minimum threshold, confirmation prompts, comprehensive logging
- 📊 **CSV Reporting**: Detailed reports of all transactions
- ⚡ **Smart Filtering**: Automatically excludes USDC and USD from liquidation
- 🎯 **Dust Protection**: Configurable minimum USD value threshold (default: $0.01)
- 🔧 **Precision Handling**: Automatic decimal precision management for different cryptocurrencies
- 📈 **Portfolio Analysis**: Uses Coinbase portfolio API for accurate balance detection
- 🚦 **Rate Limiting**: Built-in API rate limiting to prevent errors
- 💡 **Error Recovery**: Graceful handling of API errors and edge cases

## 🎯 Common Commands

```bash
# See what would be sold (safe)
python coinbase_liquidation.py

# Set minimum to $5 (skip small amounts)
python coinbase_liquidation.py --min-threshold 5.0

# Actually execute trades (after reviewing trial)
python coinbase_liquidation.py --live

# Execute with $10 minimum
python coinbase_liquidation.py --live --min-threshold 10.0

# Test connection and view portfolio
python test_connection.py
```

## 📋 What You'll See

### Trial Run Output
```
[START] Starting Coinbase Liquidation Bot
Mode: TRIAL
Minimum threshold: $0.01
Successfully loaded Coinbase API credentials
[ANALYSIS] Analyzing current balances...
Using portfolio: e38cecfc-4d71-5442-aee8-cd8b965fb7c4
Processing 125 portfolio assets...
Found balance: 884.8 ALEPH = $60.39
Found balance: 413.27 MOODENG = $63.73
...

[PLAN] Liquidation Plan Summary:
Total cryptocurrencies to liquidate: 63
Total estimated USD value: $3247.69
  - 884.80000000 ALEPH @ $0.07 = $60.39
  - 413.27000000 MOODENG @ $0.15 = $63.73
  - 3172.50000000 AST @ $0.03 = $100.41
  ...

============================================================
TOTAL PORTFOLIO VALUE: $3247.69 USD
============================================================

[TRIAL] TRIAL MODE: No actual trades will be executed
Use --live flag to execute actual trades

[SUMMARY] Liquidation Summary:
Successful trades: 63
CSV report: coinbase_liquidation_report_trial_20251001_143319.csv

============================================================
TOTAL VALUE LIQUIDATED: $3247.69 USD
============================================================

[SUCCESS] Liquidation process completed successfully!
```

### Live Run Output
```
[START] Starting Coinbase Liquidation Bot
Mode: LIVE
Minimum threshold: $1.0
...

[WARNING] You are about to liquidate 63 cryptocurrencies worth ~$3247.69
This action cannot be undone!
Type 'CONFIRM' to proceed: CONFIRM

Executing liquidation...
[SUCCESS] EXECUTED: Sold 884.8 ALEPH for ~$60.39
[SUCCESS] EXECUTED: Sold 413.27 MOODENG for ~$63.73
[SUCCESS] EXECUTED: Sold 3172.5 AST for ~$100.41
...

[SUMMARY] Liquidation Summary:
Successful trades: 62
Failed trades: 1
CSV report: coinbase_liquidation_report_live_20251001_143349.csv

============================================================
TOTAL VALUE LIQUIDATED: $3247.93 USD
============================================================

[SUCCESS] Liquidation process completed successfully!
```

## 🛡️ Safety Features

### 1. Trial Mode (Default)
- **Never executes real trades by default**
- Shows exactly what would be sold and for how much
- Generates CSV report of planned transactions
- Displays total portfolio value prominently

### 2. Live Mode Safety
- Requires explicit `--live` flag
- Shows confirmation prompt with total value
- Requires typing "CONFIRM" to proceed
- Comprehensive logging of all actions

### 3. Minimum Threshold
- Prevents liquidation of dust amounts
- Default: $0.01 minimum USD value
- Configurable via `--min-threshold` parameter

### 4. Smart Filtering
- Automatically excludes USDC and USD from liquidation
- Uses Coinbase portfolio API for accurate balance detection
- Only processes accounts with non-zero balances
- Handles API errors gracefully

### 5. Precision Handling
- **Automatic decimal precision management** for different cryptocurrencies
- **Floor-based rounding** to prevent "insufficient funds" errors
- **Currency-specific precision rules**:
  - High precision (8 decimals): BTC, ETH, UNI, etc.
  - Medium precision (6 decimals): USDC, HOPR, OMNI, etc.
  - Low precision (4 decimals): DOGE, BONK, ALEPH, etc.
  - Integer precision (0 decimals): EDGE, ZORA, XRP, etc.

## 📊 Output Files

### 1. CSV Reports
- **Trial Mode**: `coinbase_liquidation_report_trial_YYYYMMDD_HHMMSS.csv`
- **Live Mode**: `coinbase_liquidation_report_live_YYYYMMDD_HHMMSS.csv`

**CSV Format:**
| Column | Description |
|--------|-------------|
| currency | Cryptocurrency symbol (e.g., BTC, ETH) |
| amount | Amount of cryptocurrency to sell |
| usd_value | Estimated USD value |
| order_id | Coinbase order ID (or client_order_id for live trades) |
| status | EXECUTED, TRIAL, or FAILED |
| timestamp | ISO timestamp of the operation |
| error | Error message (if status is FAILED) |

### 2. Log Files
- **Console Output**: Real-time status updates with clear formatting
- **Debug Information**: Detailed API responses and error messages

## 🔧 Technical Improvements

### Portfolio API Integration
- Uses `get_portfolios()` and `get_portfolio_breakdown()` for accurate balance detection
- Pre-calculated USD values from portfolio data (no additional price API calls needed)
- Handles all asset types including spot positions

### Rate Limiting
- Built-in `time.sleep(0.1)` between API calls
- Retry logic for 429 (rate limit) errors
- Optimized to minimize API calls

### Error Handling
- **Invalid trading pairs**: Gracefully skips currencies without USD pairs
- **Precision errors**: Automatic decimal precision management
- **Insufficient funds**: Floor-based rounding prevents over-selling
- **API errors**: Comprehensive error logging and recovery

## 🆘 Troubleshooting

### Common Issues

1. **"API key file not found"**
   - Ensure `cdp_api_key.json` is in the current directory
   - Use `--api-key` to specify a different path

2. **"No cryptocurrencies found to liquidate"**
   - Check if you have non-USDC/USD balances
   - Verify minimum threshold isn't too high
   - Run `python test_connection.py` to see your portfolio

3. **"Error getting accounts"**
   - Verify API key permissions
   - Check internet connection
   - Ensure API key hasn't expired

4. **"Invalid product_id" or "Too many decimals"**
   - These are now handled automatically with precision management
   - The script will skip unsupported currencies and format amounts correctly

5. **"Insufficient balance"**
   - The script now uses floor-based rounding to prevent this
   - Check if the currency was already partially sold

### Getting Help

1. **Connection issues**: Run `python test_connection.py`
2. **No cryptocurrencies found**: Check if you have non-USDC balances
3. **API errors**: Verify your API key permissions
4. **Check logs**: Look at console output for detailed error info
5. **Review CSV reports**: Check the generated reports for transaction details

## 🔒 Security Reminders

- Keep your `cdp_api_key.json` file secure
- Never commit API keys to version control
- Always test in trial mode first
- Review CSV reports before live execution
- Consider backing up your account data before running live liquidation

## 📈 Example Workflow

### Step 1: Test Connection
```bash
python test_connection.py
```
Verify your API connection and see your current portfolio.

### Step 2: Trial Run
```bash
python coinbase_liquidation.py --min-threshold 5.0
```
Review the liquidation plan and check the CSV report.

### Step 3: Execute Live (Optional)
```bash
python coinbase_liquidation.py --live --min-threshold 5.0
```
Type "CONFIRM" when prompted to execute the liquidation.

## 📋 Command Line Options

- `--live`: Execute actual trades (default: trial mode)
- `--min-threshold FLOAT`: Minimum USD value to consider for liquidation (default: $0.01)
- `--api-key PATH`: Path to Coinbase API key JSON file (default: cdp_api_key.json)

## 🎯 Requirements

- Python 3.13+ (tested and optimized)
- `coinbase-advanced-py>=1.3.0`
- `pandas>=2.2.2`
- `python-dotenv>=1.0.1`

## 📝 License

This script is provided as-is for educational and personal use. Always test thoroughly before using with real funds.

## 🚀 Recent Updates

- ✅ **Fixed order configuration**: Changed from `quote_size` to `base_size` for market sell orders
- ✅ **Added precision handling**: Automatic decimal precision management for different cryptocurrencies
- ✅ **Improved portfolio detection**: Uses Coinbase portfolio API for accurate balances
- ✅ **Enhanced error handling**: Graceful handling of invalid trading pairs and precision errors
- ✅ **Added rate limiting**: Built-in API rate limiting to prevent errors
- ✅ **Updated for Python 3.13**: All dependencies compatible with latest Python version
- ✅ **Improved logging**: Clear, emoji-free logging that works in all terminals
- ✅ **CSV report fixes**: Proper handling of both successful and failed trades