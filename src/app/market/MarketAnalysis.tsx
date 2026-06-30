"use client";

import React, { useEffect, useRef, useState } from "react";

// ─── Market Analysis Component - Full TradingView Workstation ─────────────────
export default function MarketAnalysis() {
  const containerRef = useRef<HTMLDivElement>(null);
  const [widgetLoaded, setWidgetLoaded] = useState(false);

  // Load TradingView Advanced Widget with full workstation layout
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
      symbol: "OANDA:XAUUSD",
      interval: "1D",
      timezone: "Etc/UTC",
      theme: "dark",
      style: "1",
      locale: "en",
      allow_symbol_change: true,
      calendar: true,
      support_host: "https://www.tradingview.com",
      hide_volume: false,
      toolbar_bg: "#0a0a0a",
      enable_publishing: false,
      withdateranges: true,
      hide_side_toolbar: false,
      details: true,
      hotlist: true,
      studies: ["Volume@tv-basicstudies", "MAExp@tv-basicstudies"],
      show_popup_button: true,
      popup_width: "1000",
      popup_height: "650",
    });

    containerRef.current.appendChild(script);

    // Mark as loaded after widget initializes
    const timer = setTimeout(() => setWidgetLoaded(true), 2000);
    return () => clearTimeout(timer);
  }, []);

  return (
    <div className="w-full flex flex-col" style={{ height: "calc(100vh - 120px)" }}>
      {/* ─── Chart Container - Full Workstation ───────────────────────────── */}
      <div className="relative flex-1 rounded-2xl border border-gray-800/50 bg-gray-950/40 overflow-hidden">
        {/* Loading indicator */}
        {!widgetLoaded && (
          <div className="absolute inset-0 flex items-center justify-center bg-gray-950/90 z-10">
            <div className="flex flex-col items-center gap-4">
              <div className="w-10 h-10 border-2 border-gray-700 border-t-violet-500 rounded-full animate-spin"></div>
              <span className="text-sm text-gray-400 font-medium">Loading TradingView Workstation...</span>
              <span className="text-xs text-gray-600">Chart + Watchlist + News</span>
            </div>
          </div>
        )}

        {/* TradingView Widget - Full Workstation */}
        <div
          ref={containerRef}
          className="w-full h-full"
        />
      </div>

      {/* ─── Footer Bar ───────────────────────────────────────────────────── */}
      <div className="flex items-center justify-between text-xs text-gray-600 px-2 py-2">
        <span className="text-gray-500">
          <span className="text-violet-400/60">●</span> Full workstation with watchlist, charts & news
        </span>
        <span className="font-mono text-gray-500">
          Default: <span className="text-violet-400/80">OANDA:XAUUSD</span>
        </span>
      </div>
    </div>
  );
}
