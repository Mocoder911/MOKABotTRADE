"use client";

import React, { useEffect, useState, useCallback } from "react";

// ─── Types ────────────────────────────────────────────────────────────────────
interface Profile {
  id: string;
  email: string;
  full_name: string;
  role: "admin" | "user";
  status: "pending" | "active" | "suspended";
  mt5_account_id?: string;
  mt5_server?: string;
  bot_active?: boolean;
  created_at: string;
}

interface NewUserForm {
  email: string;
  password: string;
  full_name: string;
  role: "admin" | "user";
  status: "pending" | "active" | "suspended";
  mt5_account_id: string;
  mt5_password: string;
  mt5_server: string;
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

// ─── Status Badge ─────────────────────────────────────────────────────────────
function StatusBadge({ status }: { status: string }) {
  const styles = {
    active: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30 glow-green",
    pending: "bg-amber-500/15 text-amber-400 border-amber-500/30",
    suspended: "bg-rose-500/15 text-rose-400 border-rose-500/30 glow-rose",
  };
  return (
    <span className={`inline-block px-2.5 py-1 rounded-lg text-[11px] font-bold border ${styles[status as keyof typeof styles] || styles.pending}`}>
      {status}
    </span>
  );
}

// ─── Neon Select ──────────────────────────────────────────────────────────────
function NeonSelect({
  value,
  onChange,
  options,
  accent = "cyan",
}: {
  value: string;
  onChange: (val: string) => void;
  options: { value: string; label: string }[];
  accent?: "cyan" | "green";
}) {
  const borderFocus =
    accent === "cyan"
      ? "focus:border-cyan-500/50"
      : "focus:border-emerald-500/50";
  const textFocus =
    accent === "cyan" ? "focus:text-cyan-400" : "focus:text-emerald-400";

  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className={`bg-gray-900/60 border border-gray-700/50 rounded-lg px-3 py-1.5 text-xs font-mono text-gray-300 
      ${borderFocus} ${textFocus} outline-none transition-all duration-200 cursor-pointer`}
    >
      {options.map((opt) => (
        <option key={opt.value} value={opt.value}>
          {opt.label}
        </option>
      ))}
    </select>
  );
}

// ─── Neon Input (for modal) ───────────────────────────────────────────────────
function FormInput({
  label,
  value,
  onChange,
  type = "text",
  placeholder = "",
  required = false,
}: {
  label: string;
  value: string;
  onChange: (val: string) => void;
  type?: string;
  placeholder?: string;
  required?: boolean;
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <label className="text-[10px] uppercase tracking-[0.2em] text-gray-500 font-medium">
        {label} {required && <span className="text-rose-400">*</span>}
      </label>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="bg-gray-900/60 border border-gray-700/50 rounded-lg px-3 py-2 text-sm font-mono text-gray-300 
        focus:border-cyan-500/50 focus:text-cyan-400 outline-none transition-all duration-200"
      />
    </div>
  );
}

