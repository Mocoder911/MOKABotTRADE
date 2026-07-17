"use client";

import React, { useEffect, useState, useCallback, useRef } from "react";
import { useAuth } from "@/contexts/AuthContext";

// ─── Types ────────────────────────────────────────────────────────────────────
interface BridgeLog {
  id: string;
  mt5_account_id: string;
  level: "DEBUG" | "INFO" | "WARN" | "ERROR";
  message: string;
  created_at: string;
}

interface BridgeStatus {
  status: string;
  last_heartbeat: string | null;
  cycle_count: number;
  uptime_since: string | null;
  is_alive: boolean;
  seconds_since_heartbeat: number;
}

// ─── Helpers ──────────────────────────────────────────────────────────────────
function levelColor(level: string): string {
  switch (level) {
    case "DEBUG": return "text-gray-500";
    case "INFO": return "text-emerald-400";
    case "WARN": return "text-amber-400";
    case "ERROR": return "text-rose-400";
    default: return "text-gray-400";
  }
}

function formatUptime(since: string | null): string {
  if (!since) return "--:--:--";
  const start = new Date(since).getTime();
  const now = Date.now();
  const diff = Math.max(0, Math.floor((now - start) / 1000));
  const h = Math.floor(diff / 3600);
  const m = Math.floor((diff % 3600) / 60);
  const s = diff % 60;
  return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

function formatTime(iso: string): string {
  return new Date(iso).toLocaleTimeString("en-US", { hour12: false });
}

// ─── Component ────────────────────────────────────────────────────────────────
export default function BridgeConsole() {
  const { profile } = useAuth();
  const [logs, setLogs] = useState<BridgeLog[]>([]);
  const [status, setStatus] = useState<BridgeStatus | null>(null);
  const [sendingCmd, setSendingCmd] = useState<string | null>(null);
  const logEndRef = useRef<HTMLDivElement>(null);

  const mt5Id = profile?.mt5_account_id || "260904217";

  // Fetch logs
  const fetchLogs = useCallback(async () => {
    try {
      const res = await fetch(`/api/bridge/logs?mt5_account_id=${mt5Id}&limit=200`);
      if (res.ok) {
        const json = await res.json();
        setLogs(json.logs || []);
      }
    } catch {
      // silent
    }
  }, [mt5Id]);

  // Fetch status
  const fetchStatus = useCallback(async () => {
    try {
      const res = await fetch(`/api/bridge/status?mt5_account_id=${mt5Id}`);
      if (res.ok) {
        const json = await res.json();
        setStatus(json);
      }
    } catch {
      // silent
    }
  }, [mt5Id]);

  // Send command
  const sendCommand = async (command: string) => {
    setSendingCmd(command);
    try {
      await fetch("/api/bridge/commands", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ command, mt5_account_id: mt5Id }),
      });
    } catch {
      // silent
    }
    setSendingCmd(null);
  };

  // Poll logs every 3s, status every 5s
  useEffect(() => {
    fetchLogs();
    fetchStatus();
    const logInterval = setInterval(fetchLogs, 3000);
    const statusInterval = setInterval(fetchStatus, 5000);
    return () => {
      clearInterval(logInterval);
      clearInterval(statusInterval);
    };
  }, [fetchLogs, fetchStatus]);

  // Auto-scroll removed - user can scroll freely

  const isAlive = status?.is_alive ?? false;

  return (
    <div className="flex flex-col h-full gap-4">
      {/* ─── Top Bar: Status + Commands ─── */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        {/* Status indicators */}
        <div className="flex items-center gap-6">
          {/* Connection status */}
          <div className="flex items-center gap-2">
            {isAlive ? (
              <>
                <span className="relative flex h-3 w-3">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-3 w-3 bg-emerald-500"></span>
                </span>
                <span className="text-emerald-400 font-bold text-sm tracking-wider">RUNNING</span>
              </>
            ) : (
              <>
                <span className="relative flex h-3 w-3">
                  <span className="relative inline-flex rounded-full h-3 w-3 bg-rose-500"></span>
                </span>
                <span className="text-rose-400 font-bold text-sm tracking-wider">OFFLINE</span>
              </>
            )}
          </div>

          {/* Stats */}
          <div className="flex items-center gap-4 text-xs text-gray-500 font-mono">
            <span>Cycles: <span className="text-gray-300">{status?.cycle_count ?? 0}</span></span>
            <span>Uptime: <span className="text-gray-300">{formatUptime(status?.uptime_since ?? null)}</span></span>
            {status?.seconds_since_heartbeat !== undefined && (
              <span>Last beat: <span className={isAlive ? "text-emerald-400" : "text-rose-400"}>{status.seconds_since_heartbeat}s ago</span></span>
            )}
          </div>
        </div>

        {/* Command buttons */}
        <div className="flex items-center gap-2">
          <button
            onClick={() => sendCommand("RESTART")}
            disabled={sendingCmd !== null}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-amber-400 border border-amber-500/30 rounded-lg hover:bg-amber-500/10 transition-all disabled:opacity-40"
          >
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg>
            {sendingCmd === "RESTART" ? "Restarting..." : "Restart"}
          </button>
          <button
            onClick={() => sendCommand("STOP")}
            disabled={sendingCmd !== null}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-rose-400 border border-rose-500/30 rounded-lg hover:bg-rose-500/10 transition-all disabled:opacity-40"
          >
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 10a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1h-4a1 1 0 01-1-1v-4z" /></svg>
            {sendingCmd === "STOP" ? "Stopping..." : "Stop"}
          </button>
          <button
            onClick={fetchLogs}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-gray-400 border border-gray-700 rounded-lg hover:bg-gray-800 transition-all"
          >
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg>
            Refresh
          </button>
        </div>
      </div>

      {/* ─── Log Viewer ─── */}
      <div className="flex-1 min-h-0 bg-gray-950 border border-gray-800 rounded-xl overflow-hidden">
        {/* Terminal header */}
        <div className="flex items-center gap-2 px-4 py-2 bg-gray-900/80 border-b border-gray-800">
          <div className="flex gap-1.5">
            <div className="w-2.5 h-2.5 rounded-full bg-rose-500/80"></div>
            <div className="w-2.5 h-2.5 rounded-full bg-amber-500/80"></div>
            <div className="w-2.5 h-2.5 rounded-full bg-emerald-500/80"></div>
          </div>
          <span className="text-xs text-gray-500 font-mono ml-2">Bridge Console — MT5 Account {mt5Id}</span>
        </div>

        {/* Log content */}
        <div className="overflow-y-auto h-[calc(100%-40px)] p-4 font-mono text-xs leading-relaxed">
          {logs.length === 0 ? (
            <div className="text-gray-600 text-center py-12">
              <p className="text-sm">Waiting for bridge logs...</p>
              <p className="text-xs mt-1 text-gray-700">Start the bridge to see output here</p>
            </div>
          ) : (
            logs.map((log) => (
              <div key={log.id} className="flex gap-2 hover:bg-gray-900/50 px-1 py-0.5 rounded">
                <span className="text-gray-600 shrink-0">{formatTime(log.created_at)}</span>
                <span className={`shrink-0 w-12 text-right font-bold ${levelColor(log.level)}`}>
                  {log.level}
                </span>
                <span className="text-gray-300 break-all">{log.message}</span>
              </div>
            ))
          )}
          <div ref={logEndRef} />
        </div>
      </div>
    </div>
  );
}
