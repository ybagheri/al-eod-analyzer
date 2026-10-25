//+------------------------------------------------------------------+
//| ExportRatesM5.mq5 - al-eod-analyzer S3 (Phase 5b), read-only.    |
//| Inputs: InpSymbol, InpFrom, InpTo. Ensures the symbol is         |
//| selected, forces history load with chunked CopyRates retrying    |
//| while not synchronized, and writes rates_<symbol>_M5.csv plus    |
//| <symbol>_export_info.txt to MQL5\Files. Server time, ISO dates,  |
//| '.' decimals. No trading calls.                                  |
//+------------------------------------------------------------------+
#property copyright "al-eod-analyzer"
#property version   "1.00"
#property script_show_inputs

input string   InpSymbol = "US500";
input datetime InpFrom   = D'2019.06.01 00:00';
input datetime InpTo     = D'2026.12.31 23:59';

#define RATES_FMT        "rates_%s_M5.csv"
#define INFO_FMT         "%s_export_info.txt"
#define CHUNK_DAYS       30
#define MAX_SYNC_RETRY   120

void OnStart()
  {
   if(!SymbolSelect(InpSymbol, true))
     {
      Print("ExportRatesM5: symbol not found: ", InpSymbol);
      return;
     }
   int digits = (int)SymbolInfoInteger(InpSymbol, SYMBOL_DIGITS);
   string safe = SafeName(InpSymbol);
   string rates_file = StringFormat(RATES_FMT, safe);
   string info_file = StringFormat(INFO_FMT, InpSymbol);

   int out = FileOpen(rates_file, FILE_TXT | FILE_WRITE | FILE_ANSI);
   if(out == INVALID_HANDLE)
     {
      Print("ExportRatesM5: cannot open ", rates_file, " error=", GetLastError());
      return;
     }
   FileWriteString(out, "time_server,open,high,low,close,tick_volume,real_volume,spread\r\n");

   datetime chunk_start = InpFrom;
   long total = 0;
   datetime first_bar = 0;
   datetime last_bar = 0;
   while(chunk_start < InpTo)
     {
      datetime chunk_end = chunk_start + CHUNK_DAYS * 86400;
      if(chunk_end > InpTo)
         chunk_end = InpTo;
      MqlRates rates[];
      int got = CopyRatesChunk(InpSymbol, PERIOD_M5, chunk_start, chunk_end, rates);
      for(int i = 0; i < got; i++)
        {
         if(total == 0)
            first_bar = rates[i].time;
         last_bar = rates[i].time;
         FileWriteString(out, IsoTime(rates[i].time) + "," +
                         DoubleToString(rates[i].open, digits) + "," +
                         DoubleToString(rates[i].high, digits) + "," +
                         DoubleToString(rates[i].low, digits) + "," +
                         DoubleToString(rates[i].close, digits) + "," +
                         IntegerToString((long)rates[i].tick_volume) + "," +
                         IntegerToString((long)rates[i].real_volume) + "," +
                         IntegerToString((int)rates[i].spread) + "\r\n");
         total++;
        }
      chunk_start = chunk_end;
     }
   FileClose(out);

   WriteInfoFile(info_file, InpSymbol, total, first_bar, last_bar, digits);
   Print("ExportRatesM5: ", InpSymbol, " bars=", total, " -> ", rates_file);
  }

int CopyRatesChunk(string symbol, ENUM_TIMEFRAMES tf, datetime from, datetime to, MqlRates &rates[])
  {
   for(int attempt = 0; attempt < MAX_SYNC_RETRY; attempt++)
     {
      int got = CopyRates(symbol, tf, from, to, rates);
      if(got > 0)
         return got;
      Sleep(500);
     }
   Print("ExportRatesM5: history never synchronized for ", symbol, " window ", TimeToString(from));
   return 0;
  }

void WriteInfoFile(string filename, string symbol, long total, datetime first_bar, datetime last_bar, int digits)
  {
   int file = FileOpen(filename, FILE_TXT | FILE_WRITE | FILE_ANSI);
   if(file == INVALID_HANDLE)
     {
      Print("ExportRatesM5: cannot open ", filename, " error=", GetLastError());
      return;
     }
   WriteKV(file, "symbol", symbol);
   WriteKV(file, "description", SymbolInfoString(symbol, SYMBOL_DESCRIPTION));
   WriteKV(file, "path", SymbolInfoString(symbol, SYMBOL_PATH));
   WriteKV(file, "digits", IntegerToString(digits));
   WriteKV(file, "point", DoubleToString(SymbolInfoDouble(symbol, SYMBOL_POINT), digits));
   WriteKV(file, "tick_size", DoubleToString(SymbolInfoDouble(symbol, SYMBOL_TRADE_TICK_SIZE), digits));
   WriteKV(file, "tick_value", DoubleToString(SymbolInfoDouble(symbol, SYMBOL_TRADE_TICK_VALUE), 2));
   WriteKV(file, "contract_size", DoubleToString(SymbolInfoDouble(symbol, SYMBOL_TRADE_CONTRACT_SIZE), 2));
   WriteKV(file, "expiration", IsoDate((datetime)SymbolInfoInteger(symbol, SYMBOL_EXPIRATION_TIME)));
   WriteKV(file, "trade_mode", IntegerToString((int)SymbolInfoInteger(symbol, SYMBOL_TRADE_MODE)));
   WriteKV(file, "currency_profit", SymbolInfoString(symbol, SYMBOL_CURRENCY_PROFIT));
   WriteKV(file, "currency_margin", SymbolInfoString(symbol, SYMBOL_CURRENCY_MARGIN));
   WriteKV(file, "bar_count", IntegerToString(total));
   WriteKV(file, "first_bar", IsoTime(first_bar));
   WriteKV(file, "last_bar", IsoTime(last_bar));
   FileClose(file);
  }

void WriteKV(int file, string key, string value)
  {
   FileWriteString(file, key + ": " + value + "\r\n");
  }

string IsoTime(datetime value)
  {
   if(value <= 0)
      return "";
   MqlDateTime st;
   TimeToStruct(value, st);
   return StringFormat("%04d-%02d-%02d %02d:%02d:%02d", st.year, st.mon, st.day, st.hour, st.min, st.sec);
  }

string IsoDate(datetime value)
  {
   if(value <= 0)
      return "";
   string full = IsoTime(value);
   return StringSubstr(full, 0, 10);
  }

string SafeName(string symbol)
  {
   string out = symbol;
   for(int i = StringLen(out) - 1; i >= 0; i--)
     {
      ushort c = StringGetCharacter(out, i);
      bool ok = (c >= 'A' && c <= 'Z') || (c >= 'a' && c <= 'z') || (c >= '0' && c <= '9') || c == '_' || c == '-';
      if(!ok)
         StringSetCharacter(out, i, '_');
     }
   return out;
  }
