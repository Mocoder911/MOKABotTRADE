"use client";

import React, { useEffect, useState, useCallback } from "react";
import StrategyBuilder from "./StrategyBuilder";

// ─── Types ────────────────────────────────────────────────────────────────────
interface RiskMatrixRow {
  symbol: string;
  base_volume: number;
  sl_points: number;
  tp_points: number;
  be_trigger: number;
}

interface EditingState {
  [key: string]: {
    base_volume: string;
    sl_points: string;
    tp_points: string;
    be_trigger: string;
  };
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

// ─── Neon Input ───────────────────────────────────────────────────────────────
function NeonInput({
  value,
  onChange,
  accent = "cyan",
}: {
  value: string;
  onChange: (val: string) => void;
  accent?: "cyan" | "green";
}) {
  const glowClass = accent === "cyan" ? "focus:glow-cyan" : "focus:glow-green";
  const borderFocus =
    accent === "cyan"
      ? "focus:border-cyan-500/50"
      : "focus:border-emerald-500/50";
  const textFocus =
    accent === "cyan" ? "focus:text-cyan-400" : "focus:text-emerald-400";

  return (
    <input
      type="number"
      step="any"
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className={`w-24 bg-gray-900/60 border border-gray-700/50 rounded-lg px-3 py-1.5 text-sm font-mono text-gray-300 
      ${borderFocus} ${textFocus} ${glowClass} outline-none transition-all duration-200`}
    />
  );
}

// ─── Tactics Studio Page ──────────────────────────────────────────────────────
export default function TacticsStudio() {
  const [rows, setRows] = useState<RiskMatrixRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState<EditingState>({});
  const [saving, setSaving] = useState<string | null>(null);

  const fetchRiskMatrix = useCallback(async () => {
    try {
      const res = await fetch("/api/risk-matrix");
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const json = await res.json();
      setRows(json.data);
      // Initialize editing state
      const initial: EditingState = {};
      json.data.forEach((row: RiskMatrixRow) => {
        initial[row.symbol] = {
          base_volume: String(row.base_volume),
          sl_points: String(row.sl_points),
          tp_points: String(row.tp_points),
          be_trigger: String(row.be_trigger),
        };
      });
      setEditing(initial);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch risk matrix");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchRiskMatrix();
  }, [fetchRiskMatrix]);

  const handleSave = async (symbol: string) => {
    setSaving(symbol);
    const values = editing[symbol];
    try {
      const res = await fetch("/api/risk-matrix", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          symbol,
          base_volume: parseFloat(values.base_volume),
          sl_points: parseFloat(values.sl_points),
          tp_points: parseFloat(values.tp_points),
          be_trigger: parseFloat(values.be_trigger),
        }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      // Update local state
      setRows((prev) =>
        prev.map((r) =>
          r.symbol === symbol
            ? {
                ...r,
                base_volume: parseFloat(values.base_volume),
                sl_points: parseFloat(values.sl_points),
                tp_points: parseFloat(values.tp_points),
                be_trigger: parseFloat(values.be_trigger),
              }
            : r
        )
      );
    } catch (err) {
      console.error("Save failed:", err);
    } finally {
      setSaving(null);
    }
  };

  const updateField = (symbol: string, field: keyof EditingState[string], value: string) => {
    setEditing((prev) => ({
      ...prev,
      [symbol]: {
        ...prev[symbol],
        [field]: value,
      },
    }));
  };

  const hasChanges = (symbol: string) => {
    const row = rows.find((r) => r.symbol === symbol);
    const edit = editing[symbol];
    if (!row || !edit) return false;
    return (
      String(row.base_volume) !== edit.base_volume ||
      String(row.sl_points) !== edit.sl_points ||
      String(row.tp_points) !== edit.tp_points ||
      String(row.be_trigger) !== edit.be_trigger
    );
  };

  return (
    <div className="w-full mx-auto flex flex-col gap-8 px-4">
      {/* ─── Header ───────────────────────────────────────────────────────── */}
      <div className="flex items-end justify-between pt-2">
        <div>
          <h1 className="text-2xl font-bold text-white glow-white">
            Runtime Risk Matrix
          </h1>
          <p className="text-sm text-gray-500 mt-1.5">
            Configure risk parameters per symbol &bull; Changes sync to Supabase
          </p>
        </div>
        <button
          onClick={fetchRiskMatrix}
          disabled={loading}
          className="text-xs font-medium text-gray-400 hover:text-white border border-gray-700 hover:border-gray-500 rounded-xl px-4 py-2 transition-all duration-200 disabled:opacity-30 bg-gray-900/30"
        >
          {loading ? "Loading..." : "Refresh"}
        </button>
      </div>

      {/* ─── Error State ──────────────────────────────────────────────────── */}
      {error && (
        <div className="bg-rose-500/10 border border-rose-500/20 rounded-2xl px-5 py-4 text-rose-400 text-sm">
          <span className="font-bold">Connection error:</span> {error}
          <span className="text-rose-400/50 ml-2">
            — Ensure risk_matrix table exists in Supabase
          </span>
        </div>
      )}

      {/* ─── Risk Matrix Table ────────────────────────────────────────────── */}
      <div className="overflow-x-auto rounded-2xl border border-gray-800/50 bg-gray-950/40">
        <table className="w-full min-w-[800px]">
          <thead>
            <tr className="bg-gray-900/50">
              <Th>Symbol</Th>
              <Th>Base Volume</Th>
              <Th>SL (Points)</Th>
              <Th>TP (Points)</Th>
              <Th>BE Trigger</Th>
              <Th>Action</Th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={6} className="text-center py-20 text-gray-600">
                  <div className="flex flex-col items-center gap-3">
                    <div className="w-7 h-7 border-2 border-gray-700 border-t-cyan-500 rounded-full animate-spin"></div>
                    <span className="text-sm text-gray-500">
                      Loading risk matrix...
                    </span>
                  </div>
                </td>
              </tr>
            ) : rows.length === 0 ? (
              <tr>
                <td colSpan={6} className="text-center py-20 text-gray-600">
                  <div className="flex flex-col items-center gap-3">
                    <span className="text-5xl opacity-40">🎯</span>
                    <span className="text-sm text-gray-500">
                      No risk matrix entries found
                    </span>
                    <span className="text-xs text-gray-600">
                      Add rows to the risk_matrix table in Supabase
                    </span>
                  </div>
                </td>
              </tr>
            ) : (
              rows.map((row) => (
                <tr
                  key={row.symbol}
                  className="hover:bg-gray-900/30 transition-colors duration-150"
                >
                  <Td className="text-white font-semibold text-base glow-cyan">
                    {row.symbol}
                  </Td>
                  <Td>
                    <NeonInput
                      value={editing[row.symbol]?.base_volume ?? ""}
                      onChange={(val) => updateField(row.symbol, "base_volume", val)}
                      accent="cyan"
                    />
                  </Td>
                  <Td>
                    <NeonInput
                      value={editing[row.symbol]?.sl_points ?? ""}
                      onChange={(val) => updateField(row.symbol, "sl_points", val)}
                      accent="cyan"
                    />
                  </Td>
                  <Td>
                    <NeonInput
                      value={editing[row.symbol]?.tp_points ?? ""}
                      onChange={(val) => updateField(row.symbol, "tp_points", val)}
                      accent="cyan"
                    />
                  </Td>
                  <Td>
                    <NeonInput
                      value={editing[row.symbol]?.be_trigger ?? ""}
                      onChange={(val) => updateField(row.symbol, "be_trigger", val)}
                      accent="green"
                    />
                  </Td>
                  <Td>
                    <button
                      onClick={() => handleSave(row.symbol)}
                      disabled={saving === row.symbol || !hasChanges(row.symbol)}
                      className={`text-xs font-bold px-4 py-2 rounded-lg border transition-all duration-200 
                        ${
                          hasChanges(row.symbol)
                            ? "text-emerald-400 border-emerald-500/40 bg-emerald-500/10 hover:bg-emerald-500/20 glow-green"
                            : "text-gray-600 border-gray-700/50 bg-gray-900/30 cursor-not-allowed"
                        }`}
                    >
                      {saving === row.symbol ? "Saving..." : "Save"}
                    </button>
                  </Td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* ─── Footer ───────────────────────────────────────────────────────── */}
      <div className="flex items-center justify-between text-xs text-gray-600 px-1 pb-4">
        <span className="text-gray-500">
          <span className="text-cyan-400/60">●</span> Edits sync directly to Supabase
        </span>
        <span className="font-mono">
          {rows.length} symbol{rows.length !== 1 ? "s" : ""} configured
        </span>
      </div>

      {/* ─── Strategy Builder ─────────────────────────────────────────────── */}
      <div className="mt-8 pt-8 border-t border-gray-800/50">
        <StrategyBuilder />
      </div>
    </div>
  );
}
