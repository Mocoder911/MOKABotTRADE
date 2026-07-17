"use client";

import React, { useEffect, useState } from "react";
import { useAuth } from "@/contexts/AuthContext";

// ─── Types ────────────────────────────────────────────────────────────────────
interface BalanceData {
  balance: number;
  equity: number;
}

// ─── Profit Calculator Component ──────────────────────────────────────────────
export default function ProfitCalculator() {
  const { user } = useAuth();
  const [capital, setCapital] = useState<number>(0);
  const [lotSize, setLotSize] = useState<number>(0.02);
  const [balanceData, setBalanceData] = useState<BalanceData | null>(null);
  const [loading, setLoading] = useState(true);

  // Fetch real-time balance from account_balance
  useEffect(() => {
    const fetchBalance = async () => {
      if (!user) return;
      try {
        const res = await fetch("/api/account/metrics", {
          headers: { "x-user-id": user.id },
        });
        if (res.ok) {
          const json = await res.json();
          const balance = json.balance ?? 0;
          const equity = json.equity ?? 0;
          setBalanceData({ balance, equity });
          setCapital(balance); // Use balance as capital
        }
      } catch (err) {
        console.error("Failed to fetch balance:", err);
      } finally {
        setLoading(false);
      }
    };

    fetchBalance();
    const interval = setInterval(fetchBalance, 10000); // Refresh every 10s
    return () => clearInterval(interval);
  }, [user]);

  // ─── Calculations ───────────────────────────────────────────────────────────
  const maxLotAllowed = capital > 0 ? (capital / 500) * 0.02 : 0;
  const profitPerDeal = lotSize * 500;
  const cycleGross = profitPerDeal * 20;
  const shareA = cycleGross * 0.5;
  const shareB = cycleGross * 0.5;
  const returnOnCapital = capital > 0 ? (cycleGross / capital) * 100 : 0;
  const checkStatus = lotSize <= maxLotAllowed ? "OK" : "EXCEEDED";

  // ─── Helper Functions ───────────────────────────────────────────────────────
  const formatUSD = (value: number) => {
    return value.toLocaleString("en-US", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    });
  };

  const formatPercent = (value: number) => {
    return `${value.toFixed(2)}%`;
  };

  const formatLot = (value: number) => {
    return value.toFixed(4);
  };

  // ─── Loading State ──────────────────────────────────────────────────────────
  if (loading) {
    return (
      <div className="flex flex-col gap-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-white glow-white">
              Profit Calculator
            </h1>
            <p className="text-sm text-gray-500 mt-1.5">
              Real-time profit simulation based on current balance
            </p>
          </div>
        </div>
        <div className="flex items-center justify-center py-20">
          <div className="flex flex-col items-center gap-3">
            <div className="w-7 h-7 border-2 border-gray-700 border-t-cyan-500 rounded-full animate-spin"></div>
            <span className="text-sm text-gray-500">Loading balance data...</span>
          </div>
        </div>
      </div>
    );
  }

  // ─── Main Render ────────────────────────────────────────────────────────────
  return (
    <div className="flex flex-col gap-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white glow-white">
            Profit Calculator
          </h1>
          <p className="text-sm text-gray-500 mt-1.5">
            Real-time profit simulation based on current balance
          </p>
        </div>
        <div className="flex items-center gap-3 px-4 py-2 rounded-xl border border-gray-800/50 bg-gray-900/30">
          <span className="text-[10px] uppercase tracking-[0.15em] text-gray-500 font-medium">
            Live Balance
          </span>
          <span className="text-lg font-bold font-mono text-cyan-400 glow-cyan">
            ${formatUSD(capital)}
          </span>
        </div>
      </div>

      {/* Input Section */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Capital Input */}
        <div className="flex flex-col gap-3 p-6 rounded-2xl border border-gray-800/50 bg-gray-950/40">
          <label className="text-[10px] uppercase tracking-[0.2em] text-gray-500 font-medium">
            Capital (USD)
          </label>
          <input
            type="number"
            value={capital}
            onChange={(e) => setCapital(Number(e.target.value) || 0)}
            className="w-full px-4 py-3 rounded-xl bg-gray-900/50 border border-gray-800/50 text-white font-mono text-lg focus:outline-none focus:border-cyan-500/50 transition-colors"
            placeholder="Enter capital amount"
            step="0.01"
            min="0"
          />
          <span className="text-xs text-gray-600">
            Current balance: ${formatUSD(balanceData?.balance ?? 0)}
          </span>
        </div>

        {/* Lot Size Input */}
        <div className="flex flex-col gap-3 p-6 rounded-2xl border border-gray-800/50 bg-gray-950/40">
          <label className="text-[10px] uppercase tracking-[0.2em] text-gray-500 font-medium">
            Lot Size Chosen
          </label>
          <input
            type="number"
            value={lotSize}
            onChange={(e) => setLotSize(Number(e.target.value) || 0)}
            className="w-full px-4 py-3 rounded-xl bg-gray-900/50 border border-gray-800/50 text-white font-mono text-lg focus:outline-none focus:border-cyan-500/50 transition-colors"
            placeholder="Enter lot size"
            step="0.01"
            min="0"
          />
          <span className="text-xs text-gray-600">
            Recommended: {formatLot(maxLotAllowed)} lots max
          </span>
        </div>
      </div>

      {/* Results Table */}
      <div className="overflow-hidden rounded-2xl border border-gray-800/50 bg-gray-950/40">
        <table className="w-full">
          <thead>
            <tr className="bg-gray-900/50 border-b border-gray-800/50">
              <th colSpan={3} className="px-6 py-4 text-left">
                <span className="text-[10px] uppercase tracking-[0.2em] text-cyan-400 font-bold">
                  RATE
                </span>
              </th>
            </tr>
          </thead>
          <tbody>
            <tr className="border-b border-gray-800/30 hover:bg-gray-900/30 transition-colors">
              <td className="px-6 py-4 text-sm text-gray-400">Maximum lot allowed</td>
              <td className="px-6 py-4 text-sm font-mono text-white text-right">
                {formatLot(maxLotAllowed)}
              </td>
              <td className="px-6 py-4 text-xs text-gray-600 text-right">lots</td>
            </tr>
            <tr className="border-b border-gray-800/30 hover:bg-gray-900/30 transition-colors">
              <td className="px-6 py-4 text-sm text-gray-400">Profit per deal</td>
              <td className="px-6 py-4 text-sm font-mono text-emerald-400 glow-green text-right">
                ${formatUSD(profitPerDeal)}
              </td>
              <td className="px-6 py-4 text-xs text-gray-600 text-right">USD</td>
            </tr>
          </tbody>
          <thead>
            <tr className="bg-gray-900/50 border-b border-gray-800/50">
              <th colSpan={3} className="px-6 py-4 text-left">
                <span className="text-[10px] uppercase tracking-[0.2em] text-violet-400 font-bold">
                  INPUT
                </span>
              </th>
            </tr>
          </thead>
          <tbody>
            <tr className="border-b border-gray-800/30 hover:bg-gray-900/30 transition-colors">
              <td className="px-6 py-4 text-sm text-gray-400">Cycle gross (20 deals)</td>
              <td className="px-6 py-4 text-sm font-mono text-white text-right">
                {formatUSD(cycleGross)}
              </td>
              <td className="px-6 py-4 text-xs text-gray-600 text-right">USD</td>
            </tr>
          </tbody>
          <thead>
            <tr className="bg-gray-900/50 border-b border-gray-800/50">
              <th colSpan={3} className="px-6 py-4 text-left">
                <span className="text-[10px] uppercase tracking-[0.2em] text-emerald-400 font-bold">
                  OUTPUT
                </span>
              </th>
            </tr>
          </thead>
          <tbody>
            <tr className="border-b border-gray-800/30 hover:bg-gray-900/30 transition-colors">
              <td className="px-6 py-4 text-sm text-gray-400">Share A (50%)</td>
              <td className="px-6 py-4 text-sm font-mono text-emerald-400 glow-green text-right">
                ${formatUSD(shareA)}
              </td>
              <td className="px-6 py-4 text-xs text-gray-600 text-right">USD</td>
            </tr>
            <tr className="border-b border-gray-800/30 hover:bg-gray-900/30 transition-colors">
              <td className="px-6 py-4 text-sm text-gray-400">Share B (50%)</td>
              <td className="px-6 py-4 text-sm font-mono text-emerald-400 glow-green text-right">
                ${formatUSD(shareB)}
              </td>
              <td className="px-6 py-4 text-xs text-gray-600 text-right">USD</td>
            </tr>
            <tr className="border-b border-gray-800/30 hover:bg-gray-900/30 transition-colors">
              <td className="px-6 py-4 text-sm text-gray-400">Return on capital</td>
              <td className="px-6 py-4 text-sm font-mono text-cyan-400 glow-cyan text-right">
                {formatPercent(returnOnCapital)}
              </td>
              <td className="px-6 py-4 text-xs text-gray-600 text-right">ROI</td>
            </tr>
            <tr className="hover:bg-gray-900/30 transition-colors">
              <td className="px-6 py-4 text-sm text-gray-400">Check logic</td>
              <td className="px-6 py-4 text-sm font-mono text-right">
                <span
                  className={`px-3 py-1 rounded-lg text-xs font-bold ${
                    checkStatus === "OK"
                      ? "bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 glow-green"
                      : "bg-rose-500/15 text-rose-400 border border-rose-500/30 glow-rose"
                  }`}
                >
                  {checkStatus}
                </span>
              </td>
              <td className="px-6 py-4 text-xs text-gray-600 text-right">
                {checkStatus === "OK" ? "Safe" : "Risk"}
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      {/* Footer Info */}
      <div className="flex items-center justify-between text-xs text-gray-600 px-1 pb-4">
        <span>
          Lot size: <span className="font-mono text-gray-400">{formatLot(lotSize)}</span>
          {" / "}
          Max: <span className="font-mono text-gray-400">{formatLot(maxLotAllowed)}</span>
        </span>
        <span className="font-mono">
          Auto-refresh: 10s
        </span>
      </div>
    </div>
  );
}
