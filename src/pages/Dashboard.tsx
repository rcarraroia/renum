
import React from 'react';
import { Routes, Route } from 'react-router-dom';
import { SidebarProvider } from '@/components/ui/sidebar';
import { DashboardSidebar } from '@/components/dashboard/DashboardSidebar';
import { DashboardOverview } from '@/components/dashboard/DashboardOverview';
import { TeamsPage } from '@/components/dashboard/TeamsPage';
import { ExecutionsPage } from '@/components/dashboard/ExecutionsPage';
import { SystemHealthPage } from '@/components/dashboard/SystemHealthPage';

export default function Dashboard() {
  return (
    <SidebarProvider>
      <div className="min-h-screen flex w-full">
        <DashboardSidebar />
        <main className="flex-1 overflow-auto">
          <div className="container mx-auto p-6">
            <Routes>
              <Route path="/" element={<DashboardOverview />} />
              <Route path="/teams" element={<TeamsPage />} />
              <Route path="/executions" element={<ExecutionsPage />} />
              <Route path="/system" element={<SystemHealthPage />} />
            </Routes>
          </div>
        </main>
      </div>
    </SidebarProvider>
  );
}
