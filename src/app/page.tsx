import React from "react";

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

// ─── Mock data (will be replaced by Supabase real-time fetch) ─────────────────
const MOCK_TRADES: Trade[] = [
  {
    ticket: "#102847",
    symbol: "EURUSD",
    type: "BUY",
    volume: 0.5,
    entry: 1.08432,
    sl: 1.081,
    tp: 1.09,
    livePL: 124.5,
    openTime: "2026-06-30 08:14:22",
  },
  {
    ticket: "#102848",
    symbol: "XAUUSD",
    type: "SELL",
    volume: 0.1,
    entry: 2345.6,
    sl: 2360.0,
    tp: 2310.0,
    livePL: -87.3,
    openTime: "2026-06-30 09:02:11",
  },
  {
    ticket: "#102849",
    symbol: "GBPJPY",
    type: "BUY",
    volume: 0.3,
    entry: 193.452,
    sl: 193.1,
    tp: 194.2,
    livePL: 56.8,
    openTime: "2026-06-30 09:45:03",
  },
];

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

// ─── Table Column Header ──────────────────────────────────────────────────────
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
  const trades = MOCK_TRADES;

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
        <div className="flex items-center gap-2 bg-gray-900 border border-gray-700 rounded-lg px-3 py-1.5">
          <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></span>
          <span className="text-xs text-gray-400 font-mono">
            {trades.length} open position{trades.length !== 1 ? "s" : ""}
          </span>
        </div>
      </div>

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
            {trades.length === 0 ? (
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
        <span className="font-mono">Last sync: just now</span>
      </div>
    </div>
  );
}
