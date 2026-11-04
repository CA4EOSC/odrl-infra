import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import DidManager from './pages/DidManager';
import VcWallet from './pages/VcWallet';
import PolicyBuilder from './pages/PolicyBuilder';
import Demo from './pages/Demo';
import PromptsManager from './pages/PromptsManager';
import VariablesManager from './pages/VariablesManager';
import CroissantsManager from './pages/CroissantsManager';
import GroupsManager from './pages/GroupsManager';
import OAuthCallback from './pages/OAuthCallback';
import Profile from './pages/Profile';

import { ThemeProvider } from './context/ThemeContext';
import { UserProvider } from './context/UserContext';

const queryClient = new QueryClient();

function App() {
  return (
    <ThemeProvider>
      <UserProvider>
        <QueryClientProvider client={queryClient}>
          <Router>
            <Layout>
              <Routes>
                <Route path="/" element={<Dashboard />} />
                <Route path="/dids" element={<DidManager />} />
                <Route path="/vcs" element={<VcWallet />} />
                <Route path="/policies" element={<PolicyBuilder />} />
                <Route path="/prompts" element={<PromptsManager />} />
                <Route path="/variables" element={<VariablesManager />} />
                <Route path="/croissants" element={<CroissantsManager />} />
                <Route path="/groups" element={<GroupsManager />} />
                <Route path="/demo" element={<Demo />} />
                <Route path="/profile" element={<Profile />} />
                <Route path="/auth/:provider/callback" element={<OAuthCallback />} />
              </Routes>
            </Layout>
          </Router>
        </QueryClientProvider>
      </UserProvider>
    </ThemeProvider>
  );
}

export default App;
