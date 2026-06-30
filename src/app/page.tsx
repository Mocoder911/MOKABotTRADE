"use client";

import React, { useEffect, useState, useCallback } from "react";
import TacticsStudio from "./tactics/TacticsStudio";
import MarketAnalysis from "./market/MarketAnalysis";
import UserManagement from "./admin/UserManagement";
import { useAuth } from "@/contexts/AuthContext";

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

type TabId = "dashboard" | "tactics" | "market" | "admin";

// ─── Helpers ──────────────────────────────────────────────────────────────────
function plColor(value: number): string {
  if (value > 0) return "text-emerald-400 glow-green";
  if (value < 0) return "text-rose-400 glow-rose";
  return "text-gray-500";
}

function formatPL(value: number): string {
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(2)}`;
}

function formatUSD(value: number): string {
  return value.toLocaleString("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

function typeBadge(type: "BUY" | "SELL") {
  return type === "BUY"
    ? "bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 glow-green"
    : "bg-rose-500/15 text-rose-400 border border-rose-500/30 glow-rose";
}

function exportCSV(trades: Trade[]) {
  const headers = ["Ticket", "Symbol", "Type", "Volume", "Entry", "SL", "TP", "Live P/L", "Open Time"];
  const rows = trades.map((t) => [
    t.ticket, t.symbol, t.type, t.volume, t.entry, t.sl, t.tp, t.livePL, t.openTime,
  ]);
  const csv = [headers, ...rows].map((r) => r.join(",")).join("\n");
  const blob = new Blob([csv], { type: "text/csv" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `active-trades-${Date.now()}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}

// ─── Stat Card ────────────────────────────────────────────────────────────────
function StatCard({
  label,
  value,
  accent = "cyan",
}: {
  label: string;
  value: string;
  accent?: "cyan" | "green" | "rose" | "white";
}) {
  const glowMap = {
    cyan: "glow-cyan text-cyan-400",
    green: "glow-green text-emerald-400",
    rose: "glow-rose text-rose-400",
    white: "glow-white text-white",
  };
  const boxMap = {
    cyan: "glow-box-green border-emerald-500/20",
    green: "glow-box-green border-emerald-500/20",
    rose: "glow-box-rose border-rose-500/20",
    white: "border-gray-800/50",
  };
  return (
    <div
      className={`flex flex-col items-center justify-center py-5 px-4 rounded-2xl bg-gray-900/30 border ${boxMap[accent]} transition-all duration-300`}
    >
      <span className="text-[10px] uppercase tracking-[0.2em] text-gray-500 font-medium mb-2">
        {label}
      </span>
      <span className={`text-xl font-bold font-mono ${glowMap[accent]}`}>
        {value}
      </span>
    </div>
  );
}

// ─── Table Components ─────────────────────────────────────────────────────────
function Th({ children }: { children: React.ReactNode }) {
  return (
    <th className="px-5 py-4 text-left text-[10px] font-semibold uppercase tracking-[0.15em] text-gray-500 border-b border-gray-800/50">
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
    <td
      className={`px-5 py-4 text-sm font-mono border-b border-gray-800/30 ${className}`}
    >
      {children}
    </td>
  );
}

