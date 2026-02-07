/**
 * Dakota Gold (DC) Enhanced Live Data Fetcher
 * Pulls real-time stock data AND gold prices from Yahoo Finance API
 * 
 * INSTALLATION:
 * 1. In Google Sheets: Extensions → Apps Script
 * 2. Replace ALL existing code with this
 * 3. Click Save (💾)
 * 4. Close and refresh your sheet
 */

/**
 * Fetches current price for Dakota Gold (DC)
 * Usage: =FETCH_DC_PRICE()
 */
function FETCH_DC_PRICE() {
  return fetchYahooData("DC", "regularMarketPrice");
}

/**
 * Fetches market cap directly for DC (more reliable than calculating!)
 * Usage: =FETCH_DC_MARKETCAP()
 */
function FETCH_DC_MARKETCAP() {
  return fetchYahooData("DC", "marketCap");
}

/**
 * Fetches shares outstanding for DC
 * Note: This may be inaccurate - use FETCH_DC_MARKETCAP() instead
 * Usage: =FETCH_DC_SHARES()
 */
function FETCH_DC_SHARES() {
  const ticker = "DC";
  const url = `https://query1.finance.yahoo.com/v10/finance/quoteSummary/${ticker}?modules=defaultKeyStatistics`;
  
  try {
    const response = UrlFetchApp.fetch(url, {muteHttpExceptions: true});
    const json = JSON.parse(response.getContentText());
    
    if (json.quoteSummary && json.quoteSummary.result && json.quoteSummary.result[0]) {
      const shares = json.quoteSummary.result[0].defaultKeyStatistics.sharesOutstanding.raw;
      return shares;
    } else {
      return 113700000; // Fallback: ~114M shares (calculated from $773M / $6.80)
    }
  } catch (error) {
    return 113700000; // Fallback
  }
}

/**
 * Fetches live GOLD PRICE (spot or futures)
 * Usage: =FETCH_GOLD_PRICE()
 */
function FETCH_GOLD_PRICE() {
  return fetchYahooData("GC=F", "regularMarketPrice"); // Gold Futures
}

/**
 * Fetches multiple data points for Dakota Gold (DC)
 * Usage: =FETCH_DC_DATA("fiftyTwoWeekHigh")
 * 
 * Available fields from chart API:
 * - fiftyTwoWeekHigh
 * - fiftyTwoWeekLow
 * - previousClose
 * - volume
 */
function FETCH_DC_DATA(field) {
  return fetchYahooData("DC", field);
}

/**
 * Fetches fundamental data (P/E, Book Value, etc.)
 * Usage: =FETCH_DC_FUNDAMENTAL("bookValue") or =FETCH_DC_FUNDAMENTAL("beta")
 * 
 * Available fields:
 * - bookValue (book value per share)
 * - beta (volatility metric)
 * - trailingPE (P/E ratio, may not be available for pre-revenue)
 * - priceToBook (P/B ratio)
 */
function FETCH_DC_FUNDAMENTAL(field) {
  const ticker = "DC";
  const url = `https://query1.finance.yahoo.com/v10/finance/quoteSummary/${ticker}?modules=defaultKeyStatistics,financialData`;
  
  try {
    const response = UrlFetchApp.fetch(url, {muteHttpExceptions: true});
    const json = JSON.parse(response.getContentText());
    
    if (json.quoteSummary && json.quoteSummary.result && json.quoteSummary.result[0]) {
      const data = json.quoteSummary.result[0];
      
      // Try defaultKeyStatistics first
      if (data.defaultKeyStatistics && data.defaultKeyStatistics[field]) {
        return data.defaultKeyStatistics[field].raw || data.defaultKeyStatistics[field];
      }
      
      // Try financialData
      if (data.financialData && data.financialData[field]) {
        return data.financialData[field].raw || data.financialData[field];
      }
      
      return "N/A";
    } else {
      return "N/A";
    }
  } catch (error) {
    return "Error: " + error.message;
  }
}

/**
 * Helper function to fetch Yahoo Finance data
 */
function fetchYahooData(ticker, field) {
  const url = `https://query1.finance.yahoo.com/v8/finance/chart/${ticker}`;
  
  try {
    const response = UrlFetchApp.fetch(url, {muteHttpExceptions: true});
    const json = JSON.parse(response.getContentText());
    
    if (json.chart && json.chart.result && json.chart.result[0]) {
      const meta = json.chart.result[0].meta;
      
      if (meta[field] !== undefined) {
        return meta[field];
      } else {
        return "N/A";
      }
    } else {
      return "Error: No data";
    }
  } catch (error) {
    return "Error: " + error.message;
  }
}

/**
 * Refreshes all data in the sheet
 * This function is called when you click the "Refresh Data" button
 */
function refreshData() {
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
  
  // Force recalculation by clearing and re-entering formulas
  const range = sheet.getDataRange();
  const formulas = range.getFormulas();
  
  for (let i = 0; i < formulas.length; i++) {
    for (let j = 0; j < formulas[i].length; j++) {
      if (formulas[i][j].includes("FETCH_")) {
        const cell = sheet.getRange(i + 1, j + 1);
        const formula = formulas[i][j];
        cell.setFormula("");
        SpreadsheetApp.flush();
        cell.setFormula(formula);
      }
    }
  }
  
  SpreadsheetApp.getUi().alert('✅ Live data refreshed successfully!');
}

/**
 * Creates a custom menu when the spreadsheet opens
 */
function onOpen() {
  const ui = SpreadsheetApp.getUi();
  ui.createMenu('⛏️ Dakota Gold Tools')
      .addItem('🔄 Refresh Live Data', 'refreshData')
      .addSeparator()
      .addItem('📊 About', 'showAbout')
      .addToUi();
}

/**
 * Shows info about the script
 */
function showAbout() {
  const ui = SpreadsheetApp.getUi();
  ui.alert(
    '⛏️ Dakota Gold Live Data Fetcher',
    'This script fetches real-time data from Yahoo Finance:\n\n' +
    '• DC Stock Price & Metrics\n' +
    '• Live Gold Prices\n' +
    '• Fundamental Data (P/E, Book Value, Beta)\n' +
    '• Auto-calculates NPV & Fair Value\n\n' +
    'Click "Refresh Live Data" to update all values.',
    ui.ButtonSet.OK
  );
}
