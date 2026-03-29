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
      reader.onload = (e) => {
        setOriginalImage(e.target?.result as string);
      };
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

  const handleUploadClick = () => {
    fileInputRef.current?.click();
  };

  const handleSaveMeasurements = () => {
    if (result) {
      const measurementData = {
        totalArea: measurements.totalArea ? parseFloat(measurements.totalArea) : null,
        floorHeight: parseFloat(measurements.floorHeight),
        wallThickness: parseFloat(measurements.wallThickness),
        timestamp: new Date().toISOString()
      };
      localStorage.setItem('floorplan_measurements', JSON.stringify(measurementData));
      setShowMeasurementModal(false);
    }
  };

  const handleSkipMeasurements = () => {
    localStorage.removeItem('floorplan_measurements');
    setShowMeasurementModal(false);
  };

  if (result && result.success) {
    return (
      <div className="space-y-6">
        {showMeasurementModal && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white rounded-xl shadow-2xl p-6 max-w-md w-full mx-4">
              <h3 className="text-xl font-bold text-gray-900 mb-2">Add Measurements (Optional)</h3>
              <p className="text-sm text-gray-600 mb-6">
                Provide actual measurements for more accurate cost estimation
              </p>

              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Total Built-Up Area (square meters)
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    value={measurements.totalArea}
                    onChange={(e) => setMeasurements({...measurements, totalArea: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    placeholder="e.g., 150.5"
                  />
                  <p className="text-xs text-gray-500 mt-1">Leave empty to use auto-detected dimensions</p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Floor Height (meters)
                  </label>
                  <input
                    type="number"
                    step="0.1"
                    value={measurements.floorHeight}
                    onChange={(e) => setMeasurements({...measurements, floorHeight: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Wall Thickness (meters)
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    value={measurements.wallThickness}
                    onChange={(e) => setMeasurements({...measurements, wallThickness: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  />
                </div>
              </div>

              <div className="flex gap-3 mt-6">
                <button onClick={handleSkipMeasurements} className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50">
                  Skip
                </button>
                <button onClick={handleSaveMeasurements} className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
                  Save
                </button>
              </div>
            </div>
          </div>
        )}

        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-semibold text-gray-900">Processing Complete</h2>
            <button
              onClick={() => setShowMeasurementModal(true)}
              className="text-sm text-blue-600 hover:text-blue-700 font-medium"
            >
              Edit Measurements
            </button>
          </div>
          <p className="text-gray-600">
            Your floor plan has been analyzed successfully. View the results below:
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="bg-white rounded-xl border border-gray-200 p-6 text-center">
            <div className="text-3xl mb-2">✓</div>
            <div className="text-2xl font-bold text-gray-900 mb-1">
              {result.meta?.num_walls || result.snapped_segments?.length || 0}
            </div>
            <div className="text-sm text-gray-600">Walls Detected</div>
          </div>

          <div className="bg-white rounded-xl border border-gray-200 p-6 text-center">
            <div className="text-3xl mb-2">📐</div>
            <div className="text-2xl font-bold text-gray-900 mb-1">
              {result.meta?.total_length ? Number(result.meta.total_length).toFixed(1) : '0'}m
            </div>
            <div className="text-sm text-gray-600">Total Length</div>
          </div>

          <div className="bg-white rounded-xl border border-gray-200 p-6 text-center">
            <div className="text-3xl mb-2">🏗️</div>
            <div className="text-2xl font-bold text-gray-900 mb-1">
              {result.meta?.total_volume ? Number(result.meta.total_volume).toFixed(1) : '0'}m³
            </div>
            <div className="text-sm text-gray-600">Volume</div>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <Link
            to="/detection"
            className="bg-white rounded-xl border border-gray-200 p-6 hover:shadow-lg transition-shadow"
          >
            <div className="flex items-start">
              <div className="text-3xl mr-4">🔍</div>
              <div>
                <h3 className="text-lg font-semibold text-gray-900 mb-2">
                  Detection Visualization
                </h3>
                <p className="text-sm text-gray-600">
                  View the detected walls and layout structure
                </p>
              </div>
            </div>
          </Link>

          <Link
            to="/3d-model"
            className="bg-white rounded-xl border border-gray-200 p-6 hover:shadow-lg transition-shadow"
          >
            <div className="flex items-start">
              <div className="text-3xl mr-4">🏛️</div>
              <div>
                <h3 className="text-lg font-semibold text-gray-900 mb-2">
                  3D Model
                </h3>
                <p className="text-sm text-gray-600">
                  Explore the interactive 3D visualization
                </p>
              </div>
            </div>
          </Link>

          <Link
            to="/materials"
            className="bg-white rounded-xl border border-gray-200 p-6 hover:shadow-lg transition-shadow"
          >
            <div className="flex items-start">
              <div className="text-3xl mr-4">🧱</div>
              <div>
                <h3 className="text-lg font-semibold text-gray-900 mb-2">
                  Material Analysis
                </h3>
                <p className="text-sm text-gray-600">
                  Review cost estimates and material recommendations
                </p>
              </div>
            </div>
          </Link>

          <button
            onClick={() => {
              setResult(null);
              setOriginalImage(null);
              setError(null);
            }}
            className="bg-white rounded-xl border border-gray-200 p-6 hover:shadow-lg transition-shadow text-left"
          >
            <div className="flex items-start">
              <div className="text-3xl mr-4">📤</div>
              <div>
                <h3 className="text-lg font-semibold text-gray-900 mb-2">
                  Upload New Plan
                </h3>
                <p className="text-sm text-gray-600">
                  Analyze a different floor plan
                </p>
              </div>
            </div>
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto">
      <div className="text-center mb-12">
        <h1 className="text-4xl font-bold text-gray-900 mb-4">
          Floor3D Analysis System
        </h1>
        <p className="text-lg text-gray-600">
          Transform 2D floor plans into interactive 3D models with AI-powered analysis
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-12">
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <div className="text-3xl mb-3">📤</div>
          <h3 className="text-lg font-semibold text-gray-900 mb-2">Upload</h3>
          <p className="text-sm text-gray-600">
            Upload your 2D floor plan image in JPG, PNG, or PDF format
          </p>
        </div>

        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <div className="text-3xl mb-3">🔍</div>
          <h3 className="text-lg font-semibold text-gray-900 mb-2">Analyze</h3>
          <p className="text-sm text-gray-600">
            AI detects walls, rooms, and structural elements automatically
          </p>
        </div>

        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <div className="text-3xl mb-3">🏛️</div>
          <h3 className="text-lg font-semibold text-gray-900 mb-2">Visualize</h3>
          <p className="text-sm text-gray-600">
            Explore interactive 3D models with cost estimates
          </p>
        </div>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 p-8">
        <input
          ref={fileInputRef}
          type="file"
          accept="image/*,.pdf"
          onChange={handleFileUpload}
          className="hidden"
        />

        {!loading && !error && (
          <div className="text-center">
            <div className="mb-6">
              <svg className="mx-auto h-16 w-16 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
              </svg>
            </div>
            <h3 className="text-lg font-semibold text-gray-900 mb-2">
              Upload Your Floor Plan
            </h3>
            <p className="text-sm text-gray-600 mb-6">
              Drag and drop or click to select a file
            </p>
            <button
              onClick={handleUploadClick}
              className="px-6 py-3 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 transition-colors"
            >
              Select File
            </button>
          </div>
        )}

        {loading && (
          <div className="text-center py-8">
            <div className="inline-block animate-spin rounded-full h-12 w-12 border-4 border-blue-600 border-t-transparent mb-4"></div>
            <p className="text-gray-700 font-medium">Analyzing floor plan...</p>
            <p className="text-sm text-gray-500 mt-2">This may take a few moments</p>
          </div>
        )}

        {error && (
          <div className="text-center py-8">
            <div className="text-red-500 text-4xl mb-4">⚠️</div>
            <h3 className="text-lg font-semibold text-gray-900 mb-2">
              Processing Failed
            </h3>
            <p className="text-sm text-red-600 mb-6">{error}</p>
            <button
              onClick={handleUploadClick}
              className="px-6 py-3 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 transition-colors"
            >
              Try Again
            </button>
          </div>
        )}
      </div>

      <div className="mt-8 bg-blue-50 border border-blue-200 rounded-xl p-6">
        <h3 className="text-lg font-semibold text-blue-900 mb-2">
          Supported Features
        </h3>
        <ul className="space-y-2 text-sm text-blue-800">
          <li className="flex items-start">
            <span className="mr-2">✓</span>
            <span>Automatic wall and room detection</span>
          </li>
          <li className="flex items-start">
            <span className="mr-2">✓</span>
            <span>Interactive 3D model visualization with Voyager mode</span>
          </li>
          <li className="flex items-start">
            <span className="mr-2">✓</span>
            <span>Multi-floor support with staircase detection</span>
          </li>
          <li className="flex items-start">
            <span className="mr-2">✓</span>
            <span>Material cost estimation and recommendations</span>
          </li>
          <li className="flex items-start">
            <span className="mr-2">✓</span>
            <span>Professional PDF report generation</span>
          </li>
        </ul>
      </div>
    </div>
  );
};

export default HomePage;
