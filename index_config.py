"""
index_config.py
Single source of truth for all 25 indices in the Valuation Tracker.

Each entry:
- sheet_name: name as it appears in original Excel (for export compat)
- display:    clean display name
- yf:         yfinance ticker (for price + RSI)
- nse_name:   NSE official index name (matches ind_close_all_*.csv)
- start_year: earliest year we'll fetch — set to MAX(index inception, 2012)
              because NSE ind_close_all archive only goes back to ~2011.
              For newer indices (Digital, Defense, Manufacturing), uses launch year.
"""

INDICES = [
    # ── Broad market (NSE PE/PB data back to ~2012) ──
    {"sheet_name": "NIFTY 50",            "display": "Nifty 50",            "yf": "^NSEI",                  "nse_name": "Nifty 50",                  "start_year": 2012},
    {"sheet_name": "NIFTY NEXT 50",       "display": "Nifty Next 50",       "yf": "^NSMIDCP",               "nse_name": "Nifty Next 50",             "start_year": 2012},
    {"sheet_name": "NIFTY MID 100",       "display": "Nifty Midcap 100",    "yf": "NIFTY_MIDCAP_100.NS",    "nse_name": "Nifty Midcap 100",          "start_year": 2012},
    {"sheet_name": "NIFTY MID 150",       "display": "Nifty Midcap 150",    "yf": "NIFTY_MID_SELECT.NS",    "nse_name": "Nifty Midcap 150",          "start_year": 2016},  # launched Apr 2016
    {"sheet_name": "NIFTY SMALL 250",     "display": "Nifty Smallcap 250",  "yf": "^CNXSC",                 "nse_name": "Nifty Smallcap 250",        "start_year": 2016},  # launched Apr 2016

    # ── Banking & Financial ──
    {"sheet_name": "NIFTY BANK",          "display": "Nifty Bank",          "yf": "^NSEBANK",               "nse_name": "Nifty Bank",                "start_year": 2012},
    {"sheet_name": "Nifty Private Bank",  "display": "Nifty Private Bank",  "yf": "NIFTY_PVT_BANK.NS",      "nse_name": "Nifty Private Bank",        "start_year": 2016},  # launched Jan 2016
    {"sheet_name": "PSU BANK",            "display": "Nifty PSU Bank",      "yf": "^CNXPSUBANK",            "nse_name": "Nifty PSU Bank",            "start_year": 2012},
    {"sheet_name": "Nifty Fin Ser",       "display": "Nifty Fin Services",  "yf": "NIFTY_FIN_SERVICE.NS",   "nse_name": "Nifty Financial Services",  "start_year": 2012},

    # ── Sectoral ──
    {"sheet_name": "Nifty Auto",          "display": "Nifty Auto",          "yf": "^CNXAUTO",               "nse_name": "Nifty Auto",                "start_year": 2012},
    {"sheet_name": "NIFTY IT",            "display": "Nifty IT",            "yf": "^CNXIT",                 "nse_name": "Nifty IT",                  "start_year": 2012},
    {"sheet_name": "Nifty Infra",         "display": "Nifty Infra",         "yf": "^CNXINFRA",              "nse_name": "Nifty Infrastructure",      "start_year": 2012},
    {"sheet_name": "Nifty FMCG",          "display": "Nifty FMCG",          "yf": "^CNXFMCG",               "nse_name": "Nifty FMCG",                "start_year": 2012},
    {"sheet_name": "Nifty Realty",        "display": "Nifty Realty",        "yf": "^CNXREALTY",             "nse_name": "Nifty Realty",              "start_year": 2012},
    {"sheet_name": "Nifty Energy",        "display": "Nifty Energy",        "yf": "^CNXENERGY",             "nse_name": "Nifty Energy",              "start_year": 2012},
    {"sheet_name": "BSE Power",           "display": "Nifty Power",         "yf": "NIFTY_ENR.NS",           "nse_name": "Nifty Energy",              "start_year": 2012},
    {"sheet_name": "CPSE",                "display": "Nifty CPSE",          "yf": "CPSEETF.NS",             "nse_name": "Nifty CPSE",                "start_year": 2014},  # CPSE index Mar 2014
    {"sheet_name": "Defense",             "display": "Nifty India Defence", "yf": "INDIADEFENCE.NS",        "nse_name": "Nifty India Defence",       "start_year": 2024},  # launched Apr 2024
    {"sheet_name": "Nifty Pharma",        "display": "Nifty Pharma",        "yf": "^CNXPHARMA",             "nse_name": "Nifty Pharma",              "start_year": 2012},
    {"sheet_name": "Nifty Consumption",   "display": "Nifty Consumption",   "yf": "^CNXCONSUM",             "nse_name": "Nifty India Consumption",   "start_year": 2012},
    {"sheet_name": "Nifty Commodity",     "display": "Nifty Commodities",   "yf": "^CNXCMDT",               "nse_name": "Nifty Commodities",         "start_year": 2012},
    {"sheet_name": "NIFTY DIGITAL",       "display": "Nifty Digital",       "yf": "NIFTY_DIGITAL.NS",       "nse_name": "Nifty India Digital",       "start_year": 2023},  # launched Aug 2023
    {"sheet_name": "Nifty Manufacturing", "display": "Nifty Manufacturing", "yf": "NIFTY_MANUFACTURING.NS", "nse_name": "Nifty India Manufacturing", "start_year": 2022},  # launched Mar 2022
    {"sheet_name": "Nifty Metal",         "display": "Nifty Metal",         "yf": "^CNXMETAL",              "nse_name": "Nifty Metal",               "start_year": 2012},

    # ── International (Nasdaq = price-only, no PE in our pipeline) ──
    {"sheet_name": "Nasdaq 100",          "display": "Nasdaq 100",          "yf": "^NDX",                   "nse_name": None,                        "start_year": 2012},
]

# Quick lookups
BY_SHEET   = {ix["sheet_name"]: ix for ix in INDICES}
BY_DISPLAY = {ix["display"]:    ix for ix in INDICES}
BY_NSE     = {ix["nse_name"]:   ix for ix in INDICES if ix["nse_name"]}
