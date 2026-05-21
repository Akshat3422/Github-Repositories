"use client";

import React, { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { 
  Github, LogOut, Search, Loader2, Sparkles, CheckCircle2, AlertTriangle, 
  HelpCircle, ChevronRight, Play, RefreshCw, Layers, Cpu, DollarSign
} from "lucide-react";
import { BrainCircuit } from "lucide-react";

interface Repo {
  id: string;
  name: string;
  full_name: string;
  description: string | null;
  html_url: string;
  pushed_at: string;
  language: string | null;
  stargazers_count: number;
}

interface Job {
  id: string;
  status: string;
  checkpoint: string;
  error_message: string | null;
  retry_count: number;
  input_tokens: number;
  output_tokens: number;
  model_used: Record<string, any>;
  repo_name?: string;
  repo_full_name?: string;
}

export default function Dashboard() {
  const router = useRouter();
  
  // Auth state
  const [userId, setUserId] = useState<string | null>(null);
  const [username, setUsername] = useState<string | null>(null);
  const [avatarUrl, setAvatarUrl] = useState<string | null>(null);

  // UI state
  const [repos, setRepos] = useState<Repo[]>([]);
  const [filteredRepos, setFilteredRepos] = useState<Repo[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [isLoadingRepos, setIsLoadingRepos] = useState(true);
  
  const [selectedRepo, setSelectedRepo] = useState<Repo | null>(null);
  const [bypassReadme, setBypassReadme] = useState(false);
  const [isTriggering, setIsTriggering] = useState(false);

  // Active Job states
  const [activeJob, setActiveJob] = useState<Job | null>(null);
  const [sseError, setSseError] = useState<string | null>(null);

  const backendUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  // Check auth
  useEffect(() => {
    const cachedUserId = localStorage.getItem("user_id");
    const cachedUsername = localStorage.getItem("username");
    const cachedAvatar = localStorage.getItem("avatar_url");

    if (!cachedUserId || !cachedUsername) {
      router.push("/");
    } else {
      setUserId(cachedUserId);
      setUsername(cachedUsername);
      setAvatarUrl(cachedAvatar);
    }
  }, [router]);

  // Load user repositories
  useEffect(() => {
    if (!userId) return;
    
    async function fetchRepos() {
      setIsLoadingRepos(true);
      try {
        const response = await fetch(`${backendUrl}/api/repos?user_id=${userId}`);
        if (!response.ok) {
          throw new Error("Failed to fetch repositories.");
        }
        const data = await response.json();
        setRepos(data);
        setFilteredRepos(data);
      } catch (err) {
        console.error(err);
      } finally {
        setIsLoadingRepos(false);
      }
    }

    fetchRepos();
  }, [userId, backendUrl]);

  // Search Filter
  useEffect(() => {
    if (!searchQuery) {
      setFilteredRepos(repos);
    } else {
      const q = searchQuery.toLowerCase();
      setFilteredRepos(
        repos.filter(
          (r) =>
            r.name.toLowerCase().includes(q) ||
            (r.description && r.description.toLowerCase().includes(q))
        )
      );
    }
  }, [searchQuery, repos]);

  // Listen to Active Job SSE Stream
  useEffect(() => {
    if (!activeJob?.id || activeJob.status === "done" || activeJob.status === "failed") return;

    const eventSource = new EventSource(`${backendUrl}/api/pipeline/status/${activeJob.id}/stream`);

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data) as Job;
        setActiveJob(data);
        
        if (data.status === "done" || data.status === "failed") {
          eventSource.close();
        }
      } catch (err) {
        console.error("SSE Parse Error:", err);
      }
    };

    eventSource.onerror = () => {
      setSseError("Lost connection to real-time status. Polling database instead...");
      eventSource.close();
    };

    return () => {
      eventSource.close();
    };
  }, [activeJob?.id, activeJob?.status, backendUrl]);

  // Fallback Polling if SSE fails
  useEffect(() => {
    if (!activeJob?.id || activeJob.status === "done" || activeJob.status === "failed" || !sseError) return;

    const interval = setInterval(async () => {
      try {
        const response = await fetch(`${backendUrl}/api/pipeline/status/${activeJob!.id}`);
        if (response.ok) {
          const data = await response.json() as Job;
          setActiveJob(data);
          if (data.status === "done" || data.status === "failed") {
            setSseError(null);
            clearInterval(interval);
          }
        }
      } catch (err) {
        console.error("Polling Error:", err);
      }
    }, 2000);

    return () => clearInterval(interval);
  }, [activeJob?.id, activeJob?.status, sseError, backendUrl]);

  // Trigger Pipeline
  const handleTriggerPipeline = async (bypass = false) => {
    if (!selectedRepo || !userId) return;

    setIsTriggering(true);
    setSseError(null);
    try {
      const response = await fetch(
        `${backendUrl}/api/pipeline/trigger?user_id=${userId}&bypass_warning=${bypass || bypassReadme}`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            repo_id: selectedRepo.id,
            repo_name: selectedRepo.name,
            repo_full_name: selectedRepo.full_name,
            repo_pushed_at: selectedRepo.pushed_at,
          }),
        }
      );

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Failed to trigger pipeline.");
      }

      const job = await response.json() as Job;
      setActiveJob({
        ...job,
        repo_name: selectedRepo.name,
        repo_full_name: selectedRepo.full_name
      });
    } catch (err: any) {
      alert(err.message || "An unexpected error occurred.");
    } finally {
      setIsTriggering(false);
    }
  };

  // Disconnect GitHub Account
  const handleDisconnect = async () => {
    if (!userId) return;
    
    const confirmDisc = confirm("Are you sure you want to disconnect? This deletes all your tokens and generated stories.");
    if (!confirmDisc) return;

    try {
      const response = await fetch(`${backendUrl}/api/auth/disconnect?user_id=${userId}`, {
        method: "POST",
      });
      if (response.ok) {
        localStorage.clear();
        router.push("/");
      }
    } catch (err) {
      console.error("Disconnect Error:", err);
    }
  };

  // Calculate pricing based on standard token pricing
  // Llama-3.1-8b: Input $0.05 / 1MT, Output $0.08 / 1MT
  // Llama-3.3-70b: Input $0.59 / 1MT, Output $0.79 / 1MT
  // We'll calculate a unified approximate cost
  const calculateCost = (input: number, output: number) => {
    const cost = (input * 0.0000005) + (output * 0.0000008); // general approx
    return cost.toFixed(5);
  };

  return (
    <div className="min-h-screen bg-black text-slate-100 flex flex-col">
      {/* Top Navbar */}
      <nav className="w-full max-w-7xl mx-auto px-6 py-4 flex justify-between items-center border-b border-slate-900 bg-black/50 backdrop-blur sticky top-0 z-20">
        <div className="flex items-center gap-2 cursor-pointer" onClick={() => router.push("/dashboard")}>
          <BrainCircuit className="h-6 w-6 text-violet-500" />
          <span className="text-lg font-bold bg-gradient-to-r from-white to-slate-400 bg-clip-text text-transparent">
            DevStory.AI
          </span>
        </div>
        
        {username && (
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2 bg-slate-950 p-1.5 pr-3.5 rounded-full border border-slate-800">
              {avatarUrl ? (
                <img src={avatarUrl} alt={username} className="w-7 h-7 rounded-full border border-slate-700" />
              ) : (
                <div className="w-7 h-7 rounded-full bg-violet-600 flex items-center justify-center text-xs uppercase font-bold">
                  {username[0]}
                </div>
              )}
              <span className="text-sm font-medium text-slate-300">@{username}</span>
            </div>
            <button 
              onClick={handleDisconnect}
              className="flex items-center gap-1.5 text-xs text-slate-500 hover:text-red-400 transition-all font-medium py-2 px-3 border border-dashed border-slate-800 hover:border-red-900 rounded-lg"
              title="Disconnect Account"
            >
              <LogOut className="h-3.5 w-3.5" />
              Disconnect
            </button>
          </div>
        )}
      </nav>

      {/* Main Container */}
      <div className="flex-1 max-w-7xl w-full mx-auto px-6 py-8 grid grid-cols-1 lg:grid-cols-12 gap-8">
        
        {/* Left Side: Repos List Selection (7 Columns) */}
        <div className="lg:col-span-7 flex flex-col gap-6">
          <div className="flex flex-col gap-1">
            <h2 className="text-2xl font-bold">Select a Repository</h2>
            <p className="text-sm text-slate-400">Choose a project to extract a LinkedIn story from.</p>
          </div>

          <div className="relative">
            <Search className="absolute left-3.5 top-3 h-4 w-4 text-slate-500" />
            <input 
              type="text" 
              placeholder="Search repositories..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 focus:border-violet-600 outline-none text-slate-300 pl-10 pr-4 py-2.5 rounded-xl text-sm transition-all shadow-inner"
            />
          </div>

          {isLoadingRepos ? (
            <div className="flex flex-col items-center justify-center py-20 gap-3">
              <Loader2 className="h-8 w-8 text-violet-500 animate-spin" />
              <p className="text-sm text-slate-500">Loading GitHub repositories...</p>
            </div>
          ) : filteredRepos.length === 0 ? (
            <div className="text-center py-16 border border-slate-900 rounded-2xl glass">
              <Github className="h-8 w-8 text-slate-600 mx-auto mb-3" />
              <h4 className="font-bold text-slate-300">No repositories found</h4>
              <p className="text-xs text-slate-500 mt-1">Try another search query or check permissions.</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-3 overflow-y-auto max-h-[500px] pr-1">
              {filteredRepos.map((repo) => {
                const isSelected = selectedRepo?.id === repo.id;
                return (
                  <div
                    key={repo.id}
                    onClick={() => {
                      if (activeJob?.status === "pending" || activeJob?.status === "running") return;
                      setSelectedRepo(repo);
                    }}
                    className={`p-4 rounded-xl border transition-all cursor-pointer flex flex-col justify-between ${
                      isSelected 
                        ? "bg-violet-950/20 border-violet-500 shadow-md shadow-violet-500/5" 
                        : "bg-slate-950/40 border-slate-900 hover:border-slate-800 hover:bg-slate-950/80"
                    } ${activeJob?.status === "running" ? "opacity-60 cursor-not-allowed" : ""}`}
                  >
                    <div className="flex justify-between items-start gap-4">
                      <div>
                        <div className="flex items-center gap-2">
                          <h3 className="font-bold text-base text-slate-200">{repo.name}</h3>
                          {repo.language && (
                            <span className="text-[10px] bg-slate-800 text-slate-300 font-medium px-2 py-0.5 rounded-full">
                              {repo.language}
                            </span>
                          )}
                        </div>
                        <p className="text-xs text-slate-400 mt-1 line-clamp-2 pr-4">{repo.description || "No description provided."}</p>
                      </div>
                      <div className="flex items-center gap-1 text-[11px] text-slate-500 bg-slate-900 px-2 py-1 rounded-md">
                        <span className="text-amber-500">★</span>
                        <span>{repo.stargazers_count}</span>
                      </div>
                    </div>
                    
                    <div className="flex justify-between items-center mt-3 pt-3 border-t border-slate-900/50 text-[10px] text-slate-500">
                      <span>Pushed: {new Date(repo.pushed_at).toLocaleDateString()}</span>
                      <span className="text-slate-400 font-mono text-[9px]">{repo.full_name}</span>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Right Side: Orchestrator Status Panel (5 Columns) */}
        <div className="lg:col-span-5 flex flex-col gap-6">
          <div className="p-6 rounded-2xl glass flex flex-col gap-6 sticky top-24">
            
            {/* Top Info */}
            <div className="flex flex-col gap-1">
              <h3 className="text-xl font-bold flex items-center gap-2">
                <Sparkles className="h-5 w-5 text-violet-400" />
                Pipeline Orchestrator
              </h3>
              <p className="text-xs text-slate-400">Configure parameters and run the multi-agent pipeline.</p>
            </div>

            {/* Selected Repo Card */}
            {selectedRepo ? (
              <div className="p-4 rounded-xl bg-slate-950 border border-slate-900 flex flex-col gap-3">
                <div>
                  <span className="text-[9px] uppercase tracking-wider text-slate-500 font-bold">Selected Repo</span>
                  <h4 className="font-bold text-slate-300 text-lg leading-tight mt-0.5">{selectedRepo.name}</h4>
                  <p className="text-[10px] text-slate-500 font-mono mt-0.5">{selectedRepo.full_name}</p>
                </div>

                {/* Overwrite / Warnings */}
                <div className="flex items-center gap-2.5 pt-2 border-t border-slate-900">
                  <input 
                    type="checkbox" 
                    id="bypassReadme"
                    checked={bypassReadme}
                    onChange={(e) => setBypassReadme(e.target.checked)}
                    className="h-4 w-4 bg-slate-900 border-slate-800 accent-violet-600 rounded cursor-pointer"
                    disabled={activeJob?.status === "running"}
                  />
                  <label htmlFor="bypassReadme" className="text-xs text-slate-400 cursor-pointer select-none">
                    Bypass missing README validation warnings
                  </label>
                </div>

                {/* Run Button */}
                {(!activeJob || activeJob.status === "done" || activeJob.status === "failed") && (
                  <button
                    onClick={() => handleTriggerPipeline(false)}
                    disabled={isTriggering}
                    className="w-full flex items-center justify-center gap-2.5 px-5 py-3 rounded-xl bg-violet-600 hover:bg-violet-500 text-white font-semibold text-sm transition-all duration-300 shadow-lg shadow-violet-600/20 active:scale-95 disabled:opacity-50"
                  >
                    {isTriggering ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <Play className="h-4 w-4 fill-white" />
                    )}
                    Generate LinkedIn Post Drafts
                  </button>
                )}
              </div>
            ) : (
              <div className="py-12 px-6 rounded-xl border border-dashed border-slate-800 text-center flex flex-col items-center justify-center gap-3">
                <HelpCircle className="h-8 w-8 text-slate-600" />
                <span className="text-sm text-slate-500 font-medium">Select a repository on the left to start.</span>
              </div>
            )}

            {/* Active Execution State */}
            {activeJob && (
              <div className="border-t border-slate-900 pt-5 flex flex-col gap-5">
                
                {/* Header state */}
                <div className="flex justify-between items-center">
                  <span className="text-xs font-bold uppercase tracking-wider text-slate-400">Execution Status</span>
                  <span className={`text-xs px-2.5 py-0.5 rounded-full font-bold uppercase tracking-wider ${
                    activeJob.status === "done" 
                      ? "bg-emerald-950/40 text-emerald-400 border border-emerald-900/30" 
                      : activeJob.status === "failed" 
                        ? "bg-red-950/40 text-red-400 border border-red-900/30" 
                        : "bg-violet-950/40 text-violet-400 border border-violet-900/30 animate-pulse"
                  }`}>
                    {activeJob.status}
                  </span>
                </div>

                {/* Progress Steps */}
                <div className="flex flex-col gap-3.5">
                  
                  {/* Step 1: Router */}
                  <div className="flex items-center justify-between text-xs">
                    <div className="flex items-center gap-2">
                      {activeJob.checkpoint !== "none" || activeJob.status === "done" ? (
                        <CheckCircle2 className="h-4 w-4 text-emerald-500" />
                      ) : activeJob.status === "failed" && activeJob.checkpoint === "none" ? (
                        <AlertTriangle className="h-4 w-4 text-red-500" />
                      ) : (
                        <Loader2 className="h-4 w-4 text-violet-500 animate-spin" />
                      )}
                      <span className={activeJob.checkpoint !== "none" || activeJob.status === "done" ? "text-slate-400" : "text-slate-200 font-bold"}>
                        1. Router Agent Validation
                      </span>
                    </div>
                    <span className="text-[10px] text-slate-600">llama-3.1-8b</span>
                  </div>

                  {/* Step 2: Agent 1 */}
                  <div className="flex items-center justify-between text-xs">
                    <div className="flex items-center gap-2">
                      {activeJob.checkpoint === "agent1" || activeJob.checkpoint === "agent2" || activeJob.checkpoint === "agent3" || activeJob.status === "done" ? (
                        <CheckCircle2 className="h-4 w-4 text-emerald-500" />
                      ) : activeJob.status === "failed" && activeJob.checkpoint === "none" ? (
                        <HelpCircle className="h-4 w-4 text-slate-700" />
                      ) : activeJob.checkpoint === "none" && activeJob.status === "running" ? (
                        <Loader2 className="h-4 w-4 text-violet-500 animate-spin" />
                      ) : (
                        <div className="h-4 w-4 rounded-full border-2 border-slate-800" />
                      )}
                      <span className={
                        (activeJob.checkpoint === "agent1" || activeJob.checkpoint === "agent2" || activeJob.checkpoint === "agent3" || activeJob.status === "done")
                          ? "text-slate-400" 
                          : (activeJob.checkpoint === "none" && activeJob.status === "running") 
                            ? "text-slate-200 font-bold" 
                            : "text-slate-600"
                      }>
                        2. Repo Intelligence (Agent 1)
                      </span>
                    </div>
                    <span className="text-[10px] text-slate-600">llama-3.1-8b</span>
                  </div>

                  {/* Step 3: Agent 2 */}
                  <div className="flex items-center justify-between text-xs">
                    <div className="flex items-center gap-2">
                      {activeJob.checkpoint === "agent2" || activeJob.checkpoint === "agent3" || activeJob.status === "done" ? (
                        <CheckCircle2 className="h-4 w-4 text-emerald-500" />
                      ) : activeJob.status === "failed" && (activeJob.checkpoint === "none" || activeJob.checkpoint === "agent1") ? (
                        <HelpCircle className="h-4 w-4 text-slate-700" />
                      ) : activeJob.checkpoint === "agent1" && activeJob.status === "running" ? (
                        <Loader2 className="h-4 w-4 text-violet-500 animate-spin" />
                      ) : (
                        <div className="h-4 w-4 rounded-full border-2 border-slate-800" />
                      )}
                      <span className={
                        (activeJob.checkpoint === "agent2" || activeJob.checkpoint === "agent3" || activeJob.status === "done")
                          ? "text-slate-400" 
                          : (activeJob.checkpoint === "agent1" && activeJob.status === "running") 
                            ? "text-slate-200 font-bold" 
                            : "text-slate-600"
                      }>
                        3. Insight Extraction (Agent 2)
                      </span>
                    </div>
                    <span className="text-[10px] text-slate-600">llama-3.3-70b</span>
                  </div>

                  {/* Step 4: Agent 3 */}
                  <div className="flex items-center justify-between text-xs">
                    <div className="flex items-center gap-2">
                      {activeJob.checkpoint === "agent3" || activeJob.status === "done" ? (
                        <CheckCircle2 className="h-4 w-4 text-emerald-500" />
                      ) : activeJob.status === "failed" && activeJob.checkpoint !== "agent2" ? (
                        <HelpCircle className="h-4 w-4 text-slate-700" />
                      ) : activeJob.checkpoint === "agent2" && activeJob.status === "running" ? (
                        <Loader2 className="h-4 w-4 text-violet-500 animate-spin" />
                      ) : (
                        <div className="h-4 w-4 rounded-full border-2 border-slate-800" />
                      )}
                      <span className={
                        (activeJob.checkpoint === "agent3" || activeJob.status === "done")
                          ? "text-slate-400" 
                          : (activeJob.checkpoint === "agent2" && activeJob.status === "running") 
                            ? "text-slate-200 font-bold" 
                            : "text-slate-600"
                      }>
                        4. LinkedIn Generation (Agent 3)
                      </span>
                    </div>
                    <span className="text-[10px] text-slate-600">llama-3.3-70b</span>
                  </div>
                </div>

                {/* Warnings / Errors / Override triggers */}
                {activeJob.status === "failed" && (
                  <div className="p-4 rounded-xl bg-red-950/20 border border-red-900/40 text-xs flex flex-col gap-2.5">
                    <div className="flex items-start gap-2">
                      <AlertTriangle className="h-4 w-4 text-red-400 shrink-0 mt-0.5" />
                      <div className="flex-1">
                        <span className="font-bold text-red-300">Analysis Halted</span>
                        <p className="text-red-400 mt-0.5 leading-relaxed">{activeJob.error_message}</p>
                      </div>
                    </div>

                    {/* Offer override button if the error is missing README */}
                    {activeJob.error_message?.toLowerCase().includes("readme") && (
                      <button
                        onClick={() => handleTriggerPipeline(true)}
                        className="w-full flex items-center justify-center gap-1.5 px-3 py-2 bg-red-950/60 hover:bg-red-900/50 text-red-200 rounded-lg font-bold border border-red-800/40 transition-all"
                      >
                        <RefreshCw className="h-3 w-3 animate-spin-slow" />
                        Bypass Warning & Force Re-Run
                      </button>
                    )}
                  </div>
                )}

                {/* Job Stats & Cost Metrics */}
                <div className="grid grid-cols-3 gap-2 bg-slate-950/70 p-3.5 rounded-xl border border-slate-900 text-center">
                  <div className="flex flex-col">
                    <span className="text-[9px] uppercase tracking-wider text-slate-500 font-bold flex items-center justify-center gap-1">
                      <Layers className="h-3 w-3" />
                      Tokens
                    </span>
                    <span className="text-sm font-bold text-slate-300 mt-1">
                      {(activeJob.input_tokens || 0) + (activeJob.output_tokens || 0)}
                    </span>
                  </div>
                  <div className="flex flex-col border-x border-slate-900">
                    <span className="text-[9px] uppercase tracking-wider text-slate-500 font-bold flex items-center justify-center gap-1">
                      <Cpu className="h-3 w-3" />
                      Retries
                    </span>
                    <span className="text-sm font-bold text-slate-300 mt-1">
                      {activeJob.retry_count || 0}/3
                    </span>
                  </div>
                  <div className="flex flex-col">
                    <span className="text-[9px] uppercase tracking-wider text-slate-500 font-bold flex items-center justify-center gap-1">
                      <DollarSign className="h-3 w-3" />
                      Job Cost
                    </span>
                    <span className="text-sm font-bold text-slate-300 mt-1">
                      ${calculateCost(activeJob.input_tokens || 0, activeJob.output_tokens || 0)}
                    </span>
                  </div>
                </div>

                {/* View Drafts button */}
                {activeJob.status === "done" && (
                  <button
                    onClick={() => router.push(`/drafts?job_id=${activeJob.id}`)}
                    className="w-full flex items-center justify-center gap-1.5 px-4 py-3 bg-gradient-to-r from-violet-600 to-fuchsia-600 hover:from-violet-500 hover:to-fuchsia-500 text-white rounded-xl font-bold text-sm transition-all shadow-lg shadow-violet-600/10 active:scale-95"
                  >
                    View Post Drafts
                    <ChevronRight className="h-4 w-4" />
                  </button>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
