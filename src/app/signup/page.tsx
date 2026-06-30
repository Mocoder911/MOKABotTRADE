"use client";

import React, { useState } from "react";
import { supabase } from "@/lib/supabase-client";
import Link from "next/link";
import Image from "next/image";
import { useRouter } from "next/navigation";

export default function SignupPage() {
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const router = useRouter();

  async function handleSignup(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);

    if (password !== confirmPassword) {
      setError("Passwords do not match");
      setLoading(false);
      return;
    }

    if (password.length < 6) {
      setError("Password must be at least 6 characters");
      setLoading(false);
      return;
    }

    const { error } = await supabase.auth.signUp({
      email,
      password,
      options: {
        data: {
          full_name: fullName,
        },
      },
    });

    if (error) {
      setError(error.message);
      setLoading(false);
      return;
    }

    setSuccess(true);
    setLoading(false);
  }

  if (success) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-black px-4">
        <div className="w-full max-w-md">
          <div className="flex justify-center mb-8">
            <div className="flex items-center gap-3">
              <Image
                src="/mokabot-logo.png"
                alt="MokaBot"
                width={48}
                height={48}
                className="object-contain h-auto"
                priority
              />
              <span className="text-white font-bold text-2xl tracking-tight glow-white">
                Moka<span className="text-emerald-400 glow-green">Bot</span>
              </span>
            </div>
          </div>

          <div className="rounded-2xl border border-emerald-500/20 bg-gray-950/40 p-8 text-center">
            <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center">
              <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-emerald-400">
                <polyline points="20 6 9 17 4 12"></polyline>
              </svg>
            </div>
            <h2 className="text-xl font-bold text-white glow-white mb-2">
              Account Created
            </h2>
            <p className="text-sm text-gray-400 mb-2">
              Your account is pending admin approval.
            </p>
            <p className="text-xs text-gray-600 mb-6">
              You will receive an email once your account is activated.
            </p>
            <button
              onClick={() => router.push("/login")}
              className="text-cyan-400 hover:text-cyan-300 hover:glow-cyan text-sm font-medium transition-all"
            >
              Back to Login
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-black px-4">
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="flex justify-center mb-8">
          <div className="flex items-center gap-3">
            <Image
              src="/mokabot-logo.png"
              alt="MokaBot"
              width={48}
              height={48}
              className="object-contain h-auto"
              priority
            />
            <span className="text-white font-bold text-2xl tracking-tight glow-white">
              Moka<span className="text-emerald-400 glow-green">Bot</span>
            </span>
          </div>
        </div>

        {/* Card */}
        <div className="rounded-2xl border border-gray-800/50 bg-gray-950/40 p-8">
          <h1 className="text-2xl font-bold text-white glow-white text-center mb-2">
            Create Account
          </h1>
          <p className="text-sm text-gray-500 text-center mb-8">
            Sign up to join the trading platform
          </p>

          <form onSubmit={handleSignup} className="flex flex-col gap-5">
            <div>
              <label className="block text-[11px] uppercase tracking-[0.15em] text-gray-500 font-medium mb-2">
                Full Name
              </label>
              <input
                type="text"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                required
                placeholder="John Doe"
                className="w-full bg-gray-900/60 border border-gray-700/50 rounded-xl px-4 py-3 text-sm font-mono text-gray-300 
                focus:border-cyan-500/50 focus:text-cyan-400 focus:glow-cyan outline-none transition-all duration-200 placeholder:text-gray-700"
              />
            </div>

            <div>
              <label className="block text-[11px] uppercase tracking-[0.15em] text-gray-500 font-medium mb-2">
                Email
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                placeholder="your@email.com"
                className="w-full bg-gray-900/60 border border-gray-700/50 rounded-xl px-4 py-3 text-sm font-mono text-gray-300 
                focus:border-cyan-500/50 focus:text-cyan-400 focus:glow-cyan outline-none transition-all duration-200 placeholder:text-gray-700"
              />
            </div>

            <div>
              <label className="block text-[11px] uppercase tracking-[0.15em] text-gray-500 font-medium mb-2">
                Password
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                placeholder="••••••••"
                className="w-full bg-gray-900/60 border border-gray-700/50 rounded-xl px-4 py-3 text-sm font-mono text-gray-300 
                focus:border-cyan-500/50 focus:text-cyan-400 focus:glow-cyan outline-none transition-all duration-200 placeholder:text-gray-700"
              />
            </div>

            <div>
              <label className="block text-[11px] uppercase tracking-[0.15em] text-gray-500 font-medium mb-2">
                Confirm Password
              </label>
              <input
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                required
                placeholder="••••••••"
                className="w-full bg-gray-900/60 border border-gray-700/50 rounded-xl px-4 py-3 text-sm font-mono text-gray-300 
                focus:border-cyan-500/50 focus:text-cyan-400 focus:glow-cyan outline-none transition-all duration-200 placeholder:text-gray-700"
              />
            </div>

            {error && (
              <div className="bg-rose-500/10 border border-rose-500/20 rounded-xl px-4 py-3 text-rose-400 text-sm">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full mt-2 bg-emerald-500/20 border border-emerald-500/40 text-emerald-400 font-bold py-3 rounded-xl
              hover:bg-emerald-500/30 hover:glow-green transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? "Creating Account..." : "Sign Up"}
            </button>
          </form>

          <div className="mt-6 text-center text-sm text-gray-500">
            Already have an account?{" "}
            <Link
              href="/login"
              className="text-cyan-400 hover:text-cyan-300 hover:glow-cyan transition-all"
            >
              Sign In
            </Link>
          </div>
        </div>

        <p className="text-center text-xs text-gray-700 mt-6">
          Secured by Supabase Auth
        </p>
      </div>
    </div>
  );
}
