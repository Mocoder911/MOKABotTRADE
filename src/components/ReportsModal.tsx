"use client";

import React, { useState, useRef, useEffect } from "react";
import Image from "next/image";
import { useAuth } from "@/contexts/AuthContext";

interface Trade {
  symbol: string;
  live_pl: number;
  closed_at: string;
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

type Period = "daily" | "weekly" | "monthly" | "custom" | "all-time";

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

function formatDate(dateStr: string): string {
  return new Date(dateStr).toISOString().split("T")[0];
}

export default function ReportsDropdown() {
  const { user } = useAuth();
  const [isOpen, setIsOpen] = useState(false);
  const [showCustomDates, setShowCustomDates] = useState(false);
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [loading, setLoading] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
        setShowCustomDates(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const generateReport = async (period: Period) => {
    if (!user) return;

    if (period === "custom") {
      if (!startDate || !endDate) {
        alert("Please select both start and end dates");
        return;
      }
      setShowCustomDates(true);
      return;
    }

    setLoading(true);
    try {
      const params = new URLSearchParams({ period });
      const res = await fetch(`/api/reports?${params.toString()}`, {
        headers: { "x-user-id": user.id },
        cache: "no-store",
      });

      if (res.ok) {
        const data = await res.json();
        openReportWindow(data, period);
      }
    } catch (err) {
      console.error("Failed to fetch report:", err);
    } finally {
      setLoading(false);
      setIsOpen(false);
    }
  };

  const generateCustomReport = async () => {
    if (!user || !startDate || !endDate) return;

    setLoading(true);
    try {
      const params = new URLSearchParams({
        period: "custom",
        start: startDate,
        end: endDate,
      });
      const res = await fetch(`/api/reports?${params.toString()}`, {
        headers: { "x-user-id": user.id },
        cache: "no-store",
      });

      if (res.ok) {
        const data = await res.json();
        openReportWindow(data, "custom", startDate, endDate);
      }
    } catch (err) {
      console.error("Failed to fetch report:", err);
    } finally {
      setLoading(false);
      setShowCustomDates(false);
      setIsOpen(false);
    }
  };

  const openReportWindow = (data: ReportData, period: Period, start?: string, end?: string) => {
    const periodLabels: Record<string, string> = {
      daily: "Daily Report",
      weekly: "Weekly Report",
      monthly: "Monthly Report",
      "all-time": "All-Time Report",
      custom: `Custom Report (${start} to ${end})`,
    };

    const periodLabel = periodLabels[period] || "Report";
    const generatedAt = new Date().toLocaleString();

    const htmlContent = `
<!DOCTYPE html>
<html>
<head>
  <title>Trading Report - ${periodLabel}</title>
  <style>
    @media print {
      body { margin: 0; padding: 20px; }
      .no-print { display: none; }
    }
    body {
      font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
      background: #1a1f26;
      color: #fff;
      margin: 0;
      padding: 20px;
    }
    .header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 20px;
      border-bottom: 2px solid #374151;
      margin-bottom: 30px;
    }
    .logo-section {
      display: flex;
      align-items: center;
      gap: 15px;
    }
    .logo-text {
      font-size: 24px;
      font-weight: bold;
      color: #22d3ee;
    }
    .mt5-badge {
      background: linear-gradient(135deg, #3b82f6, #1d4ed8);
      padding: 10px 20px;
      border-radius: 8px;
      font-weight: bold;
      font-size: 18px;
    }
    .title {
      text-align: center;
      flex: 1;
    }
    .title h1 {
      margin: 0;
      font-size: 28px;
      letter-spacing: 2px;
    }
    .title p {
      margin: 5px 0 0 0;
      color: #6b7280;
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 2px;
    }
    .summary {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 20px;
      margin-bottom: 30px;
    }
    .summary-card {
      background: #111827;
      border: 1px solid #374151;
      border-radius: 12px;
      padding: 20px;
      text-align: center;
    }
    .summary-card label {
      display: block;
      font-size: 11px;
      color: #6b7280;
      text-transform: uppercase;
      letter-spacing: 1px;
      margin-bottom: 8px;
    }
    .summary-card .value {
      font-size: 28px;
      font-weight: bold;
    }
    .value-cyan { color: #22d3ee; }
    .value-green { color: #10b981; }
    .value-white { color: #fff; }
    table {
      width: 100%;
      border-collapse: collapse;
      background: #111827;
      border-radius: 12px;
      overflow: hidden;
    }
    th {
      background: #1f2937;
      padding: 15px;
      text-align: left;
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 1px;
      color: #6b7280;
    }
    td {
      padding: 12px 15px;
      border-top: 1px solid #374151;
    }
    tr:hover { background: #1f2937; }
    .type-buy {
      background: rgba(16, 185, 129, 0.2);
      color: #10b981;
      padding: 4px 8px;
      border-radius: 4px;
      font-size: 11px;
      font-weight: 600;
    }
    .type-sell {
      background: rgba(244, 63, 94, 0.2);
      color: #f43f5e;
      padding: 4px 8px;
      border-radius: 4px;
      font-size: 11px;
      font-weight: 600;
    }
    .profit { color: #10b981; font-family: monospace; text-align: right; }
    .footer {
      margin-top: 30px;
      padding-top: 20px;
      border-top: 1px solid #374151;
      display: flex;
      justify-content: space-between;
      font-size: 12px;
      color: #6b7280;
    }
    .print-btn {
      background: #22d3ee;
      color: #000;
      border: none;
      padding: 12px 30px;
      border-radius: 8px;
      font-weight: bold;
      cursor: pointer;
      font-size: 14px;
    }
    .print-btn:hover { background: #06b6d4; }
    .no-trades {
      text-align: center;
      padding: 40px;
      color: #6b7280;
      font-size: 18px;
    }
  </style>
</head>
<body>
  <div class="no-print" style="text-align: center; margin-bottom: 20px;">
    <button class="print-btn" onclick="window.print()">Print / Save as PDF</button>
  </div>

  <div class="header">
    <div class="logo-section">
      <div class="logo-text">MOKABot</div>
    </div>
    <div class="title">
      <h1>${periodLabel}</h1>
      <p>Winning Trades Only</p>
    </div>
    <div class="logo-section">
      <div class="mt5-badge">MetaTrader 5</div>
    </div>
  </div>

  <div class="summary">
    <div class="summary-card">
      <label>Winning Trades</label>
      <div class="value value-cyan">${data.tradeCount}</div>
    </div>
    <div class="summary-card">
      <label>Total Profit</label>
      <div class="value value-green">+$${formatUSD(data.totalProfit)}</div>
    </div>
    <div class="summary-card">
      <label>Balance</label>
      <div class="value value-white">$${formatUSD(data.balance)}</div>
    </div>
  </div>

  ${data.trades.length > 0 ? `
  <table>
    <thead>
      <tr>
        <th>Symbol</th>
        <th>Type</th>
        <th>Volume</th>
        <th style="text-align: right;">Profit</th>
        <th style="text-align: right;">Closed</th>
      </tr>
    </thead>
    <tbody>
      ${data.trades.map(trade => `
      <tr>
        <td>${trade.symbol}</td>
        <td><span class="type-${trade.type}">${trade.type?.toUpperCase()}</span></td>
        <td>${trade.volume}</td>
        <td class="profit">+$${formatUSD(trade.live_pl)}</td>
        <td style="text-align: right; color: #6b7280;">${formatTime(trade.closed_at)}</td>
      </tr>
      `).join("")}
    </tbody>
  </table>
  ` : '<div class="no-trades">No winning trades found for this period</div>'}

  <div class="footer">
    <span>Report generated: ${generatedAt}</span>
    <span>MOKABot Trading Platform</span>
  </div>

  <script>
    // Auto-focus print button
    document.querySelector('.print-btn')?.focus();
  </script>
</body>
</html>
    `;

    const printWindow = window.open("", "_blank");
    if (printWindow) {
      printWindow.document.write(htmlContent);
      printWindow.document.close();
    }
  };

  return (
    <div className="relative" ref={dropdownRef}>
      {/* Reports Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="text-xs text-gray-500 hover:text-cyan-400 border border-gray-800 hover:border-cyan-500/30 rounded-lg px-3 py-1.5 transition-all duration-200"
        title="Reports"
      >
        <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
          <polyline points="14 2 14 8 20 8"></polyline>
          <line x1="16" y1="13" x2="8" y2="13"></line>
          <line x1="16" y1="17" x2="8" y2="17"></line>
          <polyline points="10 9 9 9 8 9"></polyline>
        </svg>
      </button>

      {/* Dropdown Menu */}
      {isOpen && (
        <div className="absolute right-0 top-full mt-2 w-56 bg-[#1a1f26] border border-gray-700/60 rounded-xl shadow-2xl overflow-hidden z-50">
          <div className="px-4 py-3 border-b border-gray-700/40 bg-gray-900/30">
            <p className="text-xs font-medium text-gray-400 uppercase tracking-wider">Generate Report</p>
          </div>

          <div className="p-2">
            <button
              onClick={() => generateReport("daily")}
              disabled={loading}
              className="w-full text-left px-4 py-3 rounded-lg text-sm text-gray-300 hover:text-white hover:bg-gray-800/50 transition-colors flex items-center gap-3 disabled:opacity-50"
            >
              <svg className="w-4 h-4 text-cyan-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <circle cx="12" cy="12" r="10" strokeWidth="2"></circle>
                <polyline points="12 6 12 12 16 14" strokeWidth="2"></polyline>
              </svg>
              Daily Report
            </button>

            <button
              onClick={() => generateReport("weekly")}
              disabled={loading}
              className="w-full text-left px-4 py-3 rounded-lg text-sm text-gray-300 hover:text-white hover:bg-gray-800/50 transition-colors flex items-center gap-3 disabled:opacity-50"
            >
              <svg className="w-4 h-4 text-cyan-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <rect x="3" y="4" width="18" height="18" rx="2" ry="2" strokeWidth="2"></rect>
                <line x1="16" y1="2" x2="16" y2="6" strokeWidth="2"></line>
                <line x1="8" y1="2" x2="8" y2="6" strokeWidth="2"></line>
                <line x1="3" y1="10" x2="21" y2="10" strokeWidth="2"></line>
              </svg>
              Weekly Report
            </button>

            <button
              onClick={() => generateReport("monthly")}
              disabled={loading}
              className="w-full text-left px-4 py-3 rounded-lg text-sm text-gray-300 hover:text-white hover:bg-gray-800/50 transition-colors flex items-center gap-3 disabled:opacity-50"
            >
              <svg className="w-4 h-4 text-cyan-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <rect x="3" y="4" width="18" height="18" rx="2" ry="2" strokeWidth="2"></rect>
                <line x1="16" y1="2" x2="16" y2="6" strokeWidth="2"></line>
                <line x1="8" y1="2" x2="8" y2="6" strokeWidth="2"></line>
                <line x1="3" y1="10" x2="21" y2="10" strokeWidth="2"></line>
              </svg>
              Monthly Report
            </button>

            <button
              onClick={() => generateReport("all-time")}
              disabled={loading}
              className="w-full text-left px-4 py-3 rounded-lg text-sm text-gray-300 hover:text-white hover:bg-gray-800/50 transition-colors flex items-center gap-3 disabled:opacity-50"
            >
              <svg className="w-4 h-4 text-cyan-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" strokeWidth="2"></polyline>
              </svg>
              All-Time Report
            </button>

            <div className="border-t border-gray-700/40 my-2"></div>

            <button
              onClick={() => generateReport("custom")}
              disabled={loading}
              className="w-full text-left px-4 py-3 rounded-lg text-sm text-gray-300 hover:text-white hover:bg-gray-800/50 transition-colors flex items-center gap-3 disabled:opacity-50"
            >
              <svg className="w-4 h-4 text-cyan-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <circle cx="12" cy="12" r="10" strokeWidth="2"></circle>
                <line x1="12" y1="8" x2="12" y2="12" strokeWidth="2"></line>
                <line x1="12" y1="16" x2="12.01" y2="16" strokeWidth="2"></line>
              </svg>
              Custom Date Range
            </button>
          </div>

          {/* Custom Date Picker */}
          {showCustomDates && (
            <div className="p-4 border-t border-gray-700/40 bg-gray-900/30">
              <div className="space-y-3">
                <div>
                  <label className="block text-xs text-gray-500 mb-1">Start Date</label>
                  <input
                    type="date"
                    value={startDate}
                    onChange={(e) => setStartDate(e.target.value)}
                    className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-sm text-white focus:outline-none focus:border-cyan-500"
                  />
                </div>
                <div>
                  <label className="block text-xs text-gray-500 mb-1">End Date</label>
                  <input
                    type="date"
                    value={endDate}
                    onChange={(e) => setEndDate(e.target.value)}
                    className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-sm text-white focus:outline-none focus:border-cyan-500"
                  />
                </div>
                <button
                  onClick={generateCustomReport}
                  disabled={loading || !startDate || !endDate}
                  className="w-full py-2 bg-cyan-500 hover:bg-cyan-600 text-black font-medium rounded-lg text-sm transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {loading ? "Generating..." : "Generate Report"}
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
