"use client";

import React, { useEffect, useState, useCallback } from "react";

// ─── Types ────────────────────────────────────────────────────────────────────
interface Strategy {
  id: string;
  name: string;
  description?: string;
  symbol: string;
  entry_rules: Record<string, unknown>;
  exit_rules: Record<string, unknown>;
  sizing_rules: Record<string, unknown>;
  filters: Record<string, unknown>;
  is_active: boolean;
  priority: number;
  dry_run: boolean;  // Dry run mode flag
  created_at: string;
}

interface Condition {
  indicator: string;
  params: Record<string, number>;
  operator: string;
  value?: number;
  compare_to?: string;
}

// ─── Indicator Definitions ────────────────────────────────────────────────────
const INDICATORS: Record<string, { label: string; params: { name: string; default: number; label: string }[] }> = {
  rsi: {
    label: "RSI",
    params: [{ name: "length", default: 14, label: "Period" }],
  },
  macd: {
    label: "MACD",
    params: [
      { name: "fast", default: 12, label: "Fast" },
      { name: "slow", default: 26, label: "Slow" },
      { name: "signal", default: 9, label: "Signal" },
    ],
  },
  bbands: {
    label: "Bollinger Bands",
    params: [
      { name: "length", default: 20, label: "Period" },
      { name: "std", default: 2, label: "Std Dev" },
    ],
  },
  sma: {
    label: "SMA",
    params: [{ name: "length", default: 20, label: "Period" }],
  },
  ema: {
    label: "EMA",
    params: [{ name: "length", default: 20, label: "Period" }],
  },
  stoch: {
    label: "Stochastic",
    params: [
      { name: "k", default: 14, label: "%K Period" },
      { name: "d", default: 3, label: "%D Period" },
    ],
  },
  atr: {
    label: "ATR",
    params: [{ name: "length", default: 14, label: "Period" }],
  },
  adx: {
    label: "ADX",
    params: [{ name: "length", default: 14, label: "Period" }],
  },
  cci: {
    label: "CCI",
    params: [{ name: "length", default: 20, label: "Period" }],
  },
  willr: {
    label: "Williams %R",
    params: [{ name: "length", default: 14, label: "Period" }],
  },
  supertrend: {
    label: "SuperTrend",
    params: [
      { name: "length", default: 10, label: "Period" },
      { name: "multiplier", default: 3, label: "Multiplier" },
    ],
  },
  psar: {
    label: "Parabolic SAR",
    params: [
      { name: "af0", default: 0.02, label: "AF Start" },
      { name: "af", default: 0.2, label: "AF Max" },
    ],
  },
};

const OPERATORS = [
  { value: "lt", label: "< Less Than" },
  { value: "gt", label: "> Greater Than" },
  { value: "lte", label: "≤ Less or Equal" },
  { value: "gte", label: "≥ Greater or Equal" },
  { value: "eq", label: "= Equal" },
  { value: "crosses_above", label: "Crosses Above" },
  { value: "crosses_below", label: "Crosses Below" },
];

const TIMEFRAMES = ["M1", "M5", "M15", "M30", "H1", "H4", "D1", "W1"];

