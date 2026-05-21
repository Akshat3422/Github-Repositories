"use client";

import React, { useState, useEffect, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { 
  ArrowLeft, Copy, Check, Save, FileDown, Loader2, Sparkles, Code2, 
  BookOpen, Star, HelpCircle
} from "lucide-react";
import confetti from "canvas-confetti";
import { BrainCircuit } from "lucide-react";

interface Post {
  style: string;
  content: string;
}

interface Job {
  id: string;
  repo_name: string;
  repo_full_name: string;
  agent3_output: {
    posts: Post[];
  };
  agent1_output: {
    tech_stack: string[];
    architecture: string;
    complexity: string;
  };
}

function DraftsContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const jobId = searchParams.get("job_id");

  const [job, setJob] = useState<Job | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [activeTab, setActiveTab] = useState(0);
  
  // Editing state
  const [editContent, setEditContent] = useState("");
  const [isSaving, setIsSaving] = useState(false);
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null);

  const backendUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  // Load Job details
  useEffect(() => {
    if (!jobId) {
      router.push("/dashboard");
      return;
    }

    async function fetchJob() {
      setIsLoading(true);
      try {
        const response = await fetch(`${backendUrl}/api/pipeline/status/${jobId}`);
        if (!response.ok) {
          throw new Error("Failed to fetch job drafts.");
        }
        const data = (await response.json()) as Job;
        setJob(data);
        if (data.agent3_output?.posts?.length > 0) {
          setEditContent(data.agent3_output.posts[0].content);
        }
      } catch (err) {
        console.error(err);
        router.push("/dashboard");
      } finally {
        setIsLoading(false);
      }
    }

    fetchJob();
  }, [jobId, router, backendUrl]);

  // Handle Tab Switch
  const handleTabChange = (index: number) => {
    setActiveTab(index);
    if (job?.agent3_output?.posts?.[index]) {
      setEditContent(job.agent3_output.posts[index].content);
    }
  };

  // Copy to Clipboard
  const handleCopy = async (index: number) => {
    const textToCopy = job?.agent3_output?.posts?.[index]?.content || editContent;
    try {
      await navigator.clipboard.writeText(textToCopy);
      setCopiedIndex(index);
      confetti({
        particleCount: 50,
        spread: 60,
        origin: { y: 0.8 }
      });
      setTimeout(() => setCopiedIndex(null), 2000);
    } catch (err) {
      console.error("Failed to copy text:", err);
    }
  };

  // Save Edits to backend JSONB
  const handleSave = async () => {
    if (!jobId || !job) return;

    setIsSaving(true);
    try {
      const response = await fetch(`${backendUrl}/api/pipeline/jobs/${jobId}/draft`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          post_index: activeTab,
          content: editContent,
        }),
      });

      if (!response.ok) {
        throw new Error("Failed to save changes.");
      }

      const updatedJob = (await response.json()) as Job;
      setJob(updatedJob);
    } catch (err) {
      alert("Failed to save edits to PostgreSQL.");
    } finally {
      setIsSaving(false);
    }
  };

  // Export as file
  const handleExport = (styleName: string) => {
    const text = editContent;
    const blob = new Blob([text], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${job?.repo_name}_${styleName.toLowerCase().replace(/ /g, "_")}.txt`;
    link.click();
    URL.revokeObjectURL(url);
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-black flex flex-col items-center justify-center">
        <Loader2 className="h-10 w-10 text-violet-500 animate-spin mb-3" />
        <p className="text-sm text-slate-500">Loading generated drafts...</p>
      </div>
    );
  }

  if (!job || !job.agent3_output?.posts) {
    return (
      <div className="min-h-screen bg-black flex flex-col items-center justify-center">
        <p className="text-red-400">Failed to load drafts. Redirecting...</p>
      </div>
    );
  }

  const posts = job.agent3_output.posts;

  return (
    <div className="min-h-screen bg-black text-slate-100 flex flex-col">
      {/* Top Navbar */}
      <nav className="w-full max-w-7xl mx-auto px-6 py-4 flex justify-between items-center border-b border-slate-900 bg-black/50 backdrop-blur sticky top-0 z-20">
        <div 
          onClick={() => router.push("/dashboard")}
          className="flex items-center gap-2 cursor-pointer text-slate-400 hover:text-slate-200 transition-all text-sm font-medium"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Dashboard
        </div>
        <div className="flex items-center gap-2">
          <BrainCircuit className="h-6 w-6 text-violet-500" />
          <span className="text-base font-bold bg-gradient-to-r from-white to-slate-400 bg-clip-text text-transparent">
            DevStory.AI
          </span>
        </div>
      </nav>

      {/* Main Grid */}
      <div className="flex-1 max-w-7xl w-full mx-auto px-6 py-8 grid grid-cols-1 lg:grid-cols-12 gap-8">
        
        {/* Left Side: Draft Editor (8 Columns) */}
        <div className="lg:col-span-8 flex flex-col gap-6">
          <div className="flex flex-col gap-1">
            <h2 className="text-2xl font-bold flex items-center gap-2">
              <Sparkles className="h-5 w-5 text-violet-400" />
              Your Generated LinkedIn Post Drafts
            </h2>
            <p className="text-sm text-slate-400">Review, customize, and copy your LinkedIn-ready posts.</p>
          </div>

          {/* Style Selector Tabs */}
          <div className="flex gap-2 p-1.5 rounded-xl bg-slate-950/80 border border-slate-900 overflow-x-auto">
            {posts.map((post, idx) => (
              <button
                key={post.style}
                onClick={() => handleTabChange(idx)}
                className={`px-4 py-2 rounded-lg text-xs font-semibold whitespace-nowrap transition-all duration-300 ${
                  activeTab === idx 
                    ? "bg-violet-600 text-white shadow-md shadow-violet-600/10" 
                    : "text-slate-400 hover:text-slate-200 hover:bg-slate-900/60"
                }`}
              >
                {post.style}
              </button>
            ))}
          </div>

          {/* Editor Container */}
          <div className="flex flex-col rounded-2xl glass overflow-hidden">
            {/* Header Controls */}
            <div className="px-5 py-3.5 border-b border-slate-900 flex justify-between items-center bg-slate-950/30">
              <span className="text-xs font-bold text-violet-400 uppercase tracking-wider">
                {posts[activeTab]?.style} Style
              </span>
              <div className="flex items-center gap-3">
                <button
                  onClick={handleSave}
                  disabled={isSaving}
                  className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-white font-medium transition-all"
                  title="Save edits to DB"
                >
                  {isSaving ? (
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  ) : (
                    <Save className="h-3.5 w-3.5" />
                  )}
                  {isSaving ? "Saving..." : "Save Draft"}
                </button>
                <span className="h-4 w-px bg-slate-800" />
                <button
                  onClick={() => handleExport(posts[activeTab]?.style)}
                  className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-white font-medium transition-all"
                  title="Export to text file"
                >
                  <FileDown className="h-3.5 w-3.5" />
                  Export
                </button>
              </div>
            </div>

            {/* Input area */}
            <textarea
              value={editContent}
              onChange={(e) => setEditContent(e.target.value)}
              className="w-full bg-slate-950/20 text-slate-300 font-mono text-sm leading-relaxed p-6 min-h-[350px] focus:outline-none resize-y border-none"
              placeholder="Post content will appear here..."
            />

            {/* Footer actions */}
            <div className="px-5 py-4 border-t border-slate-900 flex justify-between items-center bg-slate-950/30">
              <span className="text-[10px] text-slate-500">
                Word Count: {editContent.split(/\s+/).filter(Boolean).length} words
              </span>
              <button
                onClick={() => handleCopy(activeTab)}
                className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-violet-600 hover:bg-violet-500 text-white font-semibold text-xs transition-all duration-300 shadow-md shadow-violet-600/10 active:scale-95"
              >
                {copiedIndex === activeTab ? (
                  <>
                    <Check className="h-3.5 w-3.5" />
                    Copied to Clipboard!
                  </>
                ) : (
                  <>
                    <Copy className="h-3.5 w-3.5" />
                    Copy Post Text
                  </>
                )}
              </button>
            </div>
          </div>
        </div>

        {/* Right Side: Meta Details (4 Columns) */}
        <div className="lg:col-span-4 flex flex-col gap-6">
          <div className="p-6 rounded-2xl glass flex flex-col gap-6 sticky top-24">
            
            {/* Repo Header */}
            <div>
              <span className="text-[9px] uppercase tracking-wider text-slate-500 font-bold">Codebase</span>
              <h3 className="text-xl font-bold text-slate-200 mt-0.5">{job.repo_name}</h3>
              <p className="text-xs text-slate-400 font-mono mt-0.5">{job.repo_full_name}</p>
            </div>

            {/* Tech Stack Meta */}
            {job.agent1_output && (
              <div className="flex flex-col gap-4 border-t border-slate-900 pt-5">
                <div className="flex flex-col gap-1.5">
                  <span className="text-[10px] uppercase tracking-wider text-slate-500 font-bold flex items-center gap-1.5">
                    <Code2 className="h-3.5 w-3.5 text-violet-400" />
                    Tech Stack
                  </span>
                  <div className="flex flex-wrap gap-1.5">
                    {job.agent1_output.tech_stack?.map((tech) => (
                      <span 
                        key={tech} 
                        className="text-[10px] bg-slate-900 border border-slate-800 text-slate-300 px-2 py-0.5 rounded-full font-medium"
                      >
                        {tech}
                      </span>
                    ))}
                  </div>
                </div>

                <div className="flex flex-col gap-1.5">
                  <span className="text-[10px] uppercase tracking-wider text-slate-500 font-bold flex items-center gap-1.5">
                    <BookOpen className="h-3.5 w-3.5 text-violet-400" />
                    System Architecture
                  </span>
                  <p className="text-xs text-slate-400 leading-relaxed bg-slate-950/80 p-3 rounded-xl border border-slate-900">
                    {job.agent1_output.architecture}
                  </p>
                </div>

                <div className="flex justify-between items-center bg-slate-950/80 p-3 rounded-xl border border-slate-900 text-xs">
                  <span className="text-slate-500 font-medium">Complexity Rating</span>
                  <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase ${
                    job.agent1_output.complexity === "high" 
                      ? "bg-red-950/40 text-red-400 border border-red-900/30" 
                      : job.agent1_output.complexity === "medium"
                        ? "bg-amber-950/40 text-amber-400 border border-amber-900/30"
                        : "bg-emerald-950/40 text-emerald-400 border border-emerald-900/30"
                  }`}>
                    {job.agent1_output.complexity}
                  </span>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default function DraftsPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen bg-black flex flex-col items-center justify-center">
        <Loader2 className="h-10 w-10 text-violet-500 animate-spin" />
      </div>
    }>
      <DraftsContent />
    </Suspense>
  );
}
