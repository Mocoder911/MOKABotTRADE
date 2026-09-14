//+------------------------------------------------------------------+
//|                                          FTMO_Challenge_EA.mq5   |
//|                                          MOKABot Grid Trading EA  |
//|                                          FTMO $100K Challenge      |
//+------------------------------------------------------------------+
#property copyright "MOKABot"
#property version   "1.01"
#property strict

//+------------------------------------------------------------------+
//| INPUT PARAMETERS                                                  |
//+------------------------------------------------------------------+
input group "=== Currency Pairs (STRICT) ==="
input string AllowedPairs = "EURUSD,GBPUSD,USDCAD,USDJPY,AUDUSD,NZDUSD";

input group "=== Base Position Settings ==="
input double   BaseLotSize         = 0.03;    // Base position lot size
input int      MaxBasePositions    = 20;      // Max base positions across all pairs

input group "=== Grid / Safety Step Settings ==="
input double   GridLotSize         = 0.03;    // Grid step lot size
input double   GridStepLossUSD     = 15.0;    // Grid trigger: -$ pair net floating loss

input group "=== Basket Take-Profit ==="
input double   BasketTP_USD        = 10.0;    // Basket TP per pair in USD

input group "=== Freeze Engine ==="
input double   FreezeDrawdownLimit = -3500.0; // Freeze at this floating loss

input group "=== Execution Safety ==="
input int      ExecutionDelayMs    = 500;     // Delay between orders (ms)
input int      GridCooldownSec     = 10;      // Min seconds between grid steps per pair
input int      BaseCooldownSec     = 5;       // Min seconds after basket TP before new base
input int      MagicBase           = 100000;  // Magic number for base positions
input int      MagicGrid           = 200000;  // Magic number for grid positions
input string   BaseComment         = "MOKABase";
input string   GridComment         = "MOKAGrid";

//+------------------------------------------------------------------+
//| GLOBAL VARIABLES                                                  |
//+------------------------------------------------------------------+
string   g_pairs[];
int      g_pairCount     = 0;
bool     g_freezeActive  = false;
datetime g_lastOrderTime = 0;
datetime g_lastGridTime[];   // Per-pair cooldown tracker for grid steps
datetime g_lastBaseClose[];  // Per-pair cooldown tracker after basket TP

//+------------------------------------------------------------------+
//| Expert initialization                                             |
//+------------------------------------------------------------------+
int OnInit()
{
   g_pairCount = ParsePairs(AllowedPairs, g_pairs);

   if(g_pairCount == 0)
   {
      Print("ERROR: No valid pairs configured!");
      return INIT_FAILED;
   }

   // Initialize per-pair cooldown arrays
   ArrayResize(g_lastGridTime, g_pairCount);
   ArrayResize(g_lastBaseClose, g_pairCount);
   ArrayInitialize(g_lastGridTime, 0);
   ArrayInitialize(g_lastBaseClose, 0);

   Print("=== FTMO Challenge EA v1.01 Initialized ===");
   Print("Pairs: ", g_pairCount, " | Base Lot: ", BaseLotSize, " | Grid Lot: ", GridLotSize);
   Print("Max Base: ", MaxBasePositions, " | Basket TP: $", BasketTP_USD);
   Print("Grid Step: -$", GridStepLossUSD, " | Freeze: $", FreezeDrawdownLimit);
   Print("===========================================");

   // Verify all pairs are available in Market Watch
   for(int i = 0; i < g_pairCount; i++)
   {
      if(!SymbolSelect(g_pairs[i], true))
         Print("WARNING: Pair ", g_pairs[i], " not available in Market Watch");
   }

   EventSetTimer(1);
   return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
//| Expert deinitialization                                           |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   EventKillTimer();
   Print("FTMO Challenge EA stopped. Reason: ", reason);
}

//+------------------------------------------------------------------+
//| Timer function - main logic loop (runs every 1 second)            |
//+------------------------------------------------------------------+
void OnTimer()
{
   // Step 1: Check freeze engine (global floating loss protection)
   CheckFreezeEngine();

   // Step 2: Check basket TP for each pair (close if +$10 reached)
   CheckBasketTP();

   // Step 3: Count current base positions
   int totalBase = CountBasePositions();

   // Step 4: Open new base positions if under limit and not frozen
   if(!g_freezeActive && totalBase < MaxBasePositions)
      OpenBasePositions();

   // Step 5: Check grid steps (INDEPENDENT of base limit, paused only if frozen)
   if(!g_freezeActive)
      CheckGridSteps();
}

