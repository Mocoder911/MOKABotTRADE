// ─── Exness MT5 Account Configuration ─────────────────────────────────────────
// These credentials are used for SDK/API tracking with the Exness MT5 backend.
// ⚠️  Never commit this file to a public repository.

export const EXNESS_CONFIG = {
  /** Broker / Server identifier */
  broker: "Exness-MT5Trial15",

  /** Trading account number */
  accountNumber: "260904217",

  /** Account password (MT5 platform) */
  password: "Kikokok3@",
} as const;

export type ExnessConfig = typeof EXNESS_CONFIG;
