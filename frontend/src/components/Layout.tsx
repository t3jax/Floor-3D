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
    { name: 'Detection', href: '/detection', icon: '🔍' },
    { name: '3D Floor', href: '/3d-model', icon: '🏗️' },
    { name: 'Materials', href: '/materials', icon: '🧱' },
  ];

  const handleDownloadReport = async () => {
    if (!result?.project_id) return;
    setDownloading(true);
    let imageBase64 = "";

    try {
      // 1. Grab canvas if available (from the 3D viewer)
      const canvas = document.querySelector('canvas');
      if (canvas) {
        imageBase64 = canvas.toDataURL('image/png');
      }

      // 2. Fetch the PDF blob from the backend
      const response = await axios.post(
        `http://localhost:8000/api/export-report/${result.project_id}`,
        { image_base64: imageBase64 },
        { responseType: 'blob' }
      );

      // 3. Trigger download sequence
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `Structural_Report_${result.project_id.split('-')[0]}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (err) {
      console.error("Failed to download report", err);
      alert("Uh oh! Failed to extract structural report.");
    } finally {
      setDownloading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-[#111827] to-[#0f172a] text-gray-100 font-sans">
      {/* Header (Glassmorphism Futuristic) */}
      <header className="sticky top-0 z-50 backdrop-blur-md bg-gray-900/60 border-b border-cyan-800/50 shadow-[0_0_20px_rgba(0,188,212,0.15)]">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-4">
            
            <div className="flex items-center space-x-4">
              {/* Load SVG component natively using an img tag for simplicity, or just build a box here... Actually, React `img src` works perfectly! */}
              <img src="/logo.svg" alt="Floor3D Logo" className="w-12 h-12 hover:scale-110 transition-transform duration-300" onError={(e) => { e.currentTarget.style.display = 'none'; }} />
              <div>
                <h1 className="text-2xl font-black bg-clip-text text-transparent bg-gradient-to-r from-cyan-400 to-blue-500 tracking-wider">
                  Floor<span className="font-light text-gray-200">3D</span>
                </h1>
                <p className="text-xs text-cyan-200/70 font-mono tracking-widest uppercase">
                  Autonomous Structural Intelligence
                </p>
              </div>
            </div>

            {/* Top Right Actions */}
            <div className="flex items-center space-x-6">
              {result?.project_id && (
                <button 
                  onClick={handleDownloadReport}
                  disabled={downloading}
                  className="relative group overflow-hidden px-6 py-2 rounded-full bg-gradient-to-r from-cyan-600 to-blue-600 text-white font-semibold text-sm shadow-[0_0_15px_rgba(0,188,212,0.4)] hover:shadow-[0_0_25px_rgba(0,188,212,0.8)] transition-all duration-300 active:scale-95 disabled:opacity-50"
                >
                  <span className="relative z-10 flex items-center space-x-2">
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path></svg>
                    <span>{downloading ? 'Compiling...' : 'Export Report'}</span>
                  </span>
                  <div className="absolute inset-0 bg-white/20 transform -translate-x-full group-hover:translate-x-full transition-transform duration-700"></div>
                </button>
              )}
            </div>

          </div>
        </div>
      </header>

      {/* Navigation Tabs */}
      <nav className="bg-gray-800/40 border-b border-gray-700/50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex space-x-2 py-2">
            {navigation.map((item) => {
              const isActive = location.pathname === item.href;
              return (
                <Link
                  key={item.name}
                  to={item.href}
                  className={`flex items-center px-4 py-3 rounded-t-lg transition-all duration-300 font-mono text-sm uppercase tracking-wider ${
                    isActive
                      ? 'bg-gray-900/80 text-cyan-400 border-b-2 border-cyan-400 shadow-[inset_0_-2px_8px_rgba(0,188,212,0.15)]'
                      : 'text-gray-400 hover:text-cyan-200 hover:bg-gray-800/50'
                  }`}
                >
                  <span className={`mr-2 ${isActive ? 'scale-110 drop-shadow-[0_0_5px_rgba(0,188,212,0.8)]' : ''} transition-transform`}>{item.icon}</span>
                  {item.name}
                </Link>
              );
            })}
          </div>
        </div>
      </nav>

      {/* Main Content Area */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 relative">
        <div className="absolute inset-0 bg-[url('https://www.transparenttextures.com/patterns/cubes.png')] opacity-[0.03] pointer-events-none"></div>
        <div className="relative z-10">
          {children}
        </div>
      </main>
    </div>
  );
};

export default Layout;