//+------------------------------------------------------------------+
//| PARSE PAIRS from comma-separated string                           |
//+------------------------------------------------------------------+
int ParsePairs(string input, string &result[])
{
   string temp[];
   int count = StringSplit(input, ',', temp);
   int valid = 0;

   ArrayResize(result, count);

   for(int i = 0; i < count; i++)
   {
      string pair = temp[i];
      StringTrimLeft(pair);
      StringTrimRight(pair);
      StringToUpper(pair);

      string resolved = ResolveSymbol(pair);
      if(resolved != "")
      {
         result[valid] = resolved;
         valid++;
      }
      else
         Print("WARNING: Could not find symbol for ", pair);
   }

   ArrayResize(result, valid);
   return valid;
}

//+------------------------------------------------------------------+
//| RESOLVE SYMBOL - handles broker suffixes (FTMO etc.)              |
//+------------------------------------------------------------------+
string ResolveSymbol(string pair)
{
   if(SymbolInfoDouble(pair, SYMBOL_BID) > 0)
      return pair;

   string suffixes[] = {"", ".", "m", "#", ".m", "pro", "_"};
   for(int i = 0; i < ArraySize(suffixes); i++)
   {
      string test = pair + suffixes[i];
      if(SymbolInfoDouble(test, SYMBOL_BID) > 0)
         return test;
   }

   return "";
}

//+------------------------------------------------------------------+
//| FREEZE ENGINE                                                     |
//| - Activates when total floating loss <= FreezeDrawdownLimit       |
//| - Stops new base orders AND grid steps                            |
//| - Keeps existing positions open (NO realized loss)                |
//| - Auto-unfreezes when floating loss recovers                      |
//+------------------------------------------------------------------+
void CheckFreezeEngine()
{
   double totalFloating = GetTotalFloatingPL();
   bool shouldBeFrozen = (totalFloating <= FreezeDrawdownLimit);

   if(shouldBeFrozen && !g_freezeActive)
   {
      g_freezeActive = true;
      Print("!!! FREEZE ACTIVATED !!! Floating: $", DoubleToString(totalFloating, 2),
            " <= $", DoubleToString(FreezeDrawdownLimit, 2));
   }
   else if(!shouldBeFrozen && g_freezeActive)
   {
      g_freezeActive = false;
      Print("!!! FREEZE DEACTIVATED !!! Floating recovered: $", DoubleToString(totalFloating, 2));
   }
}

//+------------------------------------------------------------------+
//| TOTAL FLOATING P/L across ALL positions                           |
//+------------------------------------------------------------------+
double GetTotalFloatingPL()
{
   double total = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket > 0)
         total += PositionGetDouble(POSITION_PROFIT) + PositionGetDouble(POSITION_SWAP);
   }
   return total;
}

//+------------------------------------------------------------------+
//| COUNT BASE POSITIONS across all pairs (magic = MagicBase)         |
//+------------------------------------------------------------------+
int CountBasePositions()
{
   int count = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket > 0)
         if(PositionGetInteger(POSITION_MAGIC) == MagicBase)
            count++;
   }
   return count;
}

//+------------------------------------------------------------------+
//| COUNT ALL POSITIONS for a specific symbol (base + grid)           |
//+------------------------------------------------------------------+
int CountPairPositions(string symbol)
{
   int count = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket > 0)
         if(PositionGetString(POSITION_SYMBOL) == symbol)
            count++;
   }
   return count;
}

//+------------------------------------------------------------------+
//| PAIR NET FLOATING P/L (all positions for a symbol)                |
//| Used for BOTH basket TP check and grid step trigger               |
//+------------------------------------------------------------------+
double GetPairFloatingPL(string symbol)
{
   double pl = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket > 0)
         if(PositionGetString(POSITION_SYMBOL) == symbol)
            pl += PositionGetDouble(POSITION_PROFIT) + PositionGetDouble(POSITION_SWAP);
   }
   return pl;
}

