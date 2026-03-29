import React, { useRef, useState } from 'react';
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

  // Success State
  if (result && result.success) {
    return (
      <div className="space-y-8">
        {/* Measurement Modal */}
        {showMeasurementModal && (
          <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50">
            <div className="bg-slate-900 border border-slate-700 rounded-2xl p-8 max-w-md w-full mx-4">
              <h3 className="text-xl font-semibold text-white mb-2">Add Measurements</h3>
              <p className="text-slate-400 text-sm mb-6">Optional: For accurate cost estimation</p>

              <div className="space-y-4">
                <div>
                  <label className="block text-sm text-slate-300 mb-2">Total Area (m²)</label>
                  <input
                    type="number"
                    value={measurements.totalArea}
                    onChange={(e) => setMeasurements({...measurements, totalArea: e.target.value})}
                    className="w-full px-4 py-3 bg-slate-800 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                    placeholder="e.g., 150"
                  />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm text-slate-300 mb-2">Floor Height (m)</label>
                    <input
                      type="number"
                      value={measurements.floorHeight}
                      onChange={(e) => setMeasurements({...measurements, floorHeight: e.target.value})}
                      className="w-full px-4 py-3 bg-slate-800 border border-slate-700 rounded-lg text-white focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                    />
                  </div>
                  <div>
                    <label className="block text-sm text-slate-300 mb-2">Wall Thickness (m)</label>
                    <input
                      type="number"
                      value={measurements.wallThickness}
                      onChange={(e) => setMeasurements({...measurements, wallThickness: e.target.value})}
                      className="w-full px-4 py-3 bg-slate-800 border border-slate-700 rounded-lg text-white focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                    />
                  </div>
                </div>
              </div>

              <div className="flex gap-4 mt-8">
                <button
                  onClick={() => { localStorage.removeItem('floorplan_measurements'); setShowMeasurementModal(false); }}
                  className="flex-1 px-4 py-3 border border-slate-600 text-slate-300 rounded-lg hover:bg-slate-800 transition-colors"
                >
                  Skip
                </button>
                <button
                  onClick={handleSaveMeasurements}
                  className="flex-1 px-4 py-3 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors"
                >
                  Save
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Success Banner */}
        <div className="bg-emerald-500/10 border border-emerald-500/30 rounded-xl p-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <div className="w-12 h-12 rounded-full bg-emerald-500/20 flex items-center justify-center">
                <svg className="w-6 h-6 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              </div>
              <div>
                <h2 className="text-xl font-semibold text-white">Analysis Complete</h2>
                <p className="text-slate-400 text-sm">Floor plan processed successfully</p>
              </div>
            </div>
            <button
              onClick={() => setShowMeasurementModal(true)}
              className="text-sm text-indigo-400 hover:text-indigo-300"
            >
              Edit Measurements
            </button>
          </div>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-3 gap-6">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
            <div className="text-3xl font-bold text-white">{result.meta?.num_walls || result.snapped_segments?.length || 0}</div>
            <div className="text-slate-400 text-sm mt-1">Walls Detected</div>
          </div>
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
            <div className="text-3xl font-bold text-white">{result.meta?.total_length ? Number(result.meta.total_length).toFixed(1) : '0'}m</div>
            <div className="text-slate-400 text-sm mt-1">Total Length</div>
          </div>
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
            <div className="text-3xl font-bold text-white">{result.meta?.total_volume ? Number(result.meta.total_volume).toFixed(1) : '0'}m³</div>
            <div className="text-slate-400 text-sm mt-1">Volume</div>
          </div>
        </div>

        {/* Action Cards */}
        <div className="grid grid-cols-2 gap-6">
          <Link to="/detection" className="group bg-slate-900 border border-slate-800 rounded-xl p-6 hover:border-indigo-500/50 transition-colors">
            <h3 className="text-lg font-semibold text-white group-hover:text-indigo-400 transition-colors">Detection View</h3>
            <p className="text-slate-400 text-sm mt-2">View detected walls and structure</p>
          </Link>
          <Link to="/3d-model" className="group bg-slate-900 border border-slate-800 rounded-xl p-6 hover:border-indigo-500/50 transition-colors">
            <h3 className="text-lg font-semibold text-white group-hover:text-indigo-400 transition-colors">3D Model</h3>
            <p className="text-slate-400 text-sm mt-2">Explore interactive 3D visualization</p>
          </Link>
          <Link to="/materials" className="group bg-slate-900 border border-slate-800 rounded-xl p-6 hover:border-indigo-500/50 transition-colors">
            <h3 className="text-lg font-semibold text-white group-hover:text-indigo-400 transition-colors">Cost Analysis</h3>
            <p className="text-slate-400 text-sm mt-2">Material recommendations & pricing</p>
          </Link>
          <button
            onClick={() => { setResult(null); setOriginalImage(null); setError(null); }}
            className="group bg-slate-900 border border-slate-800 rounded-xl p-6 hover:border-indigo-500/50 transition-colors text-left"
          >
            <h3 className="text-lg font-semibold text-white group-hover:text-indigo-400 transition-colors">New Analysis</h3>
            <p className="text-slate-400 text-sm mt-2">Upload a different floor plan</p>
          </button>
        </div>
      </div>
    );
  }

  // Upload State
  return (
    <div className="max-w-2xl mx-auto pt-20">
      <div className="text-center mb-12">
        <h1 className="text-4xl font-bold text-white mb-4">Floor3D</h1>
        <p className="text-slate-400 text-lg">Transform 2D floor plans into 3D models with AI</p>
      </div>

      <div
        className="bg-slate-900 border-2 border-dashed border-slate-700 rounded-2xl p-16 hover:border-indigo-500/50 transition-colors cursor-pointer"
        onClick={() => fileInputRef.current?.click()}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept="image/*"
          onChange={handleFileUpload}
          className="hidden"
        />

        {!loading && !error && (
          <div className="text-center">
            <div className="w-16 h-16 mx-auto mb-6 rounded-full bg-slate-800 flex items-center justify-center">
              <svg className="w-8 h-8 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
              </svg>
            </div>
            <h3 className="text-xl font-semibold text-white mb-2">Upload Floor Plan</h3>
            <p className="text-slate-400">Click to select or drag and drop</p>
            <p className="text-slate-500 text-sm mt-4">Supports JPG, PNG</p>
          </div>
        )}

        {loading && (
          <div className="text-center">
            <div className="w-12 h-12 mx-auto mb-4 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin"></div>
            <p className="text-white font-medium">Analyzing floor plan...</p>
          </div>
        )}

        {error && (
          <div className="text-center">
            <div className="w-12 h-12 mx-auto mb-4 rounded-full bg-red-500/20 flex items-center justify-center">
              <svg className="w-6 h-6 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </div>
            <p className="text-white font-medium mb-2">Upload Failed</p>
            <p className="text-red-400 text-sm">{error}</p>
          </div>
        )}
      </div>

      <div className="mt-12 grid grid-cols-3 gap-6 text-center">
        <div>
          <div className="text-indigo-400 font-semibold mb-1">Step 1</div>
          <div className="text-slate-400 text-sm">Upload floor plan</div>
        </div>
        <div>
          <div className="text-indigo-400 font-semibold mb-1">Step 2</div>
          <div className="text-slate-400 text-sm">AI detects walls</div>
        </div>
        <div>
          <div className="text-indigo-400 font-semibold mb-1">Step 3</div>
          <div className="text-slate-400 text-sm">View 3D model</div>
        </div>
      </div>
    </div>
  );
};

export default HomePage;
