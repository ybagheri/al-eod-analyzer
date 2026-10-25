//+------------------------------------------------------------------+
//| ExportSymbols.mq5 - al-eod-analyzer S3 (Phase 5b), read-only.    |
//| Lists all symbols matching S&P 500 keywords with contract info   |
//| and first available M5 bar date; writes symbols_sp500.csv to     |
//| MQL5\Files. No trading calls, no terminal settings changed.      |
//+------------------------------------------------------------------+
#property copyright "al-eod-analyzer"
#property version   "1.00"
#property script_show_confirmations

#define OUT_FILE "symbols_sp500.csv"

void OnStart()
  {
   string keys[5];
   keys[0] = "SP500";
   keys[1] = "US500";
   keys[2] = "SPX";
   keys[3] = "ES";
   keys[4] = "S&P";

   int file = FileOpen(OUT_FILE, FILE_TXT | FILE_WRITE | FILE_ANSI);
   if(file == INVALID_HANDLE)
     {
      Print("ExportSymbols: cannot open ", OUT_FILE, " error=", GetLastError());
      return;
     }
   FileWriteString(file, "name,description,path,expiration,firstdate_m5,server_firstdate_m5,digits,point\n");

   int total = SymbolsTotal(false);
   int matched = 0;
   for(int i = 0; i < total; i++)
     {
      string name = SymbolName(i, false);
      string upper = name;
      StringToUpper(upper);
      bool hit = false;
      for(int k = 0; k < 5 && !hit; k++)
         if(StringFind(upper, keys[k]) >= 0)
            hit = true;
      if(!hit)
         continue;

      string description = SymbolInfoString(name, SYMBOL_DESCRIPTION);
      string path = SymbolInfoString(name, SYMBOL_PATH);
      datetime expiration = (datetime)SymbolInfoInteger(name, SYMBOL_EXPIRATION_TIME);
      datetime firstdate = (datetime)SeriesInfoInteger(name, PERIOD_M5, SERIES_FIRSTDATE);
      datetime server_firstdate = (datetime)SeriesInfoInteger(name, PERIOD_M5, SERIES_SERVER_FIRSTDATE);
      int digits = (int)SymbolInfoInteger(name, SYMBOL_DIGITS);
      double point = SymbolInfoDouble(name, SYMBOL_POINT);

      FileWriteString(file, CsvField(name) + "," + CsvField(description) + "," + CsvField(path) + "," +
                      IsoDate(expiration) + "," + IsoDate(firstdate) + "," + IsoDate(server_firstdate) + "," +
                      IntegerToString(digits) + "," + DoubleToString(point, digits) + "\r\n");
      matched++;
     }
   FileClose(file);
   Print("ExportSymbols: scanned ", total, " symbols, matched ", matched, " -> ", OUT_FILE);
  }

string CsvField(string value)
  {
   StringReplace(value, "\"", "\"\"");
   return "\"" + value + "\"";
  }

string IsoDate(datetime value)
  {
   if(value <= 0)
      return "";
   return TimeToString(value, TIME_DATE | TIME_MINUTES);
  }