//+------------------------------------------------------------------+
//| CHECK BASKET TP - close ALL positions for a pair if +$10 reached  |
//| After close, records cooldown to prevent immediate re-entry       |
//+------------------------------------------------------------------+
void CheckBasketTP()
{
   for(int p = 0; p < g_pairCount; p++)
   {
      string symbol = g_pairs[p];
      double pairPL = GetPairFloatingPL(symbol);

      if(pairPL >= BasketTP_USD)
      {
         Print("BASKET TP HIT: ", symbol, " P/L=$", DoubleToString(pairPL, 2),
               " >= $", DoubleToString(BasketTP_USD, 2));
         CloseAllPositionsForSymbol(symbol);
         g_lastBaseClose[p] = TimeCurrent();   // Record cooldown
         Sleep(ExecutionDelayMs);
      }
   }
}

//+------------------------------------------------------------------+
//| CLOSE ALL POSITIONS for a specific symbol                         |
//+------------------------------------------------------------------+
void CloseAllPositionsForSymbol(string symbol)
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket > 0)
         if(PositionGetString(POSITION_SYMBOL) == symbol)
         {
            ClosePosition(ticket);
            Sleep(ExecutionDelayMs);
         }
   }
}

//+------------------------------------------------------------------+
//| CLOSE SINGLE POSITION by ticket                                   |
//+------------------------------------------------------------------+
bool ClosePosition(ulong ticket)
{
   if(!PositionSelectByTicket(ticket))
      return false;

   MqlTradeRequest request = {};
   MqlTradeResult  result  = {};

   request.action    = TRADE_ACTION_DEAL;
   request.symbol    = PositionGetString(POSITION_SYMBOL);
   request.volume    = PositionGetDouble(POSITION_VOLUME);
   request.deviation = 20;
   request.position  = ticket;
   request.type_time = ORDER_TIME_GTC;
   request.type_filling = ORDER_FILLING_FOK;

   if(PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY)
   {
      request.type  = ORDER_TYPE_SELL;
      request.price = SymbolInfoDouble(request.symbol, SYMBOL_ASK);
   }
   else
   {
      request.type  = ORDER_TYPE_BUY;
      request.price = SymbolInfoDouble(request.symbol, SYMBOL_BID);
   }

   request.magic   = (int)PositionGetInteger(POSITION_MAGIC);
   request.comment = "BasketTP";

   if(OrderSend(request, result))
   {
      if(result.retcode == TRADE_RETCODE_DONE)
      {
         Print("CLOSED: ", request.symbol, " ticket=", ticket);
         return true;
      }
   }

   Print("CLOSE FAILED: ", request.symbol, " ticket=", ticket, " err=", result.retcode);
   return false;
}

//+------------------------------------------------------------------+
//| OPEN BASE POSITIONS                                               |
//| - Skips pairs that already have open positions                    |
//| - Respects base cooldown after basket TP close                    |
//| - Uses RSI → MACD → EMA trend for direction                      |
//| - Checks spread safety before entry                               |
//+------------------------------------------------------------------+
void OpenBasePositions()
{
   int totalBase = CountBasePositions();

   for(int p = 0; p < g_pairCount; p++)
   {
      if(totalBase >= MaxBasePositions)
         break;

      string symbol = g_pairs[p];

      // Skip if pair already has any open positions
      if(CountPairPositions(symbol) > 0)
         continue;

      // Respect base cooldown after basket TP closed this pair
      if(TimeCurrent() - g_lastBaseClose[p] < BaseCooldownSec)
         continue;

      // Determine direction via indicators
      string direction = GetDirection(symbol);
      if(direction == "NONE")
         continue;

      // Spread check
      if(!IsSpreadSafe(symbol))
         continue;

      // Execute base order
      if(ExecuteTrade(symbol, direction, BaseLotSize, MagicBase, BaseComment))
      {
         totalBase++;
         Sleep(ExecutionDelayMs);
      }
   }
}

