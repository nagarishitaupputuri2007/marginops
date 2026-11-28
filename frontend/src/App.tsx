import React, { Component, ErrorInfo, ReactNode } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { RootLayout } from '@/layouts/RootLayout';
import { DashboardPage } from '@/pages/DashboardPage';
import { CostExplorerPage } from '@/pages/CostExplorerPage';
import { UnitEconomicsPage } from '@/pages/UnitEconomicsPage';
import { AnomaliesPage } from '@/pages/AnomaliesPage';
import { InvestigatorPage } from '@/pages/InvestigatorPage';
import { AlertTriangle, RefreshCw } from 'lucide-react';

interface ErrorBoundaryProps {
  children: ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error?: Error;
}

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  public state: ErrorBoundaryState = {
    hasError: false,
  };

  public static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Uncaught error inside MarginOps view:', error, errorInfo);
  }

  public render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-[#090a0f] flex items-center justify-center p-6 text-zinc-100 font-sans">
          <div className="bg-[#0e1017] border border-zinc-800 rounded-xl max-w-md w-full p-6 text-center space-y-4 shadow-xl">
            <div className="h-10 w-10 rounded-full bg-rose-500/10 border border-rose-500/20 flex items-center justify-center text-rose-400 mx-auto">
              <AlertTriangle className="h-5 w-5" />
            </div>
            <div>
              <h2 className="text-sm font-semibold text-zinc-100">Rendering Resilience Boundary</h2>
              <p className="text-xs text-zinc-400 mt-1">
                A transient rendering error occurred in this view. The rest of the platform remains operational.
              </p>
            </div>
            {this.state.error && (
              <div className="p-3 rounded-lg bg-black/50 border border-zinc-800 text-[11px] font-mono text-zinc-400 text-left overflow-x-auto">
                {this.state.error.message}
              </div>
            )}
            <button
              onClick={() => {
                this.setState({ hasError: false });
                window.location.reload();
              }}
              className="px-4 py-2 rounded-lg bg-zinc-800 hover:bg-zinc-700 text-xs font-medium text-zinc-200 inline-flex items-center gap-2 transition"
            >
              <RefreshCw className="h-3.5 w-3.5" />
              Reload View
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      staleTime: 10000,
    },
  },
});

export const App: React.FC = () => {
  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<RootLayout />}>
              <Route index element={<DashboardPage />} />
              <Route path="explorer" element={<CostExplorerPage />} />
              <Route path="unit-economics" element={<UnitEconomicsPage />} />
              <Route path="anomalies" element={<AnomaliesPage />} />
              <Route path="investigator" element={<InvestigatorPage />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </QueryClientProvider>
    </ErrorBoundary>
  );
};

export default App;
