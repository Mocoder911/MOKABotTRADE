"use client";

import React, { useEffect, useRef, useState } from "react";

// ─── Symbol Options ───────────────────────────────────────────────────────────
const SYMBOL_OPTIONS = [
  { value: "BINANCE:BTCUSDT", label: "BTC/USDT" },
  { value: "BINANCE:ETHUSDT", label: "ETH/USDT" },
  { value: "FX:EURUSD", label: "EUR/USD" },
  { value: "FX:GBPUSD", label: "GBP/USD" },
  { value: "FX:GBPJPY", label: "GBP/JPY" },
  { value: "OANDA:XAUUSD", label: "XAU/USD (Gold)" },
  { value: "OANDA:XAGUSD", label: "XAG/USD (Silver)" },
  { value: "NASDAQ:AAPL", label: "Apple" },
  { value: "NASDAQ:TSLA", label: "Tesla" },
];

// ─── Market Analysis Component ────────────────────────────────────────────────
export default function MarketAnalysis() {
  const containerRef = useRef<HTMLDivElement>(null);
  const [symbol, setSymbol] = useState("BINANCE:BTCUSDT");
  const [widgetLoaded, setWidgetLoaded] = useState(false);

  // Load TradingView widget
  useEffect(() => {
    if (!containerRef.current) return;

    // Clear previous widget
    containerRef.current.innerHTML = "";
    setWidgetLoaded(false);

    const script = document.createElement("script");
    script.src = "https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js";
    script.type = "text/javascript";
    script.async = true;
    script.innerHTML = JSON.stringify({
      autosize: true,
      symbol: symbol,
      interval: "1D",
      timezone: "Etc/UTC",
      theme: "dark",
      style: "1",
      locale: "en",
      allow_symbol_change: true,
      calendar: false,
      support_host: "https://www.tradingview.com",
      hide_volume: false,
      toolbar_bg: "#0a0a0a",
      enable_publishing: false,
      withdateranges: true,
      hide_side_toolbar: false,
      details: true,
      hotlist: true,
      studies: ["Volume@tv-basicstudies"],
    });

    containerRef.current.appendChild(script);
    
    // Mark as loaded after a short delay
    const timer = setTimeout(() => setWidgetLoaded(true), 1500);
    return () => clearTimeout(timer);
  }, [symbol]);

  return (
    <div className="max-w-[1400px] mx-auto flex flex-col gap-6">
      {/* ─── Header ───────────────────────────────────────────────────────── */}
      <div className="flex items-end justify-between pt-2">
        <div>
          <h1 className="text-2xl font-bold text-white glow-white">
            Live Market Analysis
          </h1>
          <p className="text-sm text-gray-500 mt-1.5">
            Real-time charts powered by TradingView
          </p>
        </div>
        {/* Symbol Selector */}
        <div className="flex items-center gap-3">
          <select
            value={symbol}
            onChange={(e) => setSymbol(e.target.value)}
            className="bg-gray-900/60 border border-gray-700/50 rounded-xl px-4 py-2.5 text-sm font-mono text-gray-300 
            focus:border-cyan-500/50 focus:text-cyan-400 focus:glow-cyan outline-none transition-all duration-200
            appearance-none cursor-pointer min-w-[160px]"
            style={{
              backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%236b7280' stroke-width='2'%3E%3Cpolyline points='6 9 12 15 18 9'%3E%3C/polyline%3E%3C/svg%3E")`,
              backgroundRepeat: "no-repeat",
              backgroundPosition: "right 12px center",
              paddingRight: "36px",
            }}
          >
            {SYMBOL_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* ─── Chart Container ──────────────────────────────────────────────── */}
      <div className="relative rounded-2xl border border-gray-800/50 bg-gray-950/40 overflow-hidden"
        style={{ height: "calc(100vh - 280px)", minHeight: "500px" }}
      >
        {/* Loading indicator */}
        {!widgetLoaded && (
          <div className="absolute inset-0 flex items-center justify-center bg-gray-950/80 z-10">
            <div className="flex flex-col items-center gap-3">
              <div className="w-8 h-8 border-2 border-gray-700 border-t-cyan-500 rounded-full animate-spin"></div>
              <span className="text-sm text-gray-500">Loading chart...</span>
            </div>
          </div>
        )}
        
        {/* TradingView Widget */}
        <div
          ref={containerRef}
          className="w-full h-full"
          style={{ minHeight: "500px" }}
        />
      </div>

      {/* ─── Footer ───────────────────────────────────────────────────────── */}
      <div className="flex items-center justify-between text-xs text-gray-600 px-1 pb-4">
        <span className="text-gray-500">
          <span className="text-cyan-400/60">●</span> Live data from TradingView
        </span>
        <span className="font-mono">
          Symbol: <span className="text-cyan-400/80">{symbol}</span>
        </span>
      </div>
    </div>
  );
}