//+------------------------------------------------------------------+
//| GET DIRECTION using RSI(14) → MACD(12,26,9) → EMA(20/50)         |
//| Priority: RSI oversold/overbought → MACD crossover → EMA trend   |
//+------------------------------------------------------------------+
string GetDirection(string symbol)
{
   //--- Step 1: RSI(14)
   double rsi = GetRSI(symbol, 14);
   if(rsi >= 0)
   {
      if(rsi < 30) return "BUY";
      if(rsi > 70) return "SELL";
   }

   //--- Step 2: MACD(12,26,9) crossover
   int macdHandle = iMACD(symbol, PERIOD_M15, 12, 26, 9, PRICE_CLOSE);
   if(macdHandle != INVALID_HANDLE)
   {
      double macdMain[], macdSignal[];
      ArraySetAsSeries(macdMain, true);
      ArraySetAsSeries(macdSignal, true);

      if(CopyBuffer(macdHandle, 0, 0, 3, macdMain) > 0 &&
         CopyBuffer(macdHandle, 1, 0, 3, macdSignal) > 0)
      {
         double histogram = macdMain[0] - macdSignal[0];
         IndicatorRelease(macdHandle);

         if(macdMain[0] > macdSignal[0] && histogram > 0) return "BUY";
         if(macdMain[0] < macdSignal[0] && histogram < 0) return "SELL";
      }
      else
         IndicatorRelease(macdHandle);
   }

   //--- Step 3: EMA(20) vs EMA(50) trend fallback
   int emaFastHandle = iMA(symbol, PERIOD_M15, 20, 0, MODE_EMA, PRICE_CLOSE);
   int emaSlowHandle = iMA(symbol, PERIOD_M15, 50, 0, MODE_EMA, PRICE_CLOSE);

   if(emaFastHandle != INVALID_HANDLE && emaSlowHandle != INVALID_HANDLE)
   {
      double emaFast[], emaSlow[];
      ArraySetAsSeries(emaFast, true);
      ArraySetAsSeries(emaSlow, true);

      if(CopyBuffer(emaFastHandle, 0, 0, 2, emaFast) > 0 &&
         CopyBuffer(emaSlowHandle, 0, 0, 2, emaSlow) > 0)
      {
         IndicatorRelease(emaFastHandle);
         IndicatorRelease(emaSlowHandle);

         if(emaFast[0] > emaSlow[0]) return "BUY";
         if(emaFast[0] < emaSlow[0]) return "SELL";
      }
      else
      {
         IndicatorRelease(emaFastHandle);
         IndicatorRelease(emaSlowHandle);
      }
   }

   return "NONE";
}

//+------------------------------------------------------------------+
//| GET RSI value                                                     |
//+------------------------------------------------------------------+
double GetRSI(string symbol, int period)
{
   double rsiBuffer[];
   ArraySetAsSeries(rsiBuffer, true);

   int handle = iRSI(symbol, PERIOD_M15, period, PRICE_CLOSE);
   if(handle == INVALID_HANDLE)
      return -1;

   if(CopyBuffer(handle, 0, 0, 2, rsiBuffer) < 1)
   {
      IndicatorRelease(handle);
      return -1;
   }

   double val = rsiBuffer[0];
   IndicatorRelease(handle);
   return val;
}

//+------------------------------------------------------------------+
//| CHECK GRID STEPS                                                  |
//| CRITICAL: Independent from 20 base position limit                |
//| Trigger: pair net floating P/L <= -$15                            |
//| Direction: follows existing position direction                    |
//| Cooldown: per-pair timer prevents rapid-fire grid entries         |
//+------------------------------------------------------------------+
void CheckGridSteps()
{
   for(int p = 0; p < g_pairCount; p++)
   {
      string symbol = g_pairs[p];

      // Need at least 1 position on this pair to consider grid
      if(CountPairPositions(symbol) == 0)
         continue;

      // Per-pair cooldown between grid steps
      if(TimeCurrent() - g_lastGridTime[p] < GridCooldownSec)
         continue;

      // CRITICAL FIX: Check PAIR NET floating P/L (not just last position)
      double pairNetPL = GetPairFloatingPL(symbol);

      if(pairNetPL <= -GridStepLossUSD)
      {
         // Grid follows the direction of existing positions on this pair
         long lastType = GetLastPositionType(symbol);
         string direction = (lastType == POSITION_TYPE_BUY) ? "BUY" : "SELL";

         if(direction == "")
            continue;

         if(IsSpreadSafe(symbol))
         {
            if(ExecuteTrade(symbol, direction, GridLotSize, MagicGrid, GridComment))
            {
               Print("GRID STEP: ", symbol, " ", direction,
                     " | Pair Net P/L=$", DoubleToString(pairNetPL, 2));
               g_lastGridTime[p] = TimeCurrent();   // Update per-pair cooldown
               Sleep(ExecutionDelayMs);
            }
         }
      }
   }
}

