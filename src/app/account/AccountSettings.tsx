"use client";

import React, { useState, useEffect, useRef } from "react";
import { useAuth } from "@/contexts/AuthContext";

export default function AccountSettings() {
  const { profile, refreshProfile } = useAuth();
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);
  const initialized = useRef(false);

  // Form state
  const [fullName, setFullName] = useState("");
  const [mt5AccountId, setMt5AccountId] = useState("");
  const [mt5Password, setMt5Password] = useState("");
  const [mt5Server, setMt5Server] = useState("");
  const [avatarUrl, setAvatarUrl] = useState("");
  const [uploading, setUploading] = useState(false);

  // Load profile data ONLY ONCE when component mounts
  useEffect(() => {
    if (profile && !initialized.current) {
      initialized.current = true;
      setFullName(profile.full_name || "");
      setMt5AccountId(profile.mt5_account_id || "");
      setMt5Password(profile.mt5_password || "");
      setMt5Server(profile.mt5_server || "");
      setAvatarUrl(profile.avatar_url || "");
    }
  }, [profile]);

  // Handle avatar upload to Supabase Storage
  const handleAvatarUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !profile) return;

    // Check file size (max 2MB)
    if (file.size > 2 * 1024 * 1024) {
      setMessage({ type: "error", text: "Image must be less than 2MB" });
      return;
    }

    // Check file type
    if (!file.type.startsWith("image/")) {
      setMessage({ type: "error", text: "Please select an image file" });
      return;
    }

    setUploading(true);
    try {
      // Upload to Supabase Storage
      const fileExt = file.name.split('.').pop();
      const fileName = `${profile.id}-${Date.now()}.${fileExt}`;
      const filePath = `avatars/${fileName}`;

      const { supabase } = await import("@/lib/supabase-client");
      
      const { error: uploadError } = await supabase.storage
        .from('avatars')
        .upload(filePath, file, { upsert: true });

      if (uploadError) throw uploadError;

      // Get public URL
      const { data: { publicUrl } } = supabase.storage
        .from('avatars')
        .getPublicUrl(filePath);

      setAvatarUrl(publicUrl);
      setMessage({ type: "success", text: "Image uploaded! Click Save to apply." });
    } catch (err) {
      console.error("Upload error:", err);
      setMessage({ type: "error", text: "Failed to upload image" });
    } finally {
      setUploading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!profile) return;

    setSaving(true);
    setMessage(null);

    try {
      const res = await fetch("/api/profiles", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          id: profile.id,
          full_name: fullName,
          mt5_account_id: mt5AccountId || null,
          mt5_password: mt5Password || null,
          mt5_server: mt5Server || null,
          avatar_url: avatarUrl || "",
        }),
      });

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.error || `HTTP ${res.status}`);
      }

      await refreshProfile();
      setMessage({ type: "success", text: "Profile updated successfully! Reloading..." });
      setTimeout(() => {
        window.location.reload();
      }, 1000);
    } catch (err) {
      setMessage({ type: "error", text: err instanceof Error ? err.message : "Failed to update profile" });
    } finally {
      setSaving(false);
    }
  };

  if (!profile) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="w-8 h-8 border-2 border-gray-700 border-t-cyan-500 rounded-full animate-spin"></div>
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-white glow-white">Account Settings</h1>
        <p className="text-sm text-gray-500 mt-1.5">Manage your profile and MT5 connection</p>
      </div>

      {/* Message */}
      {message && (
        <div
          className={`mb-6 px-4 py-3 rounded-xl border text-sm ${
            message.type === "success"
              ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-400"
              : "bg-rose-500/10 border-rose-500/30 text-rose-400"
          }`}
        >
          {message.text}
        </div>
      )}

      {/* Profile Picture Section */}
      <div className="bg-gray-900/30 border border-gray-800/50 rounded-2xl p-6 mb-6">
        <h2 className="text-lg font-semibold text-white mb-4">Profile Picture</h2>
        <div className="flex items-center gap-6">
          {/* Avatar Preview */}
          <div className="w-24 h-24 rounded-full bg-gray-800 border-2 border-gray-700 overflow-hidden flex items-center justify-center">
            {avatarUrl ? (
              <img
                src={avatarUrl}
                alt="Profile"
                className="w-full h-full object-cover"
              />
            ) : (
              <span className="text-3xl text-gray-600">
                {fullName ? fullName.charAt(0).toUpperCase() : "?"}
              </span>
            )}
          </div>
          <div className="flex-1">
            <label className="block text-xs uppercase tracking-wider text-gray-500 mb-2">
              Upload Avatar
            </label>
            <label className="flex items-center gap-2 px-4 py-2.5 bg-gray-800/50 border border-gray-700 rounded-xl text-white text-sm cursor-pointer hover:border-cyan-500/50 transition-colors">
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-gray-400">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                <polyline points="17 8 12 3 7 8" />
                <line x1="12" y1="3" x2="12" y2="15" />
              </svg>
              <span>{uploading ? "Loading..." : "Choose Image"}</span>
              <input
                type="file"
                accept="image/*"
                onChange={handleAvatarUpload}
                className="hidden"
                disabled={uploading}
              />
            </label>
            <p className="text-xs text-gray-600 mt-1">Max 2MB • JPG, PNG, GIF</p>
          </div>
        </div>
      </div>

      {/* Profile Form */}
      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Personal Info */}
        <div className="bg-gray-900/30 border border-gray-800/50 rounded-2xl p-6">
          <h2 className="text-lg font-semibold text-white mb-4">Personal Information</h2>
          <div className="space-y-4">
            <div>
              <label className="block text-xs uppercase tracking-wider text-gray-500 mb-2">
                Full Name
              </label>
              <input
                type="text"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                className="w-full px-4 py-2.5 bg-gray-800/50 border border-gray-700 rounded-xl text-white text-sm placeholder-gray-600 focus:outline-none focus:border-cyan-500/50 transition-colors"
              />
            </div>
            <div>
              <label className="block text-xs uppercase tracking-wider text-gray-500 mb-2">
                Email
              </label>
              <input
                type="email"
                value={profile.email}
                disabled
                className="w-full px-4 py-2.5 bg-gray-800/30 border border-gray-800 rounded-xl text-gray-500 text-sm cursor-not-allowed"
              />
              <p className="text-xs text-gray-600 mt-1">Email cannot be changed</p>
            </div>
          </div>
        </div>

        {/* MT5 Connection */}
        <div className="bg-gray-900/30 border border-gray-800/50 rounded-2xl p-6">
          <h2 className="text-lg font-semibold text-white mb-4">MT5 Connection</h2>
          <div className="space-y-4">
            <div>
              <label className="block text-xs uppercase tracking-wider text-gray-500 mb-2">
                MT5 Account ID
              </label>
              <input
                type="text"
                value={mt5AccountId}
                onChange={(e) => setMt5AccountId(e.target.value)}
                placeholder="12345678"
                className="w-full px-4 py-2.5 bg-gray-800/50 border border-gray-700 rounded-xl text-white text-sm font-mono placeholder-gray-600 focus:outline-none focus:border-cyan-500/50 transition-colors"
              />
            </div>
            <div>
              <label className="block text-xs uppercase tracking-wider text-gray-500 mb-2">
                MT5 Password
              </label>
              <input
                type="password"
                value={mt5Password}
                onChange={(e) => setMt5Password(e.target.value)}
                placeholder="••••••••"
                className="w-full px-4 py-2.5 bg-gray-800/50 border border-gray-700 rounded-xl text-white text-sm placeholder-gray-600 focus:outline-none focus:border-cyan-500/50 transition-colors"
              />
            </div>
            <div>
              <label className="block text-xs uppercase tracking-wider text-gray-500 mb-2">
                MT5 Server
              </label>
              <select
                value={mt5Server}
                onChange={(e) => setMt5Server(e.target.value)}
                className="w-full px-4 py-2.5 bg-gray-800/50 border border-gray-700 rounded-xl text-white text-sm focus:outline-none focus:border-cyan-500/50 transition-colors"
              >
                <option value="">Select server...</option>
                <option value="Exness-MT5Real">Exness-MT5Real</option>
                <option value="Exness-MT5Real2">Exness-MT5Real2</option>
                <option value="Exness-MT5Real3">Exness-MT5Real3</option>
                <option value="Exness-MT5Real4">Exness-MT5Real4</option>
                <option value="Exness-MT5Real5">Exness-MT5Real5</option>
                <option value="Exness-MT5Trial">Exness-MT5Trial</option>
              </select>
            </div>
          </div>
        </div>

        {/* Account Status */}
        <div className="bg-gray-900/30 border border-gray-800/50 rounded-2xl p-6">
          <h2 className="text-lg font-semibold text-white mb-4">Account Status</h2>
          <div className="grid grid-cols-3 gap-4">
            <div>
              <span className="block text-xs uppercase tracking-wider text-gray-500 mb-1">Role</span>
              <span className="text-sm font-medium text-white capitalize">{profile.role}</span>
            </div>
            <div>
              <span className="block text-xs uppercase tracking-wider text-gray-500 mb-1">Status</span>
              <span className={`text-sm font-medium capitalize ${
                profile.status === "active" ? "text-emerald-400" : "text-amber-400"
              }`}>
                {profile.status}
              </span>
            </div>
            <div>
              <span className="block text-xs uppercase tracking-wider text-gray-500 mb-1">Verification</span>
              <span className={`text-sm font-medium ${
                profile.verification_status === "VALIDATED" ? "text-emerald-400" : "text-amber-400"
              }`}>
                {profile.verification_status || "PENDING"}
              </span>
            </div>
          </div>
        </div>

        {/* Submit Button */}
        <button
          type="submit"
          disabled={saving}
          className="w-full py-3 px-6 bg-cyan-500/20 hover:bg-cyan-500/30 border border-cyan-500/50 text-cyan-400 font-semibold rounded-xl transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed glow-cyan"
        >
          {saving ? "Saving..." : "Save Changes"}
        </button>
      </form>
    </div>
  );
}
