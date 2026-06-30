"use client";

import React, { useState, Suspense } from "react";
import { supabase } from "@/lib/supabase-client";
import Link from "next/link";
import Image from "next/image";
import { useRouter, useSearchParams } from "next/navigation";

export default function LoginPage() {
  return (
    <Suspense fallback={<div className="min-h-screen flex items-center justify-center bg-black"><div className="w-7 h-7 border-2 border-gray-700 border-t-cyan-500 rounded-full animate-spin"></div></div>}>
      <LoginForm />
    </Suspense>
  );
}

function LoginForm() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();
  const searchParams = useSearchParams();
  const redirect = searchParams.get("redirect") || "/";

  async function handleLogin(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);

    const { error } = await supabase.auth.signInWithPassword({
      email,
      password,
    });

    if (error) {
      setError(error.message);
      setLoading(false);
      return;
    }

    // Full page reload to sync auth state with middleware
    window.location.href = redirect;
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
            Welcome Back
          </h1>
          <p className="text-sm text-gray-500 text-center mb-8">
            Sign in to access your trading dashboard
          </p>

          <form onSubmit={handleLogin} className="flex flex-col gap-5">
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
              {loading ? "Signing in..." : "Sign In"}
            </button>
          </form>

          <div className="mt-6 text-center text-sm text-gray-500">
            Don&apos;t have an account?{" "}
            <Link
              href="/signup"
              className="text-cyan-400 hover:text-cyan-300 hover:glow-cyan transition-all"
            >
              Sign Up
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
