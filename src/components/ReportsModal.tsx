"use client";

import React, { useState, useEffect } from "react";
import Image from "next/image";
import { useAuth } from "@/contexts/AuthContext";

interface Trade {
  symbol: string;
  live_pl: number;
  close_time: string;
  type: string;
  volume: number;
}

interface ReportData {
  trades: Trade[];
  totalProfit: number;
  tradeCount: number;
  balance: number;
  period: string;
}

interface ReportsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

type Period = "daily" | "weekly" | "monthly" | "all-time";

const PERIOD_LABELS: Record<Period, string> = {
  daily: "Daily",
  weekly: "Weekly",
  monthly: "Monthly",
  "all-time": "All Time",
};

function formatUSD(value: number): string {
  return value.toLocaleString("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

function formatTime(dateStr: string): string {
  const date = new Date(dateStr);
  return date.toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function ReportsModal({ isOpen, onClose }: ReportsModalProps) {
  const { user } = useAuth();
  const [activePeriod, setActivePeriod] = useState<Period>("daily");
  const [reportData, setReportData] = useState<ReportData | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!isOpen || !user) return;

    const fetchReport = async () => {
      setLoading(true);
      try {
        const res = await fetch(`/api/reports?period=${activePeriod}`, {
          headers: { "x-user-id": user.id },
          cache: "no-store",
        });
        if (res.ok) {
          const data = await res.json();
          setReportData(data);
        }
      } catch (err) {
        console.error("Failed to fetch report:", err);
      } finally {
        setLoading(false);
      }
    };

    fetchReport();
  }, [isOpen, activePeriod, user]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/70 backdrop-blur-sm">
      <div className="bg-[#1a1f26] border border-gray-700/60 rounded-2xl shadow-2xl w-full max-w-4xl max-h-[90vh] overflow-hidden">
        {/* Header with Logos */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-700/60 bg-gradient-to-r from-gray-900/50 to-gray-800/50">
          {/* MOKABot Logo */}
          <div className="flex items-center gap-3">
            <Image
              src="/mokabot-logo.png"
              alt="MOKABot"
              width={48}
              height={48}
              className="object-contain drop-shadow-[0_0_8px_rgba(34,211,238,0.5)]"
              priority
            />
            <span className="text-lg font-bold text-cyan-400 tracking-wider">MOKABot</span>
          </div>

          {/* Title */}
          <div className="text-center">
            <h2 className="text-xl font-bold text-white tracking-wide">Trading Report</h2>
            <p className="text-xs text-gray-500 uppercase tracking-wider">Winning Trades Only</p>
          </div>

          {/* MT5 Logo */}
          <div className="flex items-center gap-3">
            <span className="text-lg font-bold text-blue-400 tracking-wider">MetaTrader 5</span>
            <div className="w-12 h-12 rounded-lg bg-gradient-to-br from-blue-500 to-blue-700 flex items-center justify-center shadow-lg">
              <span className="text-white font-bold text-lg">MT5</span>
            </div>
          </div>
        </div>

        {/* Period Tabs */}
        <div className="flex items-center gap-2 px-6 py-3 border-b border-gray-700/40 bg-gray-900/30">
          {(Object.keys(PERIOD_LABELS) as Period[]).map((period) => (
            <button
              key={period}
              onClick={() => setActivePeriod(period)}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 ${
                activePeriod === period
                  ? "bg-cyan-500/20 text-cyan-400 border border-cyan-500/50"
                  : "text-gray-500 hover:text-white hover:bg-gray-800/50"
              }`}
            >
              {PERIOD_LABELS[period]}
            </button>
          ))}
        </div>

        {/* Content */}
        <div className="overflow-y-auto max-h-[60vh] p-6">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <div className="animate-spin rounded-full h-8 w-8 border-2 border-cyan-500 border-t-transparent"></div>
              <span className="ml-3 text-gray-400">Loading report...</span>
            </div>
          ) : reportData ? (
            <>
              {/* Summary Cards */}
              <div className="grid grid-cols-3 gap-4 mb-6">
                <div className="bg-gray-900/50 border border-gray-700/50 rounded-xl p-4 text-center">
                  <p className="text-xs uppercase tracking-wider text-gray-500 mb-1">Winning Trades</p>
                  <p className="text-2xl font-bold text-cyan-400">{reportData.tradeCount}</p>
                </div>
                <div className="bg-gray-900/50 border border-gray-700/50 rounded-xl p-4 text-center">
                  <p className="text-xs uppercase tracking-wider text-gray-500 mb-1">Total Profit</p>
                  <p className="text-2xl font-bold text-emerald-400">
                    +${formatUSD(reportData.totalProfit)}
                  </p>
                </div>
                <div className="bg-gray-900/50 border border-gray-700/50 rounded-xl p-4 text-center">
                  <p className="text-xs uppercase tracking-wider text-gray-500 mb-1">Balance</p>
                  <p className="text-2xl font-bold text-white">${formatUSD(reportData.balance)}</p>
                </div>
              </div>

              {/* Trades Table */}
              {reportData.trades.length > 0 ? (
                <div className="bg-gray-900/30 border border-gray-700/40 rounded-xl overflow-hidden">
                  <table className="w-full">
                    <thead className="bg-gray-800/50">
                      <tr>
                        <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                          Symbol
                        </th>
                        <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                          Type
                        </th>
                        <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                          Volume
                        </th>
                        <th className="px-4 py-3 text-right text-xs font-medium uppercase tracking-wider text-gray-500">
                          Profit
                        </th>
                        <th className="px-4 py-3 text-right text-xs font-medium uppercase tracking-wider text-gray-500">
                          Closed
                        </th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-700/30">
                      {reportData.trades.map((trade, idx) => (
                        <tr key={idx} className="hover:bg-gray-800/30 transition-colors">
                          <td className="px-4 py-3 text-sm font-medium text-white">
                            {trade.symbol}
                          </td>
                          <td className="px-4 py-3 text-sm">
                            <span
                              className={`px-2 py-0.5 rounded text-xs font-medium ${
                                trade.type === "buy"
                                  ? "bg-emerald-500/20 text-emerald-400"
                                  : "bg-rose-500/20 text-rose-400"
                              }`}
                            >
                              {trade.type?.toUpperCase()}
                            </span>
                          </td>
                          <td className="px-4 py-3 text-sm text-gray-400">{trade.volume}</td>
                          <td className="px-4 py-3 text-sm text-right font-mono text-emerald-400">
                            +${formatUSD(trade.live_pl)}
                          </td>
                          <td className="px-4 py-3 text-sm text-right text-gray-500">
                            {formatTime(trade.close_time)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="text-center py-12">
                  <p className="text-gray-500 text-lg">No winning trades found for this period</p>
                </div>
              )}
            </>
          ) : (
            <div className="text-center py-12">
              <p className="text-gray-500 text-lg">Failed to load report</p>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-6 py-4 border-t border-gray-700/60 bg-gray-900/30">
          <p className="text-xs text-gray-600">
            Report generated: {new Date().toLocaleString()}
          </p>
          <button
            onClick={onClose}
            className="px-4 py-2 bg-gray-800 hover:bg-gray-700 text-white text-sm font-medium rounded-lg transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