// ─── User Management Component ────────────────────────────────────────────────
export default function UserManagement() {
  const [profiles, setProfiles] = useState<Profile[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [edits, setEdits] = useState<Record<string, { role: string; status: string }>>({});

  // Add User Modal state
  const [showAddModal, setShowAddModal] = useState(false);
  const [addingUser, setAddingUser] = useState(false);
  const [newUser, setNewUser] = useState<NewUserForm>({
    email: "",
    password: "",
    full_name: "",
    role: "user",
    status: "active",
    mt5_account_id: "",
    mt5_password: "",
    mt5_server: "",
  });

  const fetchProfiles = useCallback(async () => {
    try {
      const res = await fetch("/api/profiles");
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const json = await res.json();
      setProfiles(json.data);
      // Initialize edits
      const initial: Record<string, { role: string; status: string }> = {};
      json.data.forEach((p: Profile) => {
        initial[p.id] = { role: p.role, status: p.status };
      });
      setEdits(initial);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch profiles");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchProfiles();
  }, [fetchProfiles]);

  const handleSave = async (profileId: string) => {
    setSaving(profileId);
    const values = edits[profileId];
    try {
      const res = await fetch("/api/profiles", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          id: profileId,
          role: values.role,
          status: values.status,
        }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);

      // Update local state
      setProfiles((prev) =>
        prev.map((p) =>
          p.id === profileId
            ? { ...p, role: values.role as Profile["role"], status: values.status as Profile["status"] }
            : p
        )
      );

      // Show success notification
      setSuccessMsg(`Profile updated successfully`);
      setTimeout(() => setSuccessMsg(null), 3000);
    } catch (err) {
      console.error("Save failed:", err);
    } finally {
      setSaving(null);
    }
  };

  const handleAddUser = async () => {
    if (!newUser.email || !newUser.password || !newUser.full_name) {
      setError("Email, password, and full name are required");
      return;
    }

    setAddingUser(true);
    setError(null);

    try {
      const res = await fetch("/api/profiles", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(newUser),
      });

      if (!res.ok) {
        const json = await res.json();
        throw new Error(json.error || `HTTP ${res.status}`);
      }

      // Success
      setSuccessMsg(`User "${newUser.full_name}" created successfully`);
      setTimeout(() => setSuccessMsg(null), 3000);

      // Reset form and close modal
      setShowAddModal(false);
      setNewUser({
        email: "",
        password: "",
        full_name: "",
        role: "user",
        status: "active",
        mt5_account_id: "",
        mt5_password: "",
        mt5_server: "",
      });

      // Refresh profiles list
      fetchProfiles();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create user");
    } finally {
      setAddingUser(false);
    }
  };

  const hasChanges = (profileId: string) => {
    const profile = profiles.find((p) => p.id === profileId);
    const edit = edits[profileId];
    if (!profile || !edit) return false;
    return profile.role !== edit.role || profile.status !== edit.status;
  };

  return (
    <div className="max-w-[1400px] mx-auto flex flex-col gap-8">
      {/* ─── Header ───────────────────────────────────────────────────────── */}
      <div className="flex items-end justify-between pt-2">
        <div>
          <h1 className="text-2xl font-bold text-white glow-white">
            User Management
          </h1>
          <p className="text-sm text-gray-500 mt-1.5">
            Manage user roles and access &bull; Admin only
          </p>
        </div>
        <div className="flex items-center gap-3">
          {/* Add User Button */}
          <button
            onClick={() => setShowAddModal(true)}
            className="flex items-center gap-2 text-xs font-bold text-emerald-400 hover:text-emerald-300 border border-emerald-500/40 hover:border-emerald-500/60 bg-emerald-500/10 hover:bg-emerald-500/20 rounded-xl px-4 py-2 transition-all duration-200 glow-green"
          >
            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="12" y1="5" x2="12" y2="19"></line>
              <line x1="5" y1="12" x2="19" y2="12"></line>
            </svg>
            Add User
          </button>
          <button
            onClick={fetchProfiles}
            disabled={loading}
            className="text-xs font-medium text-gray-400 hover:text-white border border-gray-700 hover:border-gray-500 rounded-xl px-4 py-2 transition-all duration-200 disabled:opacity-30 bg-gray-900/30"
          >
            {loading ? "Loading..." : "Refresh"}
          </button>
        </div>
      </div>

      {/* ─── Success Notification ─────────────────────────────────────────── */}
      {successMsg && (
        <div className="bg-emerald-500/10 border border-emerald-500/30 rounded-2xl px-5 py-3 text-emerald-400 text-sm glow-green animate-pulse">
          ✓ {successMsg}
        </div>
      )}

      {/* ─── Error State ──────────────────────────────────────────────────── */}
      {error && (
        <div className="bg-rose-500/10 border border-rose-500/20 rounded-2xl px-5 py-4 text-rose-400 text-sm">
          <span className="font-bold">Error:</span> {error}
        </div>
      )}

      {/* ─── Profiles Table ───────────────────────────────────────────────── */}
      <div className="overflow-x-auto rounded-2xl border border-gray-800/50 bg-gray-950/40">
        <table className="w-full min-w-[1100px]">
          <thead>
            <tr className="bg-gray-900/50">
              <Th>Full Name</Th>
              <Th>Email</Th>
              <Th>MT5 Account</Th>
              <Th>MT5 Server</Th>
              <Th>Role</Th>
              <Th>Status</Th>
              <Th>Joined</Th>
              <Th>Action</Th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={8} className="text-center py-20 text-gray-600">
                  <div className="flex flex-col items-center gap-3">
                    <div className="w-7 h-7 border-2 border-gray-700 border-t-cyan-500 rounded-full animate-spin"></div>
                    <span className="text-sm text-gray-500">Loading users...</span>
                  </div>
                </td>
              </tr>
            ) : profiles.length === 0 ? (
              <tr>
                <td colSpan={8} className="text-center py-20 text-gray-600">
                  <div className="flex flex-col items-center gap-3">
                    <span className="text-5xl opacity-40">👥</span>
                    <span className="text-sm text-gray-500">No users found</span>
                  </div>
                </td>
              </tr>
            ) : (
              profiles.map((profile) => (
                <tr
                  key={profile.id}
                  className="hover:bg-gray-900/30 transition-colors duration-150"
                >
                  <Td className="text-white font-semibold">{profile.full_name}</Td>
                  <Td className="text-gray-400">{profile.email}</Td>
                  <Td className="text-cyan-400 font-mono text-xs">{profile.mt5_account_id || "—"}</Td>
                  <Td className="text-gray-500 font-mono text-xs">{profile.mt5_server || "—"}</Td>
                  <Td>
                    <NeonSelect
                      value={edits[profile.id]?.role ?? profile.role}
                      onChange={(val) =>
                        setEdits((prev) => ({
                          ...prev,
                          [profile.id]: { ...prev[profile.id], role: val },
                        }))
                      }
                      options={[
                        { value: "admin", label: "Admin" },
                        { value: "user", label: "User" },
                      ]}
                      accent="cyan"
                    />
                  </Td>
                  <Td>
                    <div className="flex items-center gap-2">
                      <NeonSelect
                        value={edits[profile.id]?.status ?? profile.status}
                        onChange={(val) =>
                          setEdits((prev) => ({
                            ...prev,
                            [profile.id]: { ...prev[profile.id], status: val },
                          }))
                        }
                        options={[
                          { value: "pending", label: "Pending" },
                          { value: "active", label: "Active" },
                          { value: "suspended", label: "Suspended" },
                        ]}
                        accent="green"
                      />
                      <StatusBadge status={edits[profile.id]?.status ?? profile.status} />
                    </div>
                  </Td>
                  <Td className="text-gray-600 text-xs">
                    {new Date(profile.created_at).toLocaleDateString()}
                  </Td>
                  <Td>
                    <button
                      onClick={() => handleSave(profile.id)}
                      disabled={saving === profile.id || !hasChanges(profile.id)}
                      className={`text-xs font-bold px-4 py-2 rounded-lg border transition-all duration-200 
                        ${
                          hasChanges(profile.id)
                            ? "text-emerald-400 border-emerald-500/40 bg-emerald-500/10 hover:bg-emerald-500/20 glow-green"
                            : "text-gray-600 border-gray-700/50 bg-gray-900/30 cursor-not-allowed"
                        }`}
                    >
                      {saving === profile.id ? "Saving..." : "Save"}
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
          <span className="text-cyan-400/60">●</span> Changes sync immediately to Supabase
        </span>
        <span className="font-mono">
          {profiles.length} user{profiles.length !== 1 ? "s" : ""} registered
        </span>
      </div>

      {/* ─── Add User Modal ───────────────────────────────────────────────── */}
      {showAddModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm">
          <div className="w-full max-w-lg mx-4 rounded-2xl border border-gray-700/50 bg-[#0f1419] shadow-2xl">
            {/* Modal Header */}
            <div className="flex items-center justify-between px-6 py-4 border-b border-gray-800/50">
              <h2 className="text-lg font-bold text-white glow-white">Add New User</h2>
              <button
                onClick={() => setShowAddModal(false)}
                className="text-gray-500 hover:text-white transition-colors"
              >
                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <line x1="18" y1="6" x2="6" y2="18"></line>
                  <line x1="6" y1="6" x2="18" y2="18"></line>
                </svg>
              </button>
            </div>

            {/* Modal Body */}
            <div className="px-6 py-5 flex flex-col gap-5">
              {/* Account Info */}
              <div className="flex flex-col gap-3">
                <span className="text-[10px] uppercase tracking-[0.2em] text-cyan-400/60 font-bold">Account Info</span>
                <div className="grid grid-cols-2 gap-3">
                  <div className="col-span-2">
                    <FormInput
                      label="Full Name"
                      value={newUser.full_name}
                      onChange={(val) => setNewUser((prev) => ({ ...prev, full_name: val }))}
                      placeholder="John Doe"
                      required
                    />
                  </div>
                  <FormInput
                    label="Email"
                    value={newUser.email}
                    onChange={(val) => setNewUser((prev) => ({ ...prev, email: val }))}
                    type="email"
                    placeholder="user@example.com"
                    required
                  />
                  <FormInput
                    label="Password"
                    value={newUser.password}
                    onChange={(val) => setNewUser((prev) => ({ ...prev, password: val }))}
                    type="password"
                    placeholder="Min 6 characters"
                    required
                  />
                </div>
              </div>

              {/* Role & Status */}
              <div className="flex flex-col gap-3">
                <span className="text-[10px] uppercase tracking-[0.2em] text-cyan-400/60 font-bold">Access</span>
                <div className="grid grid-cols-2 gap-3">
                  <div className="flex flex-col gap-1.5">
                    <label className="text-[10px] uppercase tracking-[0.2em] text-gray-500 font-medium">Role</label>
                    <NeonSelect
                      value={newUser.role}
                      onChange={(val) => setNewUser((prev) => ({ ...prev, role: val as "admin" | "user" }))}
                      options={[
                        { value: "user", label: "User" },
                        { value: "admin", label: "Admin" },
                      ]}
                      accent="cyan"
                    />
                  </div>
                  <div className="flex flex-col gap-1.5">
                    <label className="text-[10px] uppercase tracking-[0.2em] text-gray-500 font-medium">Status</label>
                    <NeonSelect
                      value={newUser.status}
                      onChange={(val) => setNewUser((prev) => ({ ...prev, status: val as "pending" | "active" | "suspended" }))}
                      options={[
                        { value: "active", label: "Active" },
                        { value: "pending", label: "Pending" },
                        { value: "suspended", label: "Suspended" },
                      ]}
                      accent="green"
                    />
                  </div>
                </div>
              </div>

              {/* Exness MT5 */}
              <div className="flex flex-col gap-3">
                <span className="text-[10px] uppercase tracking-[0.2em] text-emerald-400/60 font-bold">Exness MT5</span>
                <div className="grid grid-cols-2 gap-3">
                  <FormInput
                    label="MT5 Account ID"
                    value={newUser.mt5_account_id}
                    onChange={(val) => setNewUser((prev) => ({ ...prev, mt5_account_id: val }))}
                    placeholder="260904217"
                  />
                  <FormInput
                    label="MT5 Server"
                    value={newUser.mt5_server}
                    onChange={(val) => setNewUser((prev) => ({ ...prev, mt5_server: val }))}
                    placeholder="Exness-MT5Trial15"
                  />
                  <div className="col-span-2">
                    <FormInput
                      label="MT5 Password"
                      value={newUser.mt5_password}
                      onChange={(val) => setNewUser((prev) => ({ ...prev, mt5_password: val }))}
                      type="password"
                      placeholder="Trading password"
                    />
                  </div>
                </div>
              </div>
            </div>

            {/* Modal Footer */}
            <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-gray-800/50">
              <button
                onClick={() => setShowAddModal(false)}
                className="text-xs font-medium text-gray-400 hover:text-white border border-gray-700 hover:border-gray-500 rounded-xl px-5 py-2.5 transition-all duration-200"
              >
                Cancel
              </button>
              <button
                onClick={handleAddUser}
                disabled={addingUser}
                className="text-xs font-bold text-emerald-400 border border-emerald-500/40 bg-emerald-500/10 hover:bg-emerald-500/20 rounded-xl px-5 py-2.5 transition-all duration-200 glow-green disabled:opacity-30"
              >
                {addingUser ? "Creating..." : "Create User"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
