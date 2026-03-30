import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useUpload } from '../contexts/UploadContext';
import axios from 'axios';

const Layout: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const location = useLocation();
  const { result } = useUpload();
  const [downloading, setDownloading] = useState(false);

  const navigation = [
    { name: 'Home', href: '/', icon: '🏠' },
    { name: 'Detection', href: '/detection', icon: '👁️' },
    { name: '3D Model', href: '/3d-model', icon: '🏗️' },
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
      alert("Failed to generate report.");
    } finally {
      setDownloading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950">
      {/* Animated Background */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-40 -right-40 w-80 h-80 bg-indigo-500/10 rounded-full blur-3xl"></div>
        <div className="absolute top-1/2 -left-40 w-80 h-80 bg-purple-500/10 rounded-full blur-3xl"></div>
        <div className="absolute -bottom-40 right-1/3 w-80 h-80 bg-cyan-500/10 rounded-full blur-3xl"></div>
      </div>

      {/* Top Navigation */}
      <nav className="fixed top-0 left-0 right-0 z-50 bg-slate-900/70 backdrop-blur-xl border-b border-slate-800/50">
        <div className="max-w-7xl mx-auto px-6">
          <div className="flex items-center justify-between h-16">
            {/* Logo */}
            <Link to="/" className="flex items-center space-x-3 group">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center shadow-lg shadow-indigo-500/25 group-hover:shadow-indigo-500/40 transition-all">
                <span className="text-white font-bold text-sm">F3D</span>
              </div>
              <div>
                <span className="text-white font-bold text-lg">Floor3D</span>
                <span className="hidden md:inline text-slate-500 text-xs ml-2">AI-Powered Analysis</span>
              </div>
            </Link>

            {/* Nav Links */}
            <div className="flex items-center space-x-1">
              {navigation.map((item) => {
                const isActive = location.pathname === item.href;
                return (
                  <Link
                    key={item.name}
                    to={item.href}
                    className={`px-4 py-2 rounded-xl text-sm font-medium transition-all flex items-center gap-2 ${
                      isActive
                        ? 'bg-gradient-to-r from-indigo-600 to-purple-600 text-white shadow-lg shadow-indigo-500/25'
                        : 'text-slate-400 hover:text-white hover:bg-slate-800/50'
                    }`}
                  >
                    <span className="text-base">{item.icon}</span>
                    <span className="hidden md:inline">{item.name}</span>
                  </Link>
                );
              })}
            </div>

            {/* Export Button */}
            {result?.project_id && (
              <button
                onClick={handleDownloadReport}
                disabled={downloading}
                className="px-4 py-2 bg-gradient-to-r from-emerald-600 to-teal-600 text-white text-sm font-medium rounded-xl hover:from-emerald-500 hover:to-teal-500 transition-all shadow-lg shadow-emerald-500/20 disabled:opacity-50 flex items-center gap-2"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                {downloading ? 'Exporting...' : 'Export PDF'}
              </button>
            )}
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main className="relative pt-16 min-h-screen">
        <div className="max-w-7xl mx-auto px-6 py-8">
          {children}
        </div>
      </main>

      {/* Footer */}
      <footer className="relative border-t border-slate-800/50 py-6">
        <div className="max-w-7xl mx-auto px-6 flex items-center justify-between">
          <p className="text-slate-500 text-sm">
            Floor3D — AI-powered floor plan analysis
          </p>
          <p className="text-slate-600 text-xs">
            Built for Hackathon 2024
          </p>
        </div>
      </footer>
    </div>
  );
};

export default Layout;
