import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useUpload } from '../contexts/UploadContext';
import axios from 'axios';

const Layout: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const location = useLocation();
  const { result } = useUpload();
  const [downloading, setDownloading] = useState(false);

  const navigation = [
    { name: 'Home', href: '/' },
    { name: 'Detection', href: '/detection' },
    { name: '3D Model', href: '/3d-model' },
    { name: 'Materials', href: '/materials' },
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
    <div className="min-h-screen bg-slate-950">
      {/* Top Navigation */}
      <nav className="fixed top-0 left-0 right-0 z-50 bg-slate-900/80 backdrop-blur-sm border-b border-slate-800">
        <div className="max-w-7xl mx-auto px-6">
          <div className="flex items-center justify-between h-16">
            {/* Logo */}
            <div className="flex items-center space-x-3">
              <div className="w-8 h-8 rounded-lg bg-indigo-600 flex items-center justify-center">
                <span className="text-white font-bold text-sm">F3D</span>
              </div>
              <span className="text-white font-semibold text-lg">Floor3D</span>
            </div>

            {/* Nav Links */}
            <div className="flex items-center space-x-1">
              {navigation.map((item) => {
                const isActive = location.pathname === item.href;
                return (
                  <Link
                    key={item.name}
                    to={item.href}
                    className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                      isActive
                        ? 'bg-indigo-600 text-white'
                        : 'text-slate-400 hover:text-white hover:bg-slate-800'
                    }`}
                  >
                    {item.name}
                  </Link>
                );
              })}
            </div>

            {/* Export Button */}
            {result?.project_id && (
              <button
                onClick={handleDownloadReport}
                disabled={downloading}
                className="px-4 py-2 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 transition-colors disabled:opacity-50"
              >
                {downloading ? 'Exporting...' : 'Export PDF'}
              </button>
            )}
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main className="pt-16 min-h-screen">
        <div className="max-w-7xl mx-auto px-6 py-8">
          {children}
        </div>
      </main>
    </div>
  );
};

export default Layout;
