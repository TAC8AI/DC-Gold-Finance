/**
 * Dakota Gold (DC) Live Data Fetcher
 * Pulls real-time stock data from Yahoo Finance API
 * 
 * INSTALLATION:
 * 1. In Google Sheets: Extensions → Apps Script
 * 2. Delete the default code
 * 3. Paste this entire script
 * 4. Click Save (💾)
 * 5. Close the Apps Script tab
 * 6. Back in your sheet, you can now use =FETCH_DC_PRICE() and =FETCH_DC_DATA()
 */

/**
 * Fetches current price for Dakota Gold (DC)
 * Usage: =FETCH_DC_PRICE()
 */
function FETCH_DC_PRICE() {
  const ticker = "DC";
  const url = `https://query1.finance.yahoo.com/v8/finance/chart/${ticker}`;
  
  try {
    const response = UrlFetchApp.fetch(url, {muteHttpExceptions: true});
    const json = JSON.parse(response.getContentText());
    
    if (json.chart && json.chart.result && json.chart.result[0]) {
      const price = json.chart.result[0].meta.regularMarketPrice;
      return price;
    } else {
      return "Error: No data";
    }
  } catch (error) {
    return "Error: " + error.message;
  }
}

/**
 * Fetches multiple data points for Dakota Gold (DC)
 * Usage: =FETCH_DC_DATA("marketCap") or =FETCH_DC_DATA("fiftyTwoWeekHigh")
 * 
 * Available fields:
 * - marketCap
 * - fiftyTwoWeekHigh
 * - fiftyTwoWeekLow
 * - previousClose
 * - volume
 */
function FETCH_DC_DATA(field) {
  const ticker = "DC";
  const url = `https://query1.finance.yahoo.com/v8/finance/chart/${ticker}`;
  
  try {
    const response = UrlFetchApp.fetch(url, {muteHttpExceptions: true});
    const json = JSON.parse(response.getContentText());
    
    if (json.chart && json.chart.result && json.chart.result[0]) {
      const meta = json.chart.result[0].meta;
      
      // Return the requested field
      if (meta[field] !== undefined) {
        return meta[field];
      } else {
        return "Error: Field not found";
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
      if (formulas[i][j].includes("FETCH_DC")) {
        const cell = sheet.getRange(i + 1, j + 1);
        const formula = formulas[i][j];
        cell.setFormula("");
        SpreadsheetApp.flush();
        cell.setFormula(formula);
      }
    }
  }
  
  SpreadsheetApp.getUi().alert('Data refreshed successfully!');
}

/**
 * Creates a custom menu when the spreadsheet opens
 */
function onOpen() {
  const ui = SpreadsheetApp.getUi();
  ui.createMenu('Dakota Gold Tools')
      .addItem('Refresh Live Data', 'refreshData')
      .addToUi();
}
