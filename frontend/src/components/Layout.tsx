import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useUpload } from '../contexts/UploadContext';
import axios from 'axios';

const Layout: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const location = useLocation();
  const { result } = useUpload();
  const [downloading, setDownloading] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  const navigation = [
    { name: 'Home', href: '/', icon: '🏠' },
    { name: 'Detection', href: '/detection', icon: '🔍' },
    { name: '3D Floor', href: '/3d-model', icon: '🏗️' },
    { name: 'Materials', href: '/materials', icon: '🧱' },
  ];

  const handleDownloadReport = async () => {
    if (!result?.project_id) return;
    setDownloading(true);
    let imageBase64 = "";

    try {
      const canvas = document.querySelector('canvas');
      if (canvas) {
        imageBase64 = canvas.toDataURL('image/png');
      }

      const response = await axios.post(
        `http://localhost:8000/api/export-report/${result.project_id}`,
        { image_base64: imageBase64 },
        { responseType: 'blob' }
      );

      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `Floor3D_Report_${result.project_id.split('-')[0]}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (err) {
      console.error("Failed to download report", err);
      alert("Failed to generate report. Please try again.");
    } finally {
      setDownloading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 flex">
      {/* Sidebar Navigation */}
      <aside className={`${sidebarCollapsed ? 'w-20' : 'w-64'} min-h-screen bg-white border-r border-gray-200 transition-all duration-300 flex flex-col fixed left-0 top-0 z-50`}>
        {/* Logo Section */}
        <div className="p-5 border-b border-gray-100">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-blue-600 to-indigo-700 flex items-center justify-center shadow-sm">
              <span className="text-white text-lg font-bold">F</span>
            </div>
            {!sidebarCollapsed && (
              <div>
                <h1 className="text-lg font-bold text-gray-900">Floor3D</h1>
                <p className="text-[10px] text-gray-400 font-medium">Structural Analysis</p>
              </div>
            )}
          </div>
        </div>

        {/* Collapse Toggle */}
        <button 
          onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
          className="absolute -right-3 top-16 w-6 h-6 bg-white border border-gray-200 rounded-full shadow-sm flex items-center justify-center text-gray-400 hover:text-gray-600 transition-all z-10"
        >
          <svg className={`w-3 h-3 transition-transform ${sidebarCollapsed ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
        </button>

        {/* Navigation Items */}
        <nav className="flex-1 py-6 px-3 space-y-1">
          {navigation.map((item) => {
            const isActive = location.pathname === item.href;
            return (
              <Link
                key={item.name}
                to={item.href}
                className={`group flex items-center ${sidebarCollapsed ? 'justify-center' : ''} px-4 py-3 rounded-lg transition-all duration-200 ${
                  isActive
                    ? 'bg-blue-50 text-blue-700 border border-blue-100'
                    : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
                }`}
              >
                <span className="text-lg">{item.icon}</span>
                {!sidebarCollapsed && (
                  <span className={`ml-3 font-medium text-sm ${isActive ? 'text-blue-700' : ''}`}>
                    {item.name}
                  </span>
                )}
              </Link>
            );
          })}
        </nav>

        {/* Export Report Button */}
        {result?.project_id && (
          <div className="p-4 border-t border-gray-100">
            <button 
              onClick={handleDownloadReport}
              disabled={downloading}
              className={`w-full flex items-center ${sidebarCollapsed ? 'justify-center' : ''} px-4 py-3 rounded-lg bg-blue-600 text-white font-medium text-sm hover:bg-blue-700 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed`}
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              {!sidebarCollapsed && (
                <span className="ml-2">{downloading ? 'Generating...' : 'Export Report'}</span>
              )}
            </button>
          </div>
        )}

        {/* Version Info */}
        <div className="p-4 border-t border-gray-100">
          {!sidebarCollapsed && (
            <p className="text-xs text-gray-400 text-center">v1.0.0</p>
          )}
        </div>
      </aside>

      {/* Main Content Area */}
      <div className={`flex-1 ${sidebarCollapsed ? 'ml-20' : 'ml-64'} transition-all duration-300`}>
        {/* Top Header Bar */}
        <header className="sticky top-0 z-40 bg-white border-b border-gray-100">
          <div className="px-8 py-5">
            <h2 className="text-xl font-semibold text-gray-900">
              {navigation.find(n => n.href === location.pathname)?.name || 'Dashboard'}
            </h2>
            <p className="text-sm text-gray-500 mt-0.5">
              {location.pathname === '/' && 'Upload and analyze floor plans'}
              {location.pathname === '/detection' && 'View 2D detection results'}
              {location.pathname === '/3d-model' && 'Explore 3D visualization'}
              {location.pathname === '/materials' && 'Material recommendations & cost analysis'}
            </p>
          </div>
        </header>

        {/* Main Content */}
        <main className="p-8">
          {children}
        </main>
      </div>
    </div>
  );
};

export default Layout;
