"use client";

import React from "react";
import { Github, Sparkles, Code2, BrainCircuit, Share2, ShieldCheck } from "lucide-react";

export default function LandingPage() {
  const handleLogin = () => {
    const backendUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    window.location.href = `${backendUrl}/api/auth/login`;
  };

  return (
    <div className="relative min-h-screen flex flex-col justify-between overflow-hidden">
      {/* Header */}
      <header className="w-full max-w-7xl mx-auto px-6 py-6 flex justify-between items-center z-10">
        <div className="flex items-center gap-2">
          <BrainCircuit className="h-8 w-8 text-violet-500 animate-pulse" />
          <span className="text-xl font-bold bg-gradient-to-r from-white via-slate-200 to-slate-400 bg-clip-text text-transparent">
            DevStory.AI
          </span>
        </div>
        <button 
          onClick={handleLogin}
          className="flex items-center gap-2 px-5 py-2 rounded-lg bg-violet-600 hover:bg-violet-500 text-white font-medium text-sm transition-all duration-300 shadow-lg shadow-violet-500/20 active:scale-95"
        >
          <Github className="h-4 w-4" />
          Connect GitHub
        </button>
      </header>

      {/* Hero Section */}
      <main className="flex-1 flex flex-col items-center justify-center text-center px-6 py-12 max-w-4xl mx-auto z-10">
        <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full glass text-violet-400 text-xs font-semibold uppercase tracking-wider mb-8 animate-bounce">
          <Sparkles className="h-3.5 w-3.5" />
          Powered by Multi-Agent AI
        </div>
        
        <h1 className="text-5xl md:text-7xl font-extrabold tracking-tight mb-6 bg-gradient-to-b from-white to-slate-300 bg-clip-text text-transparent">
          Convert GitHub Repos Into
          <span className="block bg-gradient-to-r from-violet-400 via-fuchsia-400 to-blue-400 bg-clip-text text-transparent mt-2">
            LinkedIn Developer Stories
          </span>
        </h1>
        
        <p className="text-lg md:text-xl text-slate-400 max-w-2xl mb-10 leading-relaxed">
          Stop staring at blank drafts. Let our structured agent pipeline read your codebase, extract authentic engineering insights, and craft ready-to-publish posts.
        </p>

        <div className="flex flex-col sm:flex-row gap-4 mb-16 justify-center">
          <button 
            onClick={handleLogin}
            className="flex items-center justify-center gap-3 px-8 py-4 rounded-xl bg-gradient-to-r from-violet-600 to-fuchsia-600 hover:from-violet-500 hover:to-fuchsia-500 text-white font-semibold text-base transition-all duration-300 shadow-xl shadow-violet-600/35 hover:shadow-violet-600/50 hover:scale-[1.02] active:scale-95"
          >
            <Github className="h-5 w-5" />
            Get Started with GitHub OAuth
          </button>
        </div>

        {/* Feature Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 w-full mt-8">
          <div className="p-6 rounded-2xl glass glass-hover text-left transition-all duration-300">
            <div className="p-3 w-fit rounded-xl bg-violet-500/10 text-violet-400 mb-4">
              <Code2 className="h-6 w-6" />
            </div>
            <h3 className="text-lg font-bold mb-2">1. Connect & Select</h3>
            <p className="text-sm text-slate-400 leading-relaxed">
              Connect via read-only GitHub OAuth 2.0. Select any public or private repository you want to extract stories from.
            </p>
          </div>

          <div className="p-6 rounded-2xl glass glass-hover text-left transition-all duration-300">
            <div className="p-3 w-fit rounded-xl bg-fuchsia-500/10 text-fuchsia-400 mb-4">
              <BrainCircuit className="h-6 w-6" />
            </div>
            <h3 className="text-lg font-bold mb-2">2. Multi-Agent Pipeline</h3>
            <p className="text-sm text-slate-400 leading-relaxed">
              Our Router, Repo Intelligence, and Engineering Insight agents inspect code files, architectures, and patterns to extract grounded findings.
            </p>
          </div>

          <div className="p-6 rounded-2xl glass glass-hover text-left transition-all duration-300">
            <div className="p-3 w-fit rounded-xl bg-blue-500/10 text-blue-400 mb-4">
              <Share2 className="h-6 w-6" />
            </div>
            <h3 className="text-lg font-bold mb-2">3. Edit & Publish</h3>
            <p className="text-sm text-slate-400 leading-relaxed">
              Review and edit 3 tailored LinkedIn drafts: Technical Deep Dives, Builder Journeys, and Problem-Solution stories.
            </p>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="w-full max-w-7xl mx-auto px-6 py-8 border-t border-slate-900 flex flex-col md:flex-row justify-between items-center text-xs text-slate-500 z-10 gap-4">
        <div className="flex items-center gap-2">
          <ShieldCheck className="h-4 w-4 text-emerald-500" />
          <span>Read-only GitHub tokens are encrypted at rest and never logged.</span>
        </div>
        <div>
          <span>© {new Date().getFullYear()} DevStory.AI. All rights reserved.</span>
        </div>
      </footer>
    </div>
  );
}
