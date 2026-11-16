import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { RootLayout } from '@/layouts/RootLayout';
import { DashboardPage } from '@/pages/DashboardPage';
import { CostExplorerPage } from '@/pages/CostExplorerPage';
import { UnitEconomicsPage } from '@/pages/UnitEconomicsPage';
import { AnomaliesPage } from '@/pages/AnomaliesPage';
import { InvestigatorPage } from '@/pages/InvestigatorPage';

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
  );
};

export default App;