// ─── Strategy Builder Component ───────────────────────────────────────────────
export default function StrategyBuilder() {
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [loading, setLoading] = useState(true);
  const [showBuilder, setShowBuilder] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Builder state
  const [builderName, setBuilderName] = useState("");
  const [builderDesc, setBuilderDesc] = useState("");
  const [builderSymbol, setBuilderSymbol] = useState("XAUUSD");
  const [builderTimeframe, setBuilderTimeframe] = useState("M15");
  const [builderLogic, setBuilderLogic] = useState<"AND" | "OR">("AND");
  const [conditions, setConditions] = useState<Condition[]>([
    { indicator: "rsi", params: { length: 14 }, operator: "lt", value: 30 },
  ]);
  const [riskPerTrade, setRiskPerTrade] = useState(1.0);
  const [maxVolume, setMaxVolume] = useState(0.5);
  const [maxSpread, setMaxSpread] = useState(50);
  const [dryRun, setDryRun] = useState(true);  // Default to dry run for safety

  const fetchStrategies = useCallback(async () => {
    try {
      const res = await fetch("/api/strategies");
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const json = await res.json();
      setStrategies(json.data || []);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch strategies");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchStrategies();
  }, [fetchStrategies]);

  const updateCondition = (index: number, field: keyof Condition, value: unknown) => {
    setConditions((prev) => {
      const updated = [...prev];
      if (field === "indicator") {
        // Reset params when indicator changes
        const indicator = value as string;
        const def = INDICATORS[indicator];
        const newParams: Record<string, number> = {};
        def?.params.forEach((p) => {
          newParams[p.name] = p.default;
        });
        updated[index] = { ...updated[index], indicator, params: newParams };
      } else if (field === "params") {
        updated[index] = { ...updated[index], params: value as Record<string, number> };
      } else {
        updated[index] = { ...updated[index], [field]: value };
      }
      return updated;
    });
  };

  const updateParam = (condIndex: number, paramName: string, value: number) => {
    setConditions((prev) => {
      const updated = [...prev];
      updated[condIndex] = {
        ...updated[condIndex],
        params: { ...updated[condIndex].params, [paramName]: value },
      };
      return updated;
    });
  };

  const addCondition = () => {
    setConditions((prev) => [
      ...prev,
      { indicator: "rsi", params: { length: 14 }, operator: "lt", value: 30 },
    ]);
  };

  const removeCondition = (index: number) => {
    setConditions((prev) => prev.filter((_, i) => i !== index));
  };

  const buildEntryRules = () => ({
    conditions: conditions.map((c) => {
      const base: Record<string, unknown> = {
        indicator: c.indicator,
        params: c.params,
        operator: c.operator,
      };
      if (c.value !== undefined) base.value = c.value;
      if (c.compare_to) base.compare_to = c.compare_to;
      return base;
    }),
    logic: builderLogic,
    timeframe: builderTimeframe,
  });

  const validateJson = (): string | null => {
    if (!builderName.trim()) return "Strategy name is required";
    if (!builderSymbol.trim()) return "Symbol is required";
    if (conditions.length === 0) return "At least one condition is required";
    
    for (let i = 0; i < conditions.length; i++) {
      const c = conditions[i];
      if (!c.indicator) return `Condition ${i + 1}: Indicator is required`;
      if (!c.operator) return `Condition ${i + 1}: Operator is required`;
      if (c.operator !== "crosses_above" && c.operator !== "crosses_below" && c.value === undefined) {
        return `Condition ${i + 1}: Value is required`;
      }
    }
    
    return null;
  };

  const handleSave = async () => {
    const validationError = validateJson();
    if (validationError) {
      setError(validationError);
      return;
    }

    setSaving(true);
    setError(null);

    const entryRules = buildEntryRules();

    try {
      const res = await fetch("/api/strategies", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: builderName,
          description: builderDesc,
          symbol: builderSymbol,
          entry_rules: entryRules,
          exit_rules: {},
          sizing_rules: {
            mode: "risk_percent",
            risk_per_trade: riskPerTrade,
            max_volume: maxVolume,
          },
          filters: {
            max_spread_points: maxSpread,
          },
          is_active: false,
          priority: 0,
          dry_run: dryRun,  // Include dry_run flag
        }),
      });

      if (!res.ok) {
        const json = await res.json();
        throw new Error(json.error || `HTTP ${res.status}`);
      }

      setSuccessMsg(`Strategy "${builderName}" created successfully`);
      setTimeout(() => setSuccessMsg(null), 3000);

      // Reset builder
      setShowBuilder(false);
      setBuilderName("");
      setBuilderDesc("");
      setConditions([{ indicator: "rsi", params: { length: 14 }, operator: "lt", value: 30 }]);

      fetchStrategies();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save strategy");
    } finally {
      setSaving(false);
    }
  };

  const toggleStrategy = async (id: string, isActive: boolean) => {
    try {
      const res = await fetch("/api/strategies", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id, is_active: !isActive }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      fetchStrategies();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to toggle strategy");
    }
  };

  return (
    <div className="flex flex-col gap-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-white">Strategy Builder</h2>
          <p className="text-sm text-gray-500 mt-1">
            Create trading strategies with visual rules — no JSON coding needed
          </p>
        </div>
        <div className="flex gap-3">
          <button
            onClick={fetchStrategies}
            className="text-xs text-gray-400 hover:text-white border border-gray-700 hover:border-gray-500 rounded-xl px-4 py-2 transition-all"
          >
            Refresh
          </button>
          <button
            onClick={() => setShowBuilder(!showBuilder)}
            className="flex items-center gap-2 text-xs font-bold text-emerald-400 border border-emerald-500/40 bg-emerald-500/10 hover:bg-emerald-500/20 rounded-xl px-4 py-2 transition-all glow-green"
          >
            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="12" y1="5" x2="12" y2="19"></line>
              <line x1="5" y1="12" x2="19" y2="12"></line>
            </svg>
            New Strategy
          </button>
        </div>
      </div>

      {/* Success */}
      {successMsg && (
        <div className="bg-emerald-500/10 border border-emerald-500/30 rounded-2xl px-5 py-3 text-emerald-400 text-sm glow-green">
          ✓ {successMsg}
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="bg-rose-500/10 border border-rose-500/20 rounded-2xl px-5 py-4 text-rose-400 text-sm">
          Error: {error}
        </div>
      )}

      {/* Builder Form */}
      {showBuilder && (
        <div className="rounded-2xl border border-gray-700/50 bg-[#1a1f26] p-8">
          <h3 className="text-lg font-bold text-white mb-6">New Strategy</h3>

          {/* Basic Info */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
            <div className="flex flex-col gap-2">
              <label className="text-sm font-medium text-gray-400">Name *</label>
              <input
                type="text"
                value={builderName}
                onChange={(e) => setBuilderName(e.target.value)}
                placeholder="My Strategy"
                className="bg-gray-800 border border-gray-700 p-3 rounded-lg focus:ring-2 focus:ring-green-500 text-gray-300 outline-none transition-all"
              />
            </div>
            <div className="flex flex-col gap-2">
              <label className="text-sm font-medium text-gray-400">Symbol *</label>
              <input
                type="text"
                value={builderSymbol}
                onChange={(e) => setBuilderSymbol(e.target.value)}
                placeholder="XAUUSD"
                className="bg-gray-800 border border-gray-700 p-3 rounded-lg focus:ring-2 focus:ring-green-500 text-gray-300 outline-none transition-all"
              />
            </div>
            <div className="flex flex-col gap-2">
              <label className="text-sm font-medium text-gray-400">Timeframe</label>
              <select
                value={builderTimeframe}
                onChange={(e) => setBuilderTimeframe(e.target.value)}
                className="bg-gray-800 border border-gray-700 p-3 rounded-lg focus:ring-2 focus:ring-green-500 text-gray-300 outline-none transition-all"
              >
                {TIMEFRAMES.map((tf) => (
                  <option key={tf} value={tf}>{tf}</option>
                ))}
              </select>
            </div>
          </div>

          {/* Description */}
          <div className="mb-8">
            <label className="text-sm font-medium text-gray-400 block mb-2">Description</label>
            <input
              type="text"
              value={builderDesc}
              onChange={(e) => setBuilderDesc(e.target.value)}
              placeholder="Optional description"
              className="w-full bg-gray-800 border border-gray-700 p-3 rounded-lg focus:ring-2 focus:ring-green-500 text-gray-300 outline-none transition-all"
            />
          </div>

          {/* Conditions */}
          <div className="mb-8">
            <div className="flex items-center justify-between mb-4">
              <label className="text-sm font-medium text-gray-400">
                Entry Conditions
              </label>
              <div className="flex items-center gap-2">
                <span className="text-sm text-gray-500">Logic:</span>
                <select
                  value={builderLogic}
                  onChange={(e) => setBuilderLogic(e.target.value as "AND" | "OR")}
                  className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-300 focus:ring-2 focus:ring-green-500 outline-none"
                >
                  <option value="AND">AND (all must match)</option>
                  <option value="OR">OR (any can match)</option>
                </select>
              </div>
            </div>

            {conditions.map((cond, index) => (
              <div key={index} className="grid grid-cols-1 md:grid-cols-5 gap-4 mb-4 p-5 rounded-xl bg-gray-800/50 border border-gray-700/50 items-end">
                {/* Indicator */}
                <div className="flex flex-col gap-2">
                  <label className="text-sm font-medium text-gray-400">Indicator</label>
                  <select
                    value={cond.indicator}
                    onChange={(e) => updateCondition(index, "indicator", e.target.value)}
                    className="bg-gray-800 border border-gray-700 p-3 rounded-lg focus:ring-2 focus:ring-green-500 text-gray-300 outline-none transition-all"
                  >
                    {Object.entries(INDICATORS).map(([key, val]) => (
                      <option key={key} value={key}>{val.label}</option>
                    ))}
                  </select>
                </div>

                {/* Parameters */}
                <div className="flex flex-col gap-2">
                  <label className="text-sm font-medium text-gray-400">Parameters</label>
                  <div className="flex gap-3">
                    {INDICATORS[cond.indicator]?.params.map((param) => (
                      <div key={param.name} className="flex flex-col gap-1 flex-1">
                        <span className="text-xs text-gray-500">{param.label}</span>
                        <input
                          type="number"
                          value={cond.params[param.name] ?? param.default}
                          onChange={(e) => updateParam(index, param.name, parseFloat(e.target.value))}
                          className="bg-gray-800 border border-gray-700 p-3 rounded-lg focus:ring-2 focus:ring-green-500 text-gray-300 outline-none transition-all w-full"
                        />
                      </div>
                    ))}
                  </div>
                </div>

                {/* Operator */}
                <div className="flex flex-col gap-2">
                  <label className="text-sm font-medium text-gray-400">Condition</label>
                  <select
                    value={cond.operator}
                    onChange={(e) => updateCondition(index, "operator", e.target.value)}
                    className="bg-gray-800 border border-gray-700 p-3 rounded-lg focus:ring-2 focus:ring-green-500 text-gray-300 outline-none transition-all"
                  >
                    {OPERATORS.map((op) => (
                      <option key={op.value} value={op.value}>{op.label}</option>
                    ))}
                  </select>
                </div>

                {/* Value */}
                {cond.operator !== "crosses_above" && cond.operator !== "crosses_below" ? (
                  <div className="flex flex-col gap-2">
                    <label className="text-sm font-medium text-gray-400">Value</label>
                    <input
                      type="number"
                      value={cond.value ?? 0}
                      onChange={(e) => updateCondition(index, "value", parseFloat(e.target.value))}
                      className="bg-gray-800 border border-gray-700 p-3 rounded-lg focus:ring-2 focus:ring-green-500 text-gray-300 outline-none transition-all"
                    />
                  </div>
                ) : <div />}

                {/* Remove */}
                <div className="flex items-end">
                  {conditions.length > 1 ? (
                    <button
                      onClick={() => removeCondition(index)}
                      className="w-full text-rose-400 border border-rose-500/40 bg-rose-500/10 hover:bg-rose-500/20 rounded-lg p-3 transition-all text-sm font-medium"
                    >
                      Remove
                    </button>
                  ) : <div />}
                </div>
              </div>
            ))}

            <button
              onClick={addCondition}
              className="text-sm text-green-400 hover:text-green-300 border border-green-500/30 hover:border-green-500/50 rounded-lg px-4 py-2.5 transition-all font-medium"
            >
              + Add Condition
            </button>
          </div>

          {/* Dry Run Toggle */}
          <div className="mb-6 p-4 rounded-xl bg-gray-900/40 border border-amber-500/30">
            <div className="flex items-center justify-between">
              <div>
                <label className="text-[10px] uppercase tracking-wider text-amber-400/80 font-bold block">
                  🧪 Dry Run Mode (Simulation)
                </label>
                <p className="text-xs text-gray-500 mt-1">
                  When enabled, the bot simulates trades without executing real orders. Use this to validate your strategy before going live.
                </p>
              </div>
              <button
                type="button"
                onClick={() => setDryRun(!dryRun)}
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                  dryRun ? "bg-amber-500" : "bg-gray-700"
                }`}
              >
                <span
                  className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                    dryRun ? "translate-x-6" : "translate-x-1"
                  }`}
                />
              </button>
            </div>
            <div className={`mt-2 text-xs font-mono ${dryRun ? "text-amber-400" : "text-gray-600"}`}>
              {dryRun ? "✓ SIMULATION — No real trades will be executed" : "⚡ LIVE — Real trades will be executed"}
            </div>
          </div>

          {/* Risk & Filters */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
            <div className="flex flex-col gap-2">
              <label className="text-sm font-medium text-gray-400">Risk % per Trade</label>
              <input
                type="number"
                step="0.1"
                value={riskPerTrade}
                onChange={(e) => setRiskPerTrade(parseFloat(e.target.value))}
                className="bg-gray-800 border border-gray-700 p-3 rounded-lg focus:ring-2 focus:ring-green-500 text-gray-300 outline-none transition-all"
              />
            </div>
            <div className="flex flex-col gap-2">
              <label className="text-sm font-medium text-gray-400">Max Volume</label>
              <input
                type="number"
                step="0.01"
                value={maxVolume}
                onChange={(e) => setMaxVolume(parseFloat(e.target.value))}
                className="bg-gray-800 border border-gray-700 p-3 rounded-lg focus:ring-2 focus:ring-green-500 text-gray-300 outline-none transition-all"
              />
            </div>
            <div className="flex flex-col gap-2">
              <label className="text-sm font-medium text-gray-400">Max Spread (pts)</label>
              <input
                type="number"
                value={maxSpread}
                onChange={(e) => setMaxSpread(parseInt(e.target.value))}
                className="bg-gray-800 border border-gray-700 p-3 rounded-lg focus:ring-2 focus:ring-green-500 text-gray-300 outline-none transition-all"
              />
            </div>
          </div>

          {/* JSON Preview */}
          <div className="mb-6">
            <label className="text-[10px] uppercase tracking-wider text-gray-500 block mb-1.5">JSON Preview (auto-generated)</label>
            <pre className="bg-gray-900/60 border border-gray-700/50 rounded-lg p-3 text-xs text-gray-400 font-mono overflow-x-auto max-h-40">
              {JSON.stringify(buildEntryRules(), null, 2)}
            </pre>
          </div>

          {/* Actions */}
          <div className="flex justify-end gap-3">
            <button
              onClick={() => setShowBuilder(false)}
              className="text-xs text-gray-400 hover:text-white border border-gray-700 rounded-xl px-5 py-2.5 transition-all"
            >
              Cancel
            </button>
            <button
              onClick={handleSave}
              disabled={saving}
              className="text-xs font-bold text-emerald-400 border border-emerald-500/40 bg-emerald-500/10 hover:bg-emerald-500/20 rounded-xl px-5 py-2.5 transition-all glow-green disabled:opacity-30"
            >
              {saving ? "Saving..." : "Save Strategy"}
            </button>
          </div>
        </div>
      )}

      {/* Strategies List */}
      <div className="rounded-2xl border border-gray-800/50 bg-gray-950/40 overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="bg-gray-900/50">
              <th className="px-5 py-4 text-left text-[10px] font-semibold uppercase tracking-wider text-gray-500">Name</th>
              <th className="px-5 py-4 text-left text-[10px] font-semibold uppercase tracking-wider text-gray-500">Symbol</th>
              <th className="px-5 py-4 text-left text-[10px] font-semibold uppercase tracking-wider text-gray-500">Entry Rules</th>
              <th className="px-5 py-4 text-left text-[10px] font-semibold uppercase tracking-wider text-gray-500">Mode</th>
              <th className="px-5 py-4 text-left text-[10px] font-semibold uppercase tracking-wider text-gray-500">Status</th>
              <th className="px-5 py-4 text-left text-[10px] font-semibold uppercase tracking-wider text-gray-500">Action</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={6} className="text-center py-12 text-gray-600">
                  Loading strategies...
                </td>
              </tr>
            ) : strategies.length === 0 ? (
              <tr>
                <td colSpan={6} className="text-center py-12 text-gray-600">
                  <span className="text-4xl opacity-40 block mb-2">📊</span>
                  No strategies yet — click "New Strategy" to create one
                </td>
              </tr>
            ) : (
              strategies.map((strategy) => (
                <tr key={strategy.id} className="hover:bg-gray-900/30 transition-colors border-b border-gray-800/30">
                  <td className="px-5 py-4">
                    <div className="text-white font-semibold text-sm">{strategy.name}</div>
                    {strategy.description && (
                      <div className="text-gray-600 text-xs mt-0.5">{strategy.description}</div>
                    )}
                  </td>
                  <td className="px-5 py-4 text-cyan-400 font-mono text-xs">{strategy.symbol}</td>
                  <td className="px-5 py-4">
                    <pre className="text-xs text-gray-500 font-mono max-w-xs truncate">
                      {JSON.stringify(strategy.entry_rules)}
                    </pre>
                  </td>
                  <td className="px-5 py-4">
                    <span className={`inline-block px-2 py-0.5 rounded text-[10px] font-bold ${
                      strategy.dry_run
                        ? "bg-amber-500/15 text-amber-400 border border-amber-500/30"
                        : "bg-emerald-500/15 text-emerald-400 border border-emerald-500/30"
                    }`}>
                      {strategy.dry_run ? "🧪 DRY RUN" : "⚡ LIVE"}
                    </span>
                  </td>
                  <td className="px-5 py-4">
                    <span className={`inline-block px-2 py-0.5 rounded text-[10px] font-bold ${
                      strategy.is_active
                        ? "bg-emerald-500/15 text-emerald-400 border border-emerald-500/30"
                        : "bg-gray-700/30 text-gray-500 border border-gray-700/50"
                    }`}>
                      {strategy.is_active ? "ACTIVE" : "INACTIVE"}
                    </span>
                  </td>
                  <td className="px-5 py-4">
                    <button
                      onClick={() => toggleStrategy(strategy.id, strategy.is_active)}
                      className={`text-xs font-bold px-3 py-1.5 rounded-lg border transition-all ${
                        strategy.is_active
                          ? "text-rose-400 border-rose-500/40 bg-rose-500/10 hover:bg-rose-500/20"
                          : "text-emerald-400 border-emerald-500/40 bg-emerald-500/10 hover:bg-emerald-500/20"
                      }`}
                    >
                      {strategy.is_active ? "Deactivate" : "Activate"}
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
