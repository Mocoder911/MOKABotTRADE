"use client";

import React, { useEffect, useState } from "react";

// ─── Types ────────────────────────────────────────────────────────────────────
interface Trade {
  ticket: string;
  symbol: string;
  type: "BUY" | "SELL";
  volume: number;
  entry: number;
  sl: number;
  tp: number;
  livePL: number;
  openTime: string;
}

// ─── Helpers ──────────────────────────────────────────────────────────────────
function plColor(value: number): string {
  if (value > 0) return "text-green-500";
  if (value < 0) return "text-red-500";
  return "text-gray-400";
}

function formatPL(value: number): string {
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(2)}`;
}

function typeBadge(type: "BUY" | "SELL") {
  return type === "BUY"
    ? "bg-green-500/20 text-green-400 border border-green-500/40"
    : "bg-red-500/20 text-red-400 border border-red-500/40";
}

// ─── Table Components ─────────────────────────────────────────────────────────
function Th({ children }: { children: React.ReactNode }) {
  return (
    <th className="px-4 py-3 text-left text-[11px] font-semibold uppercase tracking-wider text-gray-400 border-b border-gray-800">
      {children}
    </th>
  );
}

function Td({
  children,
  className = "",
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <td className={`px-4 py-3 text-sm font-mono border-b border-gray-800/60 ${className}`}>
      {children}
    </td>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────
export default function DashboardPage() {
  const [trades, setTrades] = useState<Trade[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function fetchTrades() {
    try {
      const res = await fetch("/api/trades/active");
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const json = await res.json();
      setTrades(json.trades);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch trades");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchTrades();
  }, []);

  return (
    <div className="max-w-7xl mx-auto flex flex-col gap-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Active Trades</h1>
          <p className="text-sm text-gray-500 mt-1">
            Real-time positions from Exness MT5 • Account{" "}
            <span className="text-gray-400 font-mono">260904217</span>
          </p>
        </div>
        <div className="flex items-center gap-3">
          {/* Refresh button */}
          <button
            onClick={fetchTrades}
            disabled={loading}
            className="text-xs text-gray-400 hover:text-white border border-gray-700 hover:border-gray-500 rounded-lg px-3 py-1.5 transition-colors disabled:opacity-50"
          >
            {loading ? "Loading..." : "Refresh"}
          </button>
          <div className="flex items-center gap-2 bg-gray-900 border border-gray-700 rounded-lg px-3 py-1.5">
            <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></span>
            <span className="text-xs text-gray-400 font-mono">
              {trades.length} open position{trades.length !== 1 ? "s" : ""}
            </span>
          </div>
        </div>
      </div>

      {/* Error State */}
      {error && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-xl px-4 py-3 text-red-400 text-sm">
          <span className="font-bold">Connection error:</span> {error}
          <span className="text-red-400/60 ml-2">
            — Make sure your Supabase credentials are set in .env.local
          </span>
        </div>
      )}

      {/* Trades Table */}
      <div className="overflow-x-auto rounded-xl border border-gray-800 bg-gray-950/50">
        <table className="w-full min-w-[900px]">
          <thead>
            <tr className="bg-gray-900/80">
              <Th>Ticket</Th>
              <Th>Symbol</Th>
              <Th>Type</Th>
              <Th>Volume</Th>
              <Th>Entry</Th>
              <Th>SL</Th>
              <Th>TP</Th>
              <Th>Live P/L</Th>
              <Th>Open Time</Th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={9} className="text-center py-16 text-gray-600">
                  <div className="flex flex-col items-center gap-3">
                    <div className="w-6 h-6 border-2 border-gray-600 border-t-green-500 rounded-full animate-spin"></div>
                    <span className="text-sm">Fetching active trades...</span>
                  </div>
                </td>
              </tr>
            ) : trades.length === 0 ? (
              <tr>
                <td colSpan={9} className="text-center py-16 text-gray-600">
                  <div className="flex flex-col items-center gap-2">
                    <span className="text-4xl">📊</span>
                    <span className="text-sm">No active trades</span>
                  </div>
                </td>
              </tr>
            ) : (
              trades.map((trade) => (
                <tr
                  key={trade.ticket}
                  className="hover:bg-gray-900/40 transition-colors duration-150"
                >
                  <Td className="text-gray-300">{trade.ticket}</Td>
                  <Td className="text-white font-semibold">{trade.symbol}</Td>
                  <Td>
                    <span
                      className={`inline-block px-2 py-0.5 rounded text-xs font-bold ${typeBadge(trade.type)}`}
                    >
                      {trade.type}
                    </span>
                  </Td>
                  <Td className="text-gray-300">{trade.volume.toFixed(2)}</Td>
                  <Td className="text-gray-300">{trade.entry}</Td>
                  <Td className="text-red-400">{trade.sl}</Td>
                  <Td className="text-green-400">{trade.tp}</Td>
                  <Td className={`font-bold ${plColor(trade.livePL)}`}>
                    {formatPL(trade.livePL)}
                  </Td>
                  <Td className="text-gray-500 text-xs">{trade.openTime}</Td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Summary Footer */}
      <div className="flex items-center justify-between text-xs text-gray-600 px-1">
        <span>
          Total P/L:{" "}
          <span
            className={`font-bold ${plColor(trades.reduce((sum, t) => sum + t.livePL, 0))}`}
          >
            {formatPL(trades.reduce((sum, t) => sum + t.livePL, 0))}
          </span>
        </span>
        <span className="font-mono">
          Last sync: {loading ? "..." : new Date().toLocaleTimeString()}
        </span>
      </div>
    </div>
  );
}
