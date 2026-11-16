import React from 'react';
import { Outlet, Link, useLocation } from 'react-router-dom';
import {
  Activity,
  LayoutDashboard,
  DollarSign,
  Cpu,
  AlertTriangle,
  Sparkles,
  ShieldCheck,
} from 'lucide-react';

export const RootLayout: React.FC = () => {
  const location = useLocation();

  const navItems = [
    { label: 'Overview', path: '/', icon: LayoutDashboard },
    { label: 'Cost Explorer', path: '/explorer', icon: DollarSign },
    { label: 'Unit Economics', path: '/unit-economics', icon: Cpu },
    { label: 'Anomalies & Radar', path: '/anomalies', icon: AlertTriangle },
    { label: 'AI Investigator', path: '/investigator', icon: Sparkles },
  ];

  return (
    <div className="flex h-screen bg-slate-950 text-slate-100 overflow-hidden font-sans">
      {/* Sidebar */}
      <aside className="w-64 border-r border-slate-800 bg-slate-900/60 flex flex-col shrink-0">
        <div className="h-16 flex items-center px-6 border-b border-slate-800 gap-3">
          <Activity className="h-6 w-6 text-emerald-400" />
          <div className="flex flex-col">
            <span className="font-bold text-base tracking-tight bg-gradient-to-r from-emerald-400 to-teal-300 bg-clip-text text-transparent">
              MarginOps
            </span>
            <span className="text-[10px] font-mono text-slate-500 uppercase tracking-widest">
              FinOps Intelligence
            </span>
          </div>
        </div>

        <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = location.pathname === item.path;
            return (
              <Link
                key={item.path}
                to={item.path}
                className={`flex items-center gap-3 px-3 py-2 rounded-xl text-xs font-semibold transition-all ${
                  isActive
                    ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
                }`}
              >
                <Icon className={`h-4 w-4 ${isActive ? 'text-emerald-400' : 'text-slate-400'}`} />
                {item.label}
              </Link>
            );
          })}
        </nav>

        {/* Invariant Status Badge */}
        <div className="p-4 border-t border-slate-800/80 space-y-2 text-xs">
          <div className="p-2.5 rounded-lg bg-slate-950/80 border border-slate-800 flex items-center gap-2 font-mono text-[11px]">
            <ShieldCheck className="h-4 w-4 text-emerald-400 shrink-0" />
            <span className="text-slate-400 truncate">Ledger Δ: $0.0000</span>
          </div>
          <div className="text-[10px] text-slate-500 px-1 font-mono">
            Acme Cloud AI Inc. • v0.1.0
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col overflow-auto bg-slate-950">
        <header className="h-16 border-b border-slate-800/80 px-8 flex items-center justify-between bg-slate-900/30 shrink-0">
          <h2 className="text-xs font-medium text-slate-400">
            Multi-Cloud Infrastructure Cost Intelligence & Product Economics Platform
          </h2>
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20">
              <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse"></span>
              <span className="text-[11px] font-mono text-emerald-400 font-semibold">
                Engines Operational
              </span>
            </div>
          </div>
        </header>

        <main className="flex-1 p-8 overflow-y-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
};
