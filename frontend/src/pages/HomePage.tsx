import React, { useRef, useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useUpload } from '../contexts/UploadContext';
import { uploadFloorPlan } from '../services/api';

const HomePage: React.FC = () => {
  const { result, loading, error, setResult, setOriginalImage, setLoading, setError } = useUpload();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [showMeasurementModal, setShowMeasurementModal] = useState(false);
  const [measurements, setMeasurements] = useState({
    totalArea: '',
    floorHeight: '3.0',
    wallThickness: '0.23'
  });

  // Reset file input when result is cleared
  useEffect(() => {
    if (!result && fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  }, [result]);

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setLoading(true);
    setError(null);
    setOriginalImage(null);
    setResult(null);

    try {
      const reader = new FileReader();
      reader.onload = (e) => setOriginalImage(e.target?.result as string);
      reader.readAsDataURL(file);

      const processResult = await uploadFloorPlan(file);
      setResult(processResult);

      if (!processResult.success) {
        setError(processResult.message || 'Processing failed');
      } else {
        setShowMeasurementModal(true);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed');
    } finally {
      setLoading(false);
    }
  };

  const handleNewAnalysis = () => {
    setResult(null);
    setOriginalImage(null);
    setError(null);
    // Reset file input
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleSaveMeasurements = () => {
    const data = {
      totalArea: measurements.totalArea ? parseFloat(measurements.totalArea) : null,
      floorHeight: parseFloat(measurements.floorHeight),
      wallThickness: parseFloat(measurements.wallThickness),
      timestamp: new Date().toISOString()
    };
    localStorage.setItem('floorplan_measurements', JSON.stringify(data));
    setShowMeasurementModal(false);
  };

  // Success State - Modern Gradient UI
  if (result && result.success) {
    return (
      <div className="space-y-8">
        {/* Measurement Modal */}
        {showMeasurementModal && (
          <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50">
            <div className="bg-gradient-to-br from-slate-900 to-slate-800 border border-indigo-500/30 rounded-3xl p-8 max-w-md w-full mx-4 shadow-2xl shadow-indigo-500/10">
              <div className="flex items-center gap-3 mb-6">
                <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-500 flex items-center justify-center">
                  <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 7h6m0 10v-3m-3 3h.01M9 17h.01M9 14h.01M12 14h.01M15 11h.01M12 11h.01M9 11h.01M7 21h10a2 2 0 002-2V5a2 2 0 00-2-2H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                  </svg>
                </div>
                <div>
                  <h3 className="text-xl font-bold text-white">Add Measurements</h3>
                  <p className="text-slate-400 text-sm">For accurate cost estimation</p>
                </div>
              </div>

              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">Total Area (m²)</label>
                  <input
                    type="number"
                    value={measurements.totalArea}
                    onChange={(e) => setMeasurements({...measurements, totalArea: e.target.value})}
                    className="w-full px-4 py-3 bg-slate-800/50 border border-slate-700 rounded-xl text-white placeholder-slate-500 focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all"
                    placeholder="e.g., 150"
                  />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-slate-300 mb-2">Floor Height (m)</label>
                    <input
                      type="number"
                      value={measurements.floorHeight}
                      onChange={(e) => setMeasurements({...measurements, floorHeight: e.target.value})}
                      className="w-full px-4 py-3 bg-slate-800/50 border border-slate-700 rounded-xl text-white focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-slate-300 mb-2">Wall Thickness (m)</label>
                    <input
                      type="number"
                      value={measurements.wallThickness}
                      onChange={(e) => setMeasurements({...measurements, wallThickness: e.target.value})}
                      className="w-full px-4 py-3 bg-slate-800/50 border border-slate-700 rounded-xl text-white focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all"
                    />
                  </div>
                </div>
              </div>

              <div className="flex gap-4 mt-8">
                <button
                  onClick={() => { localStorage.removeItem('floorplan_measurements'); setShowMeasurementModal(false); }}
                  className="flex-1 px-4 py-3 border border-slate-600 text-slate-300 rounded-xl hover:bg-slate-800 transition-all"
                >
                  Skip
                </button>
                <button
                  onClick={handleSaveMeasurements}
                  className="flex-1 px-4 py-3 bg-gradient-to-r from-indigo-600 to-purple-600 text-white rounded-xl hover:from-indigo-500 hover:to-purple-500 transition-all font-medium"
                >
                  Save & Continue
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Success Banner with Gradient */}
        <div className="relative overflow-hidden bg-gradient-to-r from-emerald-500/20 via-teal-500/20 to-cyan-500/20 border border-emerald-500/30 rounded-2xl p-6">
          <div className="absolute inset-0 bg-gradient-to-r from-emerald-500/5 to-cyan-500/5"></div>
          <div className="relative flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-emerald-400 to-teal-500 flex items-center justify-center shadow-lg shadow-emerald-500/30">
                <svg className="w-7 h-7 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
                </svg>
              </div>
              <div>
                <h2 className="text-2xl font-bold text-white">Analysis Complete!</h2>
                <p className="text-emerald-300/80 text-sm mt-1">Your floor plan has been processed by AI</p>
              </div>
            </div>
            <button
              onClick={() => setShowMeasurementModal(true)}
              className="px-4 py-2 text-sm text-emerald-300 hover:text-white border border-emerald-500/30 rounded-lg hover:bg-emerald-500/20 transition-all"
            >
              Edit Measurements
            </button>
          </div>
        </div>

        {/* Stats Cards with Gradients */}
        <div className="grid grid-cols-3 gap-6">
          <div className="relative overflow-hidden bg-gradient-to-br from-slate-900 to-slate-800 border border-indigo-500/20 rounded-2xl p-6 group hover:border-indigo-500/40 transition-all">
            <div className="absolute top-0 right-0 w-32 h-32 bg-gradient-to-br from-indigo-500/10 to-transparent rounded-full -translate-y-1/2 translate-x-1/2"></div>
            <div className="relative">
              <div className="text-4xl font-bold bg-gradient-to-r from-indigo-400 to-purple-400 bg-clip-text text-transparent">
                {result.meta?.num_walls || result.snapped_segments?.length || 0}
              </div>
              <div className="text-slate-400 text-sm mt-2 font-medium">Walls Detected</div>
            </div>
          </div>
          <div className="relative overflow-hidden bg-gradient-to-br from-slate-900 to-slate-800 border border-cyan-500/20 rounded-2xl p-6 group hover:border-cyan-500/40 transition-all">
            <div className="absolute top-0 right-0 w-32 h-32 bg-gradient-to-br from-cyan-500/10 to-transparent rounded-full -translate-y-1/2 translate-x-1/2"></div>
            <div className="relative">
              <div className="text-4xl font-bold bg-gradient-to-r from-cyan-400 to-teal-400 bg-clip-text text-transparent">
                {result.meta?.total_length ? Number(result.meta.total_length).toFixed(1) : '0'}m
              </div>
              <div className="text-slate-400 text-sm mt-2 font-medium">Total Length</div>
            </div>
          </div>
          <div className="relative overflow-hidden bg-gradient-to-br from-slate-900 to-slate-800 border border-amber-500/20 rounded-2xl p-6 group hover:border-amber-500/40 transition-all">
            <div className="absolute top-0 right-0 w-32 h-32 bg-gradient-to-br from-amber-500/10 to-transparent rounded-full -translate-y-1/2 translate-x-1/2"></div>
            <div className="relative">
              <div className="text-4xl font-bold bg-gradient-to-r from-amber-400 to-orange-400 bg-clip-text text-transparent">
                {result.meta?.total_volume ? Number(result.meta.total_volume).toFixed(1) : '0'}m³
              </div>
              <div className="text-slate-400 text-sm mt-2 font-medium">Volume</div>
            </div>
          </div>
        </div>

        {/* Action Cards */}
        <div className="grid grid-cols-2 gap-6">
          <Link to="/detection" className="group relative overflow-hidden bg-gradient-to-br from-slate-900 to-slate-800 border border-slate-700 rounded-2xl p-6 hover:border-indigo-500/50 transition-all hover:shadow-lg hover:shadow-indigo-500/10">
            <div className="absolute inset-0 bg-gradient-to-br from-indigo-500/0 to-indigo-500/5 opacity-0 group-hover:opacity-100 transition-opacity"></div>
            <div className="relative flex items-start gap-4">
              <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-indigo-500/20 to-purple-500/20 flex items-center justify-center group-hover:from-indigo-500/30 group-hover:to-purple-500/30 transition-all">
                <svg className="w-6 h-6 text-indigo-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                </svg>
              </div>
              <div>
                <h3 className="text-lg font-semibold text-white group-hover:text-indigo-400 transition-colors">Detection View</h3>
                <p className="text-slate-400 text-sm mt-1">View AI-detected walls and structure overlay</p>
              </div>
            </div>
          </Link>

          <Link to="/3d-model" className="group relative overflow-hidden bg-gradient-to-br from-slate-900 to-slate-800 border border-slate-700 rounded-2xl p-6 hover:border-cyan-500/50 transition-all hover:shadow-lg hover:shadow-cyan-500/10">
            <div className="absolute inset-0 bg-gradient-to-br from-cyan-500/0 to-cyan-500/5 opacity-0 group-hover:opacity-100 transition-opacity"></div>
            <div className="relative flex items-start gap-4">
              <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-cyan-500/20 to-teal-500/20 flex items-center justify-center group-hover:from-cyan-500/30 group-hover:to-teal-500/30 transition-all">
                <svg className="w-6 h-6 text-cyan-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
                </svg>
              </div>
              <div>
                <h3 className="text-lg font-semibold text-white group-hover:text-cyan-400 transition-colors">3D Model</h3>
                <p className="text-slate-400 text-sm mt-1">Explore interactive 3D visualization</p>
              </div>
            </div>
          </Link>

          <Link to="/materials" className="group relative overflow-hidden bg-gradient-to-br from-slate-900 to-slate-800 border border-slate-700 rounded-2xl p-6 hover:border-amber-500/50 transition-all hover:shadow-lg hover:shadow-amber-500/10">
            <div className="absolute inset-0 bg-gradient-to-br from-amber-500/0 to-amber-500/5 opacity-0 group-hover:opacity-100 transition-opacity"></div>
            <div className="relative flex items-start gap-4">
              <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-amber-500/20 to-orange-500/20 flex items-center justify-center group-hover:from-amber-500/30 group-hover:to-orange-500/30 transition-all">
                <svg className="w-6 h-6 text-amber-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <div>
                <h3 className="text-lg font-semibold text-white group-hover:text-amber-400 transition-colors">Cost Analysis</h3>
                <p className="text-slate-400 text-sm mt-1">Material recommendations & pricing</p>
              </div>
            </div>
          </Link>

          <button
            onClick={handleNewAnalysis}
            className="group relative overflow-hidden bg-gradient-to-br from-slate-900 to-slate-800 border border-slate-700 rounded-2xl p-6 hover:border-emerald-500/50 transition-all hover:shadow-lg hover:shadow-emerald-500/10 text-left"
          >
            <div className="absolute inset-0 bg-gradient-to-br from-emerald-500/0 to-emerald-500/5 opacity-0 group-hover:opacity-100 transition-opacity"></div>
            <div className="relative flex items-start gap-4">
              <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-emerald-500/20 to-green-500/20 flex items-center justify-center group-hover:from-emerald-500/30 group-hover:to-green-500/30 transition-all">
                <svg className="w-6 h-6 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 4v16m8-8H4" />
                </svg>
              </div>
              <div>
                <h3 className="text-lg font-semibold text-white group-hover:text-emerald-400 transition-colors">New Analysis</h3>
                <p className="text-slate-400 text-sm mt-1">Upload a different floor plan</p>
              </div>
            </div>
          </button>
        </div>

        {/* Hidden file input for new uploads */}
        <input
          ref={fileInputRef}
          type="file"
          accept="image/*"
          onChange={handleFileUpload}
          className="hidden"
        />
      </div>
    );
  }

  // Upload State - Premium Landing UI
  return (
    <div className="min-h-[80vh] flex flex-col items-center justify-center px-4">
      {/* Hero Section */}
      <div className="text-center mb-12 max-w-3xl">
        <div className="inline-flex items-center px-4 py-2 bg-gradient-to-r from-indigo-500/10 to-purple-500/10 border border-indigo-500/20 rounded-full mb-6">
          <span className="w-2 h-2 bg-emerald-400 rounded-full mr-2 animate-pulse"></span>
          <span className="text-sm text-indigo-300">AI-Powered Floor Plan Analysis</span>
        </div>
        
        <h1 className="text-5xl font-bold mb-6">
          <span className="bg-gradient-to-r from-white via-indigo-200 to-white bg-clip-text text-transparent">
            Transform Floor Plans
          </span>
          <br />
          <span className="bg-gradient-to-r from-indigo-400 via-purple-400 to-cyan-400 bg-clip-text text-transparent">
            Into 3D Reality
          </span>
        </h1>
        
        <p className="text-slate-400 text-lg max-w-2xl mx-auto leading-relaxed">
          Upload your 2D floor plan and our AI system will analyze it, build a 3D model, 
          and tell you exactly what materials to construct it with — and why.
        </p>
      </div>

      {/* Upload Card */}
      <div
        className="relative w-full max-w-2xl cursor-pointer group"
        onClick={() => !loading && fileInputRef.current?.click()}
      >
        <div className="absolute -inset-1 bg-gradient-to-r from-indigo-500 via-purple-500 to-cyan-500 rounded-3xl opacity-20 group-hover:opacity-40 blur-xl transition-all duration-500"></div>
        
        <div className="relative bg-gradient-to-br from-slate-900 via-slate-900 to-slate-800 border border-slate-700 group-hover:border-indigo-500/50 rounded-3xl p-12 transition-all duration-300">
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            onChange={handleFileUpload}
            className="hidden"
          />

          {!loading && !error && (
            <div className="text-center">
              <div className="w-20 h-20 mx-auto mb-8 rounded-2xl bg-gradient-to-br from-indigo-500/20 to-purple-500/20 flex items-center justify-center group-hover:from-indigo-500/30 group-hover:to-purple-500/30 transition-all">
                <svg className="w-10 h-10 text-indigo-400 group-hover:text-indigo-300 transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                </svg>
              </div>
              <h3 className="text-2xl font-semibold text-white mb-3">Upload Floor Plan</h3>
              <p className="text-slate-400 mb-2">Click to select or drag and drop</p>
              <p className="text-slate-500 text-sm">Supports JPG, PNG, BMP formats</p>
            </div>
          )}

          {loading && (
            <div className="text-center">
              <div className="relative w-20 h-20 mx-auto mb-8">
                <div className="absolute inset-0 rounded-full bg-gradient-to-r from-indigo-500 to-purple-500 animate-spin" style={{clipPath: 'polygon(50% 0%, 100% 0%, 100% 50%, 50% 50%)'}}></div>
                <div className="absolute inset-2 rounded-full bg-slate-900 flex items-center justify-center">
                  <svg className="w-8 h-8 text-indigo-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                  </svg>
                </div>
              </div>
              <h3 className="text-xl font-semibold text-white mb-2">Analyzing Floor Plan...</h3>
              <p className="text-slate-400 text-sm">AI is detecting walls and structures</p>
            </div>
          )}

          {error && (
            <div className="text-center">
              <div className="w-20 h-20 mx-auto mb-8 rounded-2xl bg-red-500/20 flex items-center justify-center">
                <svg className="w-10 h-10 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
              </div>
              <h3 className="text-xl font-semibold text-white mb-2">Upload Failed</h3>
              <p className="text-red-400 text-sm mb-4">{error}</p>
              <button 
                onClick={(e) => { e.stopPropagation(); setError(null); }}
                className="text-indigo-400 hover:text-indigo-300 text-sm underline"
              >
                Try again
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Process Steps */}
      <div className="mt-16 grid grid-cols-3 gap-8 max-w-3xl w-full">
        <div className="text-center group">
          <div className="w-12 h-12 mx-auto mb-4 rounded-xl bg-gradient-to-br from-indigo-500/20 to-indigo-500/10 flex items-center justify-center border border-indigo-500/20 group-hover:border-indigo-500/40 transition-all">
            <span className="text-indigo-400 font-bold">1</span>
          </div>
          <h4 className="text-white font-medium mb-1">Upload</h4>
          <p className="text-slate-500 text-sm">Upload your floor plan image</p>
        </div>
        <div className="text-center group">
          <div className="w-12 h-12 mx-auto mb-4 rounded-xl bg-gradient-to-br from-purple-500/20 to-purple-500/10 flex items-center justify-center border border-purple-500/20 group-hover:border-purple-500/40 transition-all">
            <span className="text-purple-400 font-bold">2</span>
          </div>
          <h4 className="text-white font-medium mb-1">AI Analysis</h4>
          <p className="text-slate-500 text-sm">AI detects walls & structures</p>
        </div>
        <div className="text-center group">
          <div className="w-12 h-12 mx-auto mb-4 rounded-xl bg-gradient-to-br from-cyan-500/20 to-cyan-500/10 flex items-center justify-center border border-cyan-500/20 group-hover:border-cyan-500/40 transition-all">
            <span className="text-cyan-400 font-bold">3</span>
          </div>
          <h4 className="text-white font-medium mb-1">Get Results</h4>
          <p className="text-slate-500 text-sm">3D model + material costs</p>
        </div>
      </div>

      {/* Features */}
      <div className="mt-16 grid grid-cols-3 gap-6 max-w-4xl w-full">
        <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-5 hover:border-slate-700 transition-all">
          <div className="text-2xl mb-3">🏗️</div>
          <h4 className="text-white font-medium mb-1">3D Visualization</h4>
          <p className="text-slate-500 text-sm">Walk through your design in 3D</p>
        </div>
        <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-5 hover:border-slate-700 transition-all">
          <div className="text-2xl mb-3">📊</div>
          <h4 className="text-white font-medium mb-1">Cost Estimation</h4>
          <p className="text-slate-500 text-sm">Accurate material cost analysis</p>
        </div>
        <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-5 hover:border-slate-700 transition-all">
          <div className="text-2xl mb-3">🧱</div>
          <h4 className="text-white font-medium mb-1">Material Guide</h4>
          <p className="text-slate-500 text-sm">Smart recommendations & reasons</p>
        </div>
      </div>
    </div>
  );
};

export default HomePage;
