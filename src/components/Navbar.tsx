"use client";

import React from "react";
import Image from "next/image";

interface MetricCardProps {
  label: string;
  value: string;
  accent?: "white" | "green" | "red";
}

function MetricCard({ label, value, accent = "white" }: MetricCardProps) {
  const colorMap = {
    white: "text-white",
    green: "text-green-400",
    red: "text-red-400",
  };
  return (
    <div className="flex flex-col items-center px-4 py-1">
      <span className="text-[10px] uppercase tracking-widest text-gray-500 font-medium">
        {label}
      </span>
      <span className={`text-sm font-bold font-mono ${colorMap[accent]}`}>
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
    <nav className="sticky top-0 z-50 w-full bg-black border-b border-gray-800">
      <div className="max-w-7xl mx-auto flex items-center justify-between h-14 px-4">
        {/* Left: Logo */}
        <div className="flex items-center gap-2 shrink-0">
          <Image
            src="/mokabot-logo.png"
            alt="MokaBot Logo"
            width={36}
            height={36}
            className="object-contain h-auto"
            priority
          />
          <span className="text-white font-bold text-lg tracking-tight">
            Moka<span className="text-green-400">Bot</span>
          </span>
        </div>

        {/* Center: Trading Metrics */}
        <div className="hidden md:flex items-center divide-x divide-gray-700 rounded-xl bg-gray-900/60 border border-gray-800 px-1 py-1">
          <MetricCard label="Balance" value={metrics.balance} />
          <MetricCard label="Equity" value={metrics.equity} />
          <MetricCard
            label="P/L"
            value={metrics.pl}
            accent={plIsPositive ? "green" : "red"}
          />
          <MetricCard label="Margin" value={metrics.margin} />
          <MetricCard label="Position" value={metrics.position} />
        </div>

        {/* Right: Bot Status */}
        <div className="flex items-center gap-2 shrink-0">
          <span className="relative flex h-3 w-3">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-3 w-3 bg-green-500"></span>
          </span>
          <span className="animate-pulse-glow text-green-400 font-bold text-sm tracking-wider">
            ● LIVE
          </span>
        </div>
      </div>

      {/* Mobile metrics row */}
      <div className="md:hidden flex items-center justify-around border-t border-gray-800 py-2 px-2 bg-gray-950/80">
        <MetricCard label="Balance" value={metrics.balance} />
        <MetricCard label="Equity" value={metrics.equity} />
        <MetricCard
          label="P/L"
          value={metrics.pl}
          accent={plIsPositive ? "green" : "red"}
        />
        <MetricCard label="Margin" value={metrics.margin} />
        <MetricCard label="Pos" value={metrics.position} />
      </div>
    </nav>
  );
}