//+------------------------------------------------------------------+
//| GET LAST POSITION TYPE for a symbol                               |
//+------------------------------------------------------------------+
long GetLastPositionType(string symbol)
{
   datetime lastTime = 0;
   long lastType = -1;

   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket > 0)
      {
         if(PositionGetString(POSITION_SYMBOL) == symbol)
         {
            datetime openTime = (datetime)PositionGetInteger(POSITION_TIME);
            if(openTime > lastTime)
            {
               lastTime = openTime;
               lastType = PositionGetInteger(POSITION_TYPE);
            }
         }
      }
   }

   return lastType;
}

//+------------------------------------------------------------------+
//| CHECK SPREAD safety (max 3 pips = 30 points)                     |
//+------------------------------------------------------------------+
bool IsSpreadSafe(string symbol)
{
   long spreadPoints = SymbolInfoInteger(symbol, SYMBOL_SPREAD);
   // 3 pips = 30 points (works for both 5-digit and 3-digit JPY pairs)
   return (spreadPoints <= 30 && spreadPoints >= 0);
}

//+------------------------------------------------------------------+
//| EXECUTE TRADE                                                     |
//+------------------------------------------------------------------+
bool ExecuteTrade(string symbol, string direction, double lot, int magic, string comment)
{
   MqlTradeRequest request = {};
   MqlTradeResult  result  = {};

   request.action       = TRADE_ACTION_DEAL;
   request.symbol       = symbol;
   request.volume       = lot;
   request.deviation    = 20;
   request.magic        = magic;
   request.comment      = comment;
   request.type_time    = ORDER_TIME_GTC;
   request.type_filling = ORDER_FILLING_FOK;

   if(direction == "BUY")
   {
      request.type  = ORDER_TYPE_BUY;
      request.price = SymbolInfoDouble(symbol, SYMBOL_ASK);
   }
   else
   {
      request.type  = ORDER_TYPE_SELL;
      request.price = SymbolInfoDouble(symbol, SYMBOL_BID);
   }

   //--- Validate and normalize lot size
   double minLot  = SymbolInfoDouble(symbol, SYMBOL_VOLUME_MIN);
   double maxLot  = SymbolInfoDouble(symbol, SYMBOL_VOLUME_MAX);
   double lotStep = SymbolInfoDouble(symbol, SYMBOL_VOLUME_STEP);

   if(lot < minLot) request.volume = minLot;
   if(lot > maxLot) request.volume = maxLot;

   request.volume = MathFloor(request.volume / lotStep) * lotStep;

   if(!OrderSend(request, result))
   {
      Print("TRADE FAILED: ", symbol, " ", direction, " lot=", lot,
            " err=", result.retcode, " ", result.comment);
      return false;
   }

   if(result.retcode == TRADE_RETCODE_DONE)
   {
      Print("TRADE OK: ", symbol, " ", direction, " lot=", lot,
            " order=", result.order, " @ ", result.price);
      return true;
   }

   Print("TRADE ERROR: ", symbol, " retcode=", result.retcode);
   return false;
}

//+------------------------------------------------------------------+
//| OnTrade - log position changes for monitoring                     |
//+------------------------------------------------------------------+
void OnTrade()
{
   static int lastPositions = 0;
   int currentPositions = PositionsTotal();

   if(currentPositions != lastPositions)
   {
      double totalPL = GetTotalFloatingPL();
      int baseCount = CountBasePositions();
      int gridCount = currentPositions - baseCount;

      Print("POSITIONS: ", lastPositions, " -> ", currentPositions,
            " (Base:", baseCount, " Grid:", gridCount,
            ") | Total P/L: $", DoubleToString(totalPL, 2),
            " | Frozen: ", g_freezeActive);
      lastPositions = currentPositions;
   }
}
//+------------------------------------------------------------------+