// ─── Tab Button ───────────────────────────────────────────────────────────────
function TabButton({
  active,
  onClick,
  children,
  glowClass,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
  glowClass: string;
}) {
  return (
    <button
      onClick={onClick}
      className={`px-6 py-3 text-sm font-bold tracking-wide rounded-xl border transition-all duration-200
        ${
          active
            ? `${glowClass} border-transparent bg-gray-900/50`
            : "text-gray-500 border-gray-800/50 bg-transparent hover:text-gray-300 hover:border-gray-700"
        }`}
    >
      {children}
    </button>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────
export default function HomePage() {
  const { profile, loading: authLoading } = useAuth();
  const [activeTab, setActiveTab] = useState<TabId>("dashboard");
  const [trades, setTrades] = useState<Trade[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const isAdmin = profile?.role === "admin";
  const isActive = profile?.status === "active";

  // Show pending/suspended message
  if (!authLoading && profile && !isActive) {
    return (
      <div className="min-h-[60vh] flex items-center justify-center">
        <div className="text-center max-w-md">
          <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-amber-500/10 border border-amber-500/30 flex items-center justify-center">
            <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-amber-400">
              <circle cx="12" cy="12" r="10"></circle>
              <line x1="12" y1="8" x2="12" y2="12"></line>
              <line x1="12" y1="16" x2="12.01" y2="16"></line>
            </svg>
          </div>
          <h2 className="text-xl font-bold text-white glow-white mb-2">
            Account {profile.status === "pending" ? "Pending Approval" : "Suspended"}
          </h2>
          <p className="text-sm text-gray-400">
            {profile.status === "pending"
              ? "Your account is pending admin approval. You will be notified once activated."
              : "Your account has been suspended. Please contact an administrator."}
          </p>
        </div>
      </div>
    );
  }

  // Show loading while auth is initializing
  if (authLoading) {
    return (
      <div className="min-h-[60vh] flex items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-2 border-gray-700 border-t-cyan-500 rounded-full animate-spin"></div>
          <span className="text-sm text-gray-500">Loading dashboard...</span>
        </div>
      </div>
    );
  }

  const fetchTrades = useCallback(async () => {
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
  }, []);

  useEffect(() => {
    fetchTrades();
  }, [fetchTrades]);

  // ─── Computed stats ───────────────────────────────────────────────────────
  const totalTrades = trades.length;
  const wins = trades.filter((t) => t.livePL > 0).length;
  const losses = trades.filter((t) => t.livePL < 0).length;
  const winRate = totalTrades > 0 ? ((wins / totalTrades) * 100).toFixed(1) : "0.0";
  const totalPL = trades.reduce((sum, t) => sum + t.livePL, 0);

  return (
    <div className={`${activeTab === "market" ? "w-full px-4" : "max-w-[1400px] mx-auto"} flex flex-col ${activeTab === "market" ? "gap-4" : "gap-8"}`}>
      {/* ─── Tab Navigation ───────────────────────────────────────────────── */}
      <div className="flex items-center gap-3 pt-2">
        <TabButton
          active={activeTab === "dashboard"}
          onClick={() => setActiveTab("dashboard")}
          glowClass="text-cyan-400 glow-cyan"
        >
          Trading Journal
        </TabButton>
        {/* Tactics Studio - Admin only */}
        {isAdmin && (
          <TabButton
            active={activeTab === "tactics"}
            onClick={() => setActiveTab("tactics")}
            glowClass="text-emerald-400 glow-green"
          >
            Tactics Studio
          </TabButton>
        )}
        <TabButton
          active={activeTab === "market"}
          onClick={() => setActiveTab("market")}
          glowClass="text-violet-400 glow-violet"
        >
          Live
        </TabButton>
        {/* User Management - Admin only */}
        {isAdmin && (
          <TabButton
            active={activeTab === "admin"}
            onClick={() => setActiveTab("admin")}
            glowClass="text-amber-400"
          >
            User Management
          </TabButton>
        )}
      </div>

      {/* ─── Tab Content ──────────────────────────────────────────────────── */}
      {activeTab === "dashboard" ? (
        <div className="flex flex-col gap-8">
          {/* Page Header */}
          <div className="flex items-end justify-between">
            <div>
              <h1 className="text-2xl font-bold text-white glow-white">
                Active Trades
              </h1>
              <p className="text-sm text-gray-500 mt-1.5">
                Real-time positions from Exness MT5 &bull; Account{" "}
                <span className="text-gray-400 font-mono">260904217</span>
              </p>
            </div>
            <div className="flex items-center gap-3">
              <button
                onClick={() => exportCSV(trades)}
                disabled={trades.length === 0}
                className="flex items-center gap-2 text-xs font-medium text-gray-400 hover:text-emerald-400 border border-gray-700 hover:border-emerald-500/40 rounded-xl px-4 py-2 transition-all duration-200 disabled:opacity-30 bg-gray-900/30"
              >
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  width="14"
                  height="14"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                  <polyline points="7 10 12 15 17 10" />
                  <line x1="12" y1="15" x2="12" y2="3" />
                </svg>
                Export CSV
              </button>
              <button
                onClick={fetchTrades}
                disabled={loading}
                className="text-xs font-medium text-gray-400 hover:text-white border border-gray-700 hover:border-gray-500 rounded-xl px-4 py-2 transition-all duration-200 disabled:opacity-30 bg-gray-900/30"
              >
                {loading ? "Loading..." : "Refresh"}
              </button>
            </div>
          </div>

          {/* 5 Statistics Cards */}
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
            <StatCard label="Total Trades" value={String(totalTrades)} accent="cyan" />
            <StatCard label="Wins" value={String(wins)} accent="green" />
            <StatCard label="Losses" value={String(losses)} accent="rose" />
            <StatCard label="Win Rate" value={`${winRate}%`} accent="cyan" />
            <StatCard
              label="Total P/L"
              value={`$${formatUSD(totalPL)}`}
              accent={totalPL >= 0 ? "green" : "rose"}
            />
          </div>

          {/* Error State */}
          {error && (
            <div className="bg-rose-500/10 border border-rose-500/20 rounded-2xl px-5 py-4 text-rose-400 text-sm">
              <span className="font-bold">Connection error:</span> {error}
              <span className="text-rose-400/50 ml-2">
                — Check your .env.local Supabase credentials
              </span>
            </div>
          )}

          {/* Trades Data Grid */}
          <div className="overflow-x-auto rounded-2xl border border-gray-800/50 bg-gray-950/40">
            <table className="w-full min-w-[960px]">
              <thead>
                <tr className="bg-gray-900/50">
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
                    <td colSpan={9} className="text-center py-20 text-gray-600">
                      <div className="flex flex-col items-center gap-3">
                        <div className="w-7 h-7 border-2 border-gray-700 border-t-emerald-500 rounded-full animate-spin"></div>
                        <span className="text-sm text-gray-500">
                          Fetching active trades...
                        </span>
                      </div>
                    </td>
                  </tr>
                ) : trades.length === 0 ? (
                  <tr>
                    <td colSpan={9} className="text-center py-20 text-gray-600">
                      <div className="flex flex-col items-center gap-3">
                        <span className="text-5xl opacity-40">📊</span>
                        <span className="text-sm text-gray-500">
                          No active trades
                        </span>
                      </div>
                    </td>
                  </tr>
                ) : (
                  trades.map((trade) => (
                    <tr
                      key={trade.ticket}
                      className="hover:bg-gray-900/30 transition-colors duration-150"
                    >
                      <Td className="text-gray-400">{trade.ticket}</Td>
                      <Td className="text-white font-semibold">{trade.symbol}</Td>
                      <Td>
                        <span
                          className={`inline-block px-2.5 py-1 rounded-lg text-[11px] font-bold ${typeBadge(trade.type)}`}
                        >
                          {trade.type}
                        </span>
                      </Td>
                      <Td className="text-gray-400">{trade.volume.toFixed(2)}</Td>
                      <Td className="text-gray-300">{trade.entry}</Td>
                      <Td className="text-rose-400/80">{trade.sl}</Td>
                      <Td className="text-emerald-400/80">{trade.tp}</Td>
                      <Td className={`font-bold ${plColor(trade.livePL)}`}>
                        {formatPL(trade.livePL)}
                      </Td>
                      <Td className="text-gray-600 text-xs">{trade.openTime}</Td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          {/* Footer Summary */}
          <div className="flex items-center justify-between text-xs text-gray-600 px-1 pb-4">
            <span>
              Net P/L:{" "}
              <span className={`font-bold ${plColor(totalPL)}`}>
                ${formatUSD(totalPL)}
              </span>
            </span>
            <span className="font-mono">
              Last sync: {loading ? "..." : new Date().toLocaleTimeString()}
            </span>
          </div>
        </div>
      ) : activeTab === "tactics" ? (
        <TacticsStudio />
      ) : activeTab === "admin" ? (
        <UserManagement />
      ) : (
        <MarketAnalysis />
      )}
    </div>
  );
}
