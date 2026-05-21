"use client";

import React, { useEffect, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Loader2 } from "lucide-react";

function CallbackContent() {
  const router = useRouter();
  const searchParams = useSearchParams();

  useEffect(() => {
    const userId = searchParams.get("user_id");
    const username = searchParams.get("username");
    const avatarUrl = searchParams.get("avatar_url");

    if (userId && username) {
      // Store session data locally
      localStorage.setItem("user_id", userId);
      localStorage.setItem("username", username);
      if (avatarUrl) {
        localStorage.setItem("avatar_url", avatarUrl);
      }
      
      // Redirect to dashboard
      router.push("/dashboard");
    } else {
      console.error("Missing OAuth parameters in redirect URL");
      router.push("/");
    }
  }, [router, searchParams]);

  return (
    <div className="min-h-screen bg-black flex flex-col items-center justify-center text-center px-4">
      <Loader2 className="h-12 w-12 text-violet-500 animate-spin mb-4" />
      <h2 className="text-xl font-bold mb-2">Authenticating with GitHub...</h2>
      <p className="text-sm text-slate-400">Please wait while we finalize your secure login.</p>
    </div>
  );
}

export default function AuthCallback() {
  return (
    <Suspense fallback={
      <div className="min-h-screen bg-black flex flex-col items-center justify-center">
        <Loader2 className="h-12 w-12 text-violet-500 animate-spin" />
      </div>
    }>
      <CallbackContent />
    </Suspense>
  );
}
