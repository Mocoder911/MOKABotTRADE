"use client";

import React, { useEffect, useState, useCallback } from "react";
import Image from "next/image";
import { useAuth } from "@/contexts/AuthContext";
import { usePathname } from "next/navigation";

// ─── Types ────────────────────────────────────────────────────────────────────
interface AccountMetrics {
  balance: number;
  equity: number;
  pl: number;
  margin: number;
  positions: number;
}

interface MetricCardProps {
  label: string;
  value: string;
  accent?: "white" | "green" | "red" | "cyan";
}

// ─── Helpers ──────────────────────────────────────────────────────────────────
function formatUSD(value: number): string {
  return value.toLocaleString("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

function formatPL(value: number): string {
  const sign = value > 0 ? "+" : "";
  return `${sign}$${formatUSD(value)}`;
}

// ─── Metric Card ──────────────────────────────────────────────────────────────
function MetricCard({ label, value, accent = "white" }: MetricCardProps) {
  const colorMap = {
    white: "text-white glow-white",
    green: "text-emerald-400 glow-green",
    red: "text-rose-400 glow-rose",
    cyan: "text-cyan-400 glow-cyan",
  };
  return (
    <div className="flex flex-col items-center px-6 py-3">
      <span className="text-[11px] uppercase tracking-[0.2em] text-gray-500 font-medium mb-1.5">
        {label}
      </span>
      <span className={`text-lg font-bold font-mono ${colorMap[accent]}`}>
        {value}
      </span>
    </div>
  );
}

// ─── Navbar ───────────────────────────────────────────────────────────────────
export default function Navbar() {
  const { profile, user, signOut } = useAuth();
  const pathname = usePathname();
  const [metrics, setMetrics] = useState<AccountMetrics | null>(null);
  const [metricsLoading, setMetricsLoading] = useState(false);

  const fetchMetrics = useCallback(async () => {
    if (!user) return;
    setMetricsLoading(true);
    try {
      const res = await fetch("/api/account/metrics", {
        headers: { "x-user-id": user.id },
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setMetrics({
        balance: data.balance,
        equity: data.equity,
        pl: data.pl,
        margin: data.margin,
        positions: data.positions,
      });
    } catch (err) {
      console.error("Failed to fetch metrics:", err);
      setMetrics({ balance: 0, equity: 0, pl: 0, margin: 0, positions: 0 });
    } finally {
      setMetricsLoading(false);
    }
  }, [user]);

  // Fetch metrics on mount and every 30 seconds
  useEffect(() => {
    fetchMetrics();
    const interval = setInterval(fetchMetrics, 30000);
    return () => clearInterval(interval);
  }, [fetchMetrics]);

  // Hide navbar on auth pages
  if (pathname === "/login" || pathname === "/signup") {
    return null;
  }

  const plIsPositive = (metrics?.pl ?? 0) >= 0;
  const loadingValue = "—";

  return (
    <nav className="sticky top-0 z-50 w-full bg-gray-800/95 backdrop-blur-md border-b border-gray-700/60 shadow-lg shadow-black/20">
      <div className="max-w-[1400px] mx-auto flex items-center justify-between h-28 px-6">
        {/* Left: Logo */}
        <div className="flex items-center shrink-0">
          <Image
            src="/mokabot-logo.png"
            alt="MokaBot Logo"
            width={80}
            height={80}
            className="object-contain h-auto drop-shadow-[0_0_12px_rgba(34,211,238,0.5)]"
            priority
          />
        </div>

        {/* Center: Trading Metrics (Live from Supabase) */}
        <div className="hidden md:flex items-center divide-x divide-gray-700/50 rounded-2xl bg-gray-900/40 border border-gray-800/50 px-3 py-1.5">
          <MetricCard
            label="Balance"
            value={metrics ? `$${formatUSD(metrics.balance)}` : loadingValue}
            accent="cyan"
          />
          <MetricCard
            label="Equity"
            value={metrics ? `$${formatUSD(metrics.equity)}` : loadingValue}
            accent="cyan"
          />
          <MetricCard
            label="P/L"
            value={metrics ? formatPL(metrics.pl) : loadingValue}
            accent={metricsLoading ? "white" : plIsPositive ? "green" : "red"}
          />
          <MetricCard
            label="Margin"
            value={metrics ? `$${formatUSD(metrics.margin)}` : loadingValue}
          />
          <MetricCard
            label="Positions"
            value={metrics ? String(metrics.positions) : loadingValue}
            accent="cyan"
          />
        </div>

        {/* Right: User Info + Status */}
        <div className="flex items-center gap-4 shrink-0">
          {/* User info */}
          {profile && (
            <div className="hidden lg:flex flex-col items-end">
              <span className="text-sm font-medium text-white">{profile.full_name}</span>
              <span className="text-[10px] uppercase tracking-wider text-gray-500">
                {profile.role} &bull; {profile.status}
              </span>
            </div>
          )}

          {/* Bot Status — reflects real bot_active state */}
          <div className="flex items-center gap-2">
            {profile?.bot_active ? (
              <>
                <span className="relative flex h-3 w-3">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-3 w-3 bg-emerald-500"></span>
                </span>
                <span className="animate-pulse-glow text-emerald-400 font-bold text-sm tracking-wider">
                  ● LIVE
                </span>
              </>
            ) : (
              <>
                <span className="relative flex h-3 w-3">
                  <span className="relative inline-flex rounded-full h-3 w-3 bg-gray-500"></span>
                </span>
                <span className="text-gray-500 font-bold text-sm tracking-wider">
                  ● OFFLINE
                </span>
              </>
            )}
          </div>

          {/* Refresh Metrics */}
          <button
            onClick={fetchMetrics}
            disabled={metricsLoading}
            className="text-xs text-gray-500 hover:text-cyan-400 border border-gray-800 hover:border-cyan-500/30 rounded-lg px-2 py-1.5 transition-all duration-200 disabled:opacity-30"
            title="Refresh Metrics"
          >
            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={metricsLoading ? "animate-spin" : ""}>
              <polyline points="23 4 23 10 17 10"></polyline>
              <polyline points="1 20 1 14 7 14"></polyline>
              <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path>
            </svg>
          </button>

          {/* Sign out */}
          {profile && (
            <button
              onClick={signOut}
              className="text-xs text-gray-500 hover:text-rose-400 border border-gray-800 hover:border-rose-500/30 rounded-lg px-3 py-1.5 transition-all duration-200"
              title="Sign Out"
            >
              <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
                <polyline points="16 17 21 12 16 7" />
                <line x1="21" y1="12" x2="9" y2="12" />
              </svg>
            </button>
          )}
        </div>
      </div>

      {/* Mobile metrics row */}
      <div className="md:hidden flex items-center justify-around border-t border-gray-700/50 py-2 px-2 bg-gray-800/80">
        <MetricCard
          label="Balance"
          value={metrics ? `$${formatUSD(metrics.balance)}` : loadingValue}
          accent="cyan"
        />
        <MetricCard
          label="Equity"
          value={metrics ? `$${formatUSD(metrics.equity)}` : loadingValue}
          accent="cyan"
        />
        <MetricCard
          label="P/L"
          value={metrics ? formatPL(metrics.pl) : loadingValue}
          accent={metricsLoading ? "white" : plIsPositive ? "green" : "red"}
        />
        <MetricCard
          label="Margin"
          value={metrics ? `$${formatUSD(metrics.margin)}` : loadingValue}
        />
        <MetricCard
          label="Pos"
          value={metrics ? String(metrics.positions) : loadingValue}
          accent="cyan"
        />
      </div>
    </nav>
  );
}
