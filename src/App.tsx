import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Toaster } from 'sonner';
import Dashboard from '@/pages/Dashboard';
import SessionDetail from '@/pages/SessionDetail';
import SessionDetailV3 from '@/pages/SessionDetailV3';
import SessionIndex from '@/pages/SessionIndex';
import Compare from '@/pages/Compare';
import Models from '@/pages/Models';
import Details from '@/pages/Details';
import DetailsIndex from '@/pages/DetailsIndex';
import Layout from '@/components/Layout';
import DesignSystemPreview from '@/pages/DesignSystemPreview';
import AgentDebugger from '@/pages/AgentDebugger';
import SessionList from '@/pages/SessionList';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000, // 5分钟
      retry: 1,
    },
  },
});

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter
        future={{
          v7_startTransition: true,
          v7_relativeSplatPath: true,
        }}
      >
        <Routes>
          {/* Full-screen routes without Layout */}
          <Route path="/" element={<SessionList />} />
          <Route path="/debugger/:id" element={<AgentDebugger />} />

          {/* Old routes with Layout (hidden but kept for reference) */}
          <Route path="/legacy" element={<Layout />}>
            <Route index element={<Dashboard />} />
            <Route path="session" element={<SessionIndex />} />
            <Route path="session/:id" element={<SessionDetail />} />
            <Route path="session/:id/v3" element={<SessionDetailV3 />} />
            <Route path="compare" element={<Compare />} />
            <Route path="models" element={<Models />} />
            <Route path="details" element={<DetailsIndex />} />
            <Route path="details/:id" element={<Details />} />
            <Route path="design-system" element={<DesignSystemPreview />} />
          </Route>
        </Routes>
      </BrowserRouter>
      <Toaster position="top-right" />
    </QueryClientProvider>
  );
}

export default App;
