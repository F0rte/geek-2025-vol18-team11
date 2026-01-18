"use client";

import Link from "next/link";
import { useState } from "react";
import { generateWorld } from "@/lib/api-client";

export default function GeneratePage() {
  const [prompt, setPrompt] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSubmitted, setIsSubmitted] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!prompt.trim()) {
      setError("Please enter a prompt");
      return;
    }

    setIsSubmitting(true);
    setError(null);

    try {
      await generateWorld(prompt);
      setIsSubmitted(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to submit request. Please try again.");
    } finally {
      setIsSubmitting(false);
    }
  };

  if (isSubmitted) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center bg-slate-950 text-cyan-50 font-mono relative overflow-hidden select-none">
        {/* Background Grid & Effects */}
        <div className="absolute inset-0 bg-[linear-gradient(to_right,#0f172a_1px,transparent_1px),linear-gradient(to_bottom,#0f172a_1px,transparent_1px)] bg-[size:4rem_4rem] [mask-image:radial-gradient(ellipse_80%_50%_at_50%_50%,#000_70%,transparent_100%)] opacity-20 pointer-events-none" />

        <main className="relative z-10 flex flex-col items-center text-center p-8 max-w-2xl w-full">
          {/* Success Icon */}
          <div className="mb-8">
            <div className="w-24 h-24 rounded-full bg-emerald-500/20 border-2 border-emerald-500 flex items-center justify-center">
              <svg
                className="w-12 h-12 text-emerald-500"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M5 13l4 4L19 7"
                />
              </svg>
            </div>
          </div>

          {/* Success Message */}
          <h1 className="text-4xl font-black tracking-tighter text-transparent bg-clip-text bg-gradient-to-b from-emerald-100 to-emerald-500 mb-6">
            Request Submitted Successfully!
          </h1>

          <p className="text-cyan-100/70 text-lg mb-12 max-w-md">
            Your 3D world is being generated. Please check back later.
          </p>

          {/* Back Button */}
          <Link
            href="/"
            className="group relative inline-flex items-center justify-center px-12 py-4 text-lg font-bold text-cyan-950 transition-all duration-200 bg-cyan-500 font-mono focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-cyan-500 hover:bg-cyan-400 hover:scale-105"
            style={{
              clipPath:
                "polygon(10% 0, 100% 0, 100% 80%, 90% 100%, 0 100%, 0 20%)",
            }}
          >
            <span className="relative flex items-center gap-3">
              <svg
                className="w-5 h-5 group-hover:-translate-x-1 transition-transform"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M11 17l-5-5m0 0l5-5m-5 5h12"
                />
              </svg>
              Back to Home
            </span>
          </Link>
        </main>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-slate-950 text-cyan-50 font-mono relative overflow-hidden select-none">
      {/* Background Grid & Effects */}
      <div className="absolute inset-0 bg-[linear-gradient(to_right,#0f172a_1px,transparent_1px),linear-gradient(to_bottom,#0f172a_1px,transparent_1px)] bg-[size:4rem_4rem] [mask-image:radial-gradient(ellipse_80%_50%_at_50%_50%,#000_70%,transparent_100%)] opacity-20 pointer-events-none" />
      <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-transparent via-emerald-500 to-transparent opacity-50" />

      <main className="relative z-10 flex flex-col items-center p-8 max-w-3xl w-full">
        {/* Title */}
        <h1 className="text-5xl md:text-6xl font-black tracking-tighter text-transparent bg-clip-text bg-gradient-to-b from-emerald-100 to-emerald-500 drop-shadow-[0_0_20px_rgba(16,185,129,0.6)] mb-4">
          Generate 3D World
        </h1>

        <div className="w-full max-w-md h-px bg-gradient-to-r from-transparent via-emerald-900 to-transparent mb-12" />

        {/* Form */}
        <form onSubmit={handleSubmit} className="w-full max-w-2xl">
          {/* Prompt Input */}
          <div className="mb-6">
            <label htmlFor="prompt" className="block text-cyan-500/70 text-sm uppercase tracking-widest mb-3">
              Enter your prompt
            </label>
            <textarea
              id="prompt"
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder="Enter your prompt in Japanese (日本語で入力してください)"
              className="w-full min-h-[180px] px-6 py-4 bg-slate-900/50 border border-cyan-500/30 rounded text-cyan-50 placeholder-cyan-500/30 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent resize-none font-mono"
              maxLength={500}
              disabled={isSubmitting}
            />
            <div className="text-right text-xs text-cyan-500/50 mt-2">
              {prompt.length} / 500
            </div>
          </div>

          {/* Error Message */}
          {error && (
            <div className="mb-6 p-4 bg-red-500/10 border border-red-500/50 rounded">
              <p className="text-red-400 text-sm">{error}</p>
            </div>
          )}

          {/* Buttons */}
          <div className="flex flex-col md:flex-row gap-4 justify-center">
            <Link
              href="/"
              className="group relative inline-flex items-center justify-center px-10 py-4 text-lg font-bold text-cyan-100 transition-all duration-200 bg-slate-800 font-mono border border-cyan-500/30 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-cyan-500 hover:bg-slate-700 hover:scale-105"
              style={{
                clipPath:
                  "polygon(10% 0, 100% 0, 100% 80%, 90% 100%, 0 100%, 0 20%)",
              }}
            >
              <span className="relative flex items-center gap-3">
                <svg
                  className="w-5 h-5 group-hover:-translate-x-1 transition-transform"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M11 17l-5-5m0 0l5-5m-5 5h12"
                  />
                </svg>
                Back to Home
              </span>
            </Link>

            <button
              type="submit"
              disabled={!prompt.trim() || isSubmitting}
              className="group relative inline-flex items-center justify-center px-10 py-4 text-lg font-bold text-slate-950 transition-all duration-200 bg-emerald-500 font-mono focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-emerald-500 hover:bg-emerald-400 hover:scale-105 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100"
              style={{
                clipPath:
                  "polygon(10% 0, 100% 0, 100% 80%, 90% 100%, 0 100%, 0 20%)",
              }}
            >
              <span className="absolute inset-0 w-full h-full -mt-1 rounded-lg opacity-30 bg-gradient-to-b from-transparent via-transparent to-black" />
              <span className="relative flex items-center gap-3">
                {isSubmitting ? (
                  <>
                    <svg
                      className="animate-spin w-5 h-5"
                      fill="none"
                      viewBox="0 0 24 24"
                    >
                      <circle
                        className="opacity-25"
                        cx="12"
                        cy="12"
                        r="10"
                        stroke="currentColor"
                        strokeWidth="4"
                      />
                      <path
                        className="opacity-75"
                        fill="currentColor"
                        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                      />
                    </svg>
                    Generating...
                  </>
                ) : (
                  <>
                    Generate
                    <svg
                      className="w-5 h-5 group-hover:rotate-90 transition-transform"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M12 4v16m8-8H4"
                      />
                    </svg>
                  </>
                )}
              </span>
            </button>
          </div>
        </form>

        {/* Info Panel */}
        <div className="mt-16 bg-slate-900/50 border border-emerald-500/10 p-6 rounded backdrop-blur-sm max-w-2xl w-full">
          <h3 className="text-emerald-500/70 text-xs uppercase tracking-widest mb-3">
            Generation Info
          </h3>
          <ul className="text-cyan-100/70 text-sm space-y-2 list-disc list-inside">
            <li>Enter a detailed description in Japanese</li>
            <li>Generation may take several minutes</li>
            <li>Check the Play Game menu to view your generated world</li>
          </ul>
        </div>
      </main>
    </div>
  );
}
