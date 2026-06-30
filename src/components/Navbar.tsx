"use client";

import React from "react";
import Image from "next/image";

interface MetricCardProps {
  label: string;
  value: string;
  accent?: "white" | "green" | "red" | "cyan";
}

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

export default function Navbar() {
  // Placeholder metrics — will be replaced with live Supabase data
  const metrics = {
    balance: "$10,000.00",
    equity: "$10,245.80",
    pl: "+$245.80",
    margin: "$1,200.00",
    position: "3",
  };

  const plIsPositive = true;

  return (
    <nav className="sticky top-0 z-50 w-full bg-black/95 backdrop-blur-md border-b border-gray-800/60">
      <div className="max-w-[1400px] mx-auto flex items-center justify-between h-20 px-6">
        {/* Left: Logo */}
        <div className="flex items-center shrink-0">
          <Image
            src="/mokabot-logo.png"
            alt="MokaBot Logo"
            width={54}
            height={54}
            className="object-contain h-auto"
            priority
          />
        </div>

        {/* Center: Trading Metrics */}
        <div className="hidden md:flex items-center divide-x divide-gray-700/50 rounded-2xl bg-gray-900/40 border border-gray-800/50 px-3 py-1.5">
          <MetricCard label="Balance" value={metrics.balance} accent="cyan" />
          <MetricCard label="Equity" value={metrics.equity} accent="cyan" />
          <MetricCard
            label="P/L"
            value={metrics.pl}
            accent={plIsPositive ? "green" : "red"}
          />
          <MetricCard label="Margin" value={metrics.margin} />
          <MetricCard label="Positions" value={metrics.position} accent="cyan" />
        </div>

        {/* Right: Bot Status */}
        <div className="flex items-center gap-2 shrink-0">
          <span className="relative flex h-3 w-3">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-3 w-3 bg-emerald-500"></span>
          </span>
          <span className="animate-pulse-glow text-emerald-400 font-bold text-sm tracking-wider">
            ● LIVE
          </span>
        </div>
      </div>

      {/* Mobile metrics row */}
      <div className="md:hidden flex items-center justify-around border-t border-gray-800/50 py-2 px-2 bg-gray-950/80">
        <MetricCard label="Balance" value={metrics.balance} accent="cyan" />
        <MetricCard label="Equity" value={metrics.equity} accent="cyan" />
        <MetricCard
          label="P/L"
          value={metrics.pl}
          accent={plIsPositive ? "green" : "red"}
        />
        <MetricCard label="Margin" value={metrics.margin} />
        <MetricCard label="Pos" value={metrics.position} accent="cyan" />
      </div>
    </nav>
  );
}
