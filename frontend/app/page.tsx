"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

export default function Home() {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-slate-950 text-cyan-50 font-mono relative overflow-hidden select-none">
      {/* Background Grid & Effects */}
      <div className="absolute inset-0 bg-[linear-gradient(to_right,#0f172a_1px,transparent_1px),linear-gradient(to_bottom,#0f172a_1px,transparent_1px)] bg-[size:4rem_4rem] [mask-image:radial-gradient(ellipse_80%_50%_at_50%_50%,#000_70%,transparent_100%)] opacity-20 pointer-events-none" />
      <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-transparent via-cyan-500 to-transparent opacity-50" />
      <div className="absolute bottom-0 left-0 w-full h-1 bg-gradient-to-r from-transparent via-cyan-500 to-transparent opacity-50" />

      {/* Main Content */}
      <main className="relative z-10 flex flex-col items-center text-center p-8 max-w-4xl w-full">
        {/* Title Section */}
        <div
          className={`transition-all duration-1000 transform ${mounted ? "translate-y-0 opacity-100" : "translate-y-10 opacity-0"}`}
        >
          <h2 className="text-cyan-500 text-sm tracking-[0.5em] mb-4 uppercase font-bold animate-pulse">
            System Initialized
          </h2>
          <h1 className="text-6xl md:text-8xl font-black tracking-tighter text-transparent bg-clip-text bg-gradient-to-b from-cyan-100 to-cyan-500 drop-shadow-[0_0_20px_rgba(34,211,238,0.6)] mb-2">
            CYBER POINT
          </h1>
          <h1 className="text-5xl md:text-7xl font-black tracking-tighter text-transparent bg-clip-text bg-gradient-to-t from-slate-100 to-slate-400 drop-shadow-[0_0_20px_rgba(255,255,255,0.2)] mb-12">
            SHOOTER
          </h1>
        </div>

        {/* Decorative Lines */}
        <div className="w-full max-w-md h-px bg-gradient-to-r from-transparent via-cyan-900 to-transparent mb-12" />

        {/* Action Button */}
        <div
          className={`transition-all duration-1000 delay-300 transform ${mounted ? "translate-y-0 opacity-100" : "translate-y-10 opacity-0"}`}
        >
          <Link
            href="/viewer"
            className="group relative inline-flex items-center justify-center px-12 py-6 text-lg font-bold text-cyan-950 transition-all duration-200 bg-cyan-500 font-mono focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-cyan-500 hover:bg-cyan-400 hover:scale-105 clip-path-polygon"
            style={{
              clipPath:
                "polygon(10% 0, 100% 0, 100% 80%, 90% 100%, 0 100%, 0 20%)",
            }}
          >
            <span className="absolute inset-0 w-full h-full -mt-1 rounded-lg opacity-30 bg-gradient-to-b from-transparent via-transparent to-black" />
            <span className="relative flex items-center gap-3">
              Play Game
              <svg
                className="w-5 h-5 group-hover:translate-x-1 transition-transform"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M13 7l5 5m0 0l-5 5m5-5H6"
                />
              </svg>
            </span>
          </Link>
        </div>

        {/* Status Panels */}
        <div
          className={`mt-20 grid grid-cols-1 md:grid-cols-3 gap-6 w-full max-w-3xl transition-all duration-1000 delay-500 transform ${mounted ? "translate-y-0 opacity-100" : "translate-y-10 opacity-0"}`}
        >
          <div className="bg-slate-900/50 border border-cyan-500/10 p-4 rounded backdrop-blur-sm">
            <h3 className="text-cyan-500/70 text-xs uppercase tracking-widest mb-1">
              Status
            </h3>
            <div className="text-green-400 font-bold flex items-center justify-center gap-2">
              <span className="w-2 h-2 bg-green-400 rounded-full animate-pulse" />
              ONLINE
            </div>
          </div>

          <div className="bg-slate-900/50 border border-cyan-500/10 p-4 rounded backdrop-blur-sm">
            <h3 className="text-cyan-500/70 text-xs uppercase tracking-widest mb-1">
              Target
            </h3>
            <div className="text-cyan-100 font-bold">HUNYUAN 3D</div>
          </div>

          <div className="bg-slate-900/50 border border-cyan-500/10 p-4 rounded backdrop-blur-sm">
            <h3 className="text-cyan-500/70 text-xs uppercase tracking-widest mb-1">
              Version
            </h3>
            <div className="text-cyan-100 font-bold">v2.5.0 STABLE</div>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="absolute bottom-4 text-slate-600 text-xs uppercase tracking-widest">
        © 2026 F0rte Geek Team 11
      </footer>
    </div>
  );
}
