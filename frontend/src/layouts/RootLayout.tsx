import React from 'react';
import { Outlet, Link, useLocation } from 'react-router-dom';
import {
  Layers,
  LayoutDashboard,
  BarChart3,
  TrendingUp,
  AlertCircle,
  Bot,
  ShieldCheck,
  CheckCircle2,
} from 'lucide-react';

export const RootLayout: React.FC = () => {
  const location = useLocation();

  const navItems = [
    { label: 'Overview', path: '/', icon: LayoutDashboard },
    { label: 'Cost Explorer', path: '/explorer', icon: BarChart3 },
    { label: 'Unit Economics', path: '/unit-economics', icon: TrendingUp },
    { label: 'Anomalies & Radar', path: '/anomalies', icon: AlertCircle },
    { label: 'AI Investigator', path: '/investigator', icon: Bot },
  ];

  const currentRoute = navItems.find((item) => item.path === location.pathname) || navItems[0];

  return (
    <div className="flex h-screen bg-[#090a0f] text-zinc-100 overflow-hidden font-sans selection:bg-zinc-800">
      {/* Enterprise Minimalist Sidebar */}
      <aside className="w-64 border-r border-zinc-800/80 bg-[#0d0e15] flex flex-col shrink-0 select-none">
        {/* Workspace Brand Header */}
        <div className="h-16 flex items-center justify-between px-5 border-b border-zinc-800/80">
          <div className="flex items-center gap-3">
            <div className="h-8 w-8 rounded-lg bg-zinc-800/90 border border-zinc-700/60 flex items-center justify-center text-zinc-200 shadow-sm">
              <Layers className="h-4 w-4 text-zinc-200" />
            </div>
            <div className="flex flex-col">
              <span className="font-semibold text-sm tracking-tight text-zinc-100">
                MarginOps
              </span>
              <span className="text-[10px] text-zinc-400 font-medium tracking-wide uppercase">
                FinOps Enterprise
              </span>
            </div>
          </div>
          <span className="text-[10px] font-mono font-medium px-2 py-0.5 rounded bg-zinc-800/80 text-zinc-400 border border-zinc-700/40">
            v1.0
          </span>
        </div>

        {/* Primary Navigation */}
        <div className="px-3 pt-4 pb-2">
          <p className="px-3 text-[11px] font-medium uppercase tracking-wider text-zinc-400 mb-2">
            Intelligence Platform
          </p>
          <nav className="space-y-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = location.pathname === item.path;
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  className={`group flex items-center justify-between px-3 py-2 rounded-lg text-xs font-medium transition-colors ${
                    isActive
                      ? 'bg-zinc-800/90 text-zinc-100 shadow-sm border border-zinc-700/60'
                      : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800/40'
                  }`}
                >
                  <div className="flex items-center gap-2.5">
                    <Icon className={`h-4 w-4 transition-colors ${isActive ? 'text-zinc-100' : 'text-zinc-400 group-hover:text-zinc-300'}`} />
                    <span>{item.label}</span>
                  </div>
                  {isActive && (
                    <span className="h-1.5 w-1.5 rounded-full bg-emerald-400"></span>
                  )}
                </Link>
              );
            })}
          </nav>
        </div>

        {/* Multi-Tenant Context Box */}
        <div className="mt-auto p-4 border-t border-zinc-800/80 space-y-3">
          <div className="bg-[#12141e] border border-zinc-800/90 rounded-lg p-3 space-y-2">
            <div className="flex items-center justify-between text-xs">
              <span className="text-zinc-400 font-medium">Reconciliation</span>
              <span className="inline-flex items-center gap-1 font-mono text-[11px] text-emerald-400 font-medium">
                <CheckCircle2 className="h-3 w-3" />
                Δ = $0.0000
              </span>
            </div>
            <div className="flex items-center justify-between text-[11px] text-zinc-400 pt-1 border-t border-zinc-800/60">
              <span className="truncate">Acme Cloud AI</span>
              <span className="font-mono text-zinc-400">AWS • GCP • AZ</span>
            </div>
          </div>

          {/* User Profile Bar */}
          <div className="flex items-center justify-between pt-1 text-xs text-zinc-300">
            <div className="flex items-center gap-2.5 min-w-0">
              <div className="h-7 w-7 rounded-full bg-zinc-800 border border-zinc-700 flex items-center justify-center text-zinc-200 font-semibold text-[11px] shrink-0">
                NR
              </div>
              <div className="flex flex-col min-w-0">
                <span className="text-xs font-medium text-zinc-200 truncate">Naga Rishita</span>
                <span className="text-[10px] text-zinc-400 truncate">FinOps Architect</span>
              </div>
            </div>
            <div className="h-2 w-2 rounded-full bg-emerald-500/80" title="Session Authenticated"></div>
          </div>
        </div>
      </aside>

      {/* Main Content Viewport */}
      <div className="flex-1 flex flex-col overflow-hidden bg-[#090a0f]">
        {/* Executive Top App Bar */}
        <header className="h-16 border-b border-zinc-800/80 px-8 flex items-center justify-between bg-[#0d0e15]/60 backdrop-blur-sm shrink-0">
          <div className="flex items-center gap-2 text-xs">
            <span className="text-zinc-400">Platform</span>
            <span className="text-zinc-400">/</span>
            <span className="font-medium text-zinc-200">{currentRoute.label}</span>
          </div>

          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2 px-3 py-1 rounded-md bg-zinc-900 border border-zinc-800 text-[11px] text-zinc-300">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-400"></span>
              <span className="font-medium">All 5 Engines Operational</span>
            </div>
            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-zinc-900/60 border border-zinc-800/80 text-[11px] text-zinc-400 font-mono">
              <ShieldCheck className="h-3.5 w-3.5 text-zinc-400" />
              <span>SOC2 Reconciled</span>
            </div>
          </div>
        </header>

        {/* Scrollable View Content */}
        <main className="flex-1 p-8 overflow-y-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
};
