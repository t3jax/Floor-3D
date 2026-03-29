import React, { useRef } from 'react';
import { Link } from 'react-router-dom';
import { useUpload } from '../contexts/UploadContext';
import { uploadFloorPlan } from '../services/api';

const HomePage: React.FC = () => {
  const { result, loading, error, setResult, setOriginalImage, setLoading, setError } = useUpload();
  const fileInputRef = useRef<HTMLInputElement>(null);

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

  if (result && result.success) {
    return (
      <div className="space-y-6">
        {/* Success Message */}
        <div className="bg-green-50 border border-green-200 rounded-xl p-5 flex items-center">
          <div className="w-10 h-10 rounded-lg bg-green-100 flex items-center justify-center mr-4">
            <svg className="h-5 w-5 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <div>
            <h3 className="text-base font-semibold text-green-800">Floor Plan Processed Successfully</h3>
            <p className="text-sm text-green-600">Your floor plan has been analyzed and is ready for exploration.</p>
          </div>
        </div>

        {/* Stats Overview */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-white rounded-xl border border-gray-200 p-5">
            <div className="text-2xl font-bold text-gray-900">{result.graph?.nodes.length || 0}</div>
            <div className="text-sm text-gray-500 mt-1">Nodes Detected</div>
          </div>
          <div className="bg-white rounded-xl border border-gray-200 p-5">
            <div className="text-2xl font-bold text-gray-900">{result.graph?.edges.length || 0}</div>
            <div className="text-sm text-gray-500 mt-1">Wall Segments</div>
          </div>
          <div className="bg-white rounded-xl border border-gray-200 p-5">
            <div className="text-2xl font-bold text-gray-900">{result.graph?.rooms.length || 0}</div>
            <div className="text-sm text-gray-500 mt-1">Rooms Found</div>
          </div>
          <div className="bg-white rounded-xl border border-gray-200 p-5">
            <div className="text-lg font-bold text-gray-900 capitalize">{result.detection_mode}</div>
            <div className="text-sm text-gray-500 mt-1">Detection Mode</div>
          </div>
        </div>

        {/* Navigation Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Link
            to="/detection"
            className="bg-white rounded-xl border border-gray-200 p-5 hover:border-blue-300 hover:shadow-md transition-all"
          >
            <div className="flex items-center">
              <div className="w-12 h-12 rounded-lg bg-blue-50 flex items-center justify-center mr-4">
                <svg className="w-6 h-6 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
              </div>
              <div>
                <h3 className="font-semibold text-gray-900">2D Detection</h3>
                <p className="text-sm text-gray-500">View detected walls and boundaries</p>
              </div>
            </div>
          </Link>

          <Link
            to="/3d-model"
            className="bg-white rounded-xl border border-gray-200 p-5 hover:border-blue-300 hover:shadow-md transition-all"
          >
            <div className="flex items-center">
              <div className="w-12 h-12 rounded-lg bg-blue-50 flex items-center justify-center mr-4">
                <svg className="w-6 h-6 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                </svg>
              </div>
              <div>
                <h3 className="font-semibold text-gray-900">3D Model</h3>
                <p className="text-sm text-gray-500">Interactive 3D visualization</p>
              </div>
            </div>
          </Link>

          <Link
            to="/materials"
            className="bg-white rounded-xl border border-gray-200 p-5 hover:border-blue-300 hover:shadow-md transition-all"
          >
            <div className="flex items-center">
              <div className="w-12 h-12 rounded-lg bg-blue-50 flex items-center justify-center mr-4">
                <svg className="w-6 h-6 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 7h6m0 10v-3m-3 3h.01M9 17h.01M9 14h.01M12 14h.01M15 11h.01M12 11h.01M9 11h.01M7 21h10a2 2 0 002-2V5a2 2 0 00-2-2H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                </svg>
              </div>
              <div>
                <h3 className="font-semibold text-gray-900">Materials & Cost</h3>
                <p className="text-sm text-gray-500">Recommendations and estimates</p>
              </div>
            </div>
          </Link>
        </div>

        {/* Upload New Button */}
        <div className="text-center pt-4">
          <button
            onClick={handleUploadClick}
            className="inline-flex items-center px-5 py-2.5 bg-gray-100 text-gray-700 font-medium rounded-lg hover:bg-gray-200 transition-colors"
          >
            <svg className="w-5 h-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
            </svg>
            Upload New Floor Plan
          </button>
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            onChange={handleFileUpload}
            className="hidden"
          />
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Welcome Section */}
      <div className="text-center py-6">
        <h2 className="text-3xl font-bold text-gray-900 mb-3">Welcome to Floor3D</h2>
        <p className="text-gray-600 max-w-xl mx-auto">
          Upload a floor plan image to analyze its geometry, generate a 3D model, and receive intelligent material recommendations.
        </p>
      </div>

      {/* Upload Section */}
      <div className="bg-white rounded-xl border-2 border-dashed border-gray-200 p-10 text-center hover:border-blue-300 transition-colors">
        <div className="mx-auto w-16 h-16 rounded-xl bg-blue-50 flex items-center justify-center mb-6">
          <svg className="w-8 h-8 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
          </svg>
        </div>
        
        <h3 className="text-xl font-semibold text-gray-900 mb-2">Upload Floor Plan</h3>
        <p className="text-gray-500 mb-6">
          Drag and drop or click to select. Supports PNG, JPG, JPEG (max 10MB)
        </p>
        
        <button
          onClick={handleUploadClick}
          disabled={loading}
          className="inline-flex items-center px-6 py-3 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {loading ? 'Processing...' : 'Select File'}
        </button>
        <input
          ref={fileInputRef}
          type="file"
          accept="image/*"
          onChange={handleFileUpload}
          className="hidden"
        />
      </div>

      {/* Loading Indicator */}
      {loading && (
        <div className="text-center py-8">
          <div className="mx-auto w-12 h-12 border-4 border-gray-200 border-t-blue-600 rounded-full animate-spin mb-4"></div>
          <p className="text-gray-600 font-medium">Processing your floor plan...</p>
          <p className="text-gray-500 text-sm mt-1">This may take a few moments</p>
        </div>
      )}

      {/* Error Display */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-5 flex items-center">
          <div className="w-10 h-10 rounded-lg bg-red-100 flex items-center justify-center mr-4">
            <svg className="h-5 w-5 text-red-600" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
            </svg>
          </div>
          <div>
            <h3 className="font-semibold text-red-800">Processing Error</h3>
            <p className="text-sm text-red-600">{error}</p>
          </div>
        </div>
      )}

      {/* Features */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-4">
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <div className="w-10 h-10 rounded-lg bg-blue-50 flex items-center justify-center mb-4">
            <svg className="w-5 h-5 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
          </div>
          <h3 className="font-semibold text-gray-900 mb-2">Smart Detection</h3>
          <p className="text-sm text-gray-500">
            OpenCV algorithms detect walls, rooms, and openings with high precision.
          </p>
        </div>
        
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <div className="w-10 h-10 rounded-lg bg-blue-50 flex items-center justify-center mb-4">
            <svg className="w-5 h-5 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
            </svg>
          </div>
          <h3 className="font-semibold text-gray-900 mb-2">3D Visualization</h3>
          <p className="text-sm text-gray-500">
            Interactive 3D models with accurate wall representation and room layout.
          </p>
        </div>
        
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <div className="w-10 h-10 rounded-lg bg-blue-50 flex items-center justify-center mb-4">
            <svg className="w-5 h-5 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 7h6m0 10v-3m-3 3h.01M9 17h.01M9 14h.01M12 14h.01M15 11h.01M12 11h.01M9 11h.01M7 21h10a2 2 0 002-2V5a2 2 0 00-2-2H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
            </svg>
          </div>
          <h3 className="font-semibold text-gray-900 mb-2">Cost Estimation</h3>
          <p className="text-sm text-gray-500">
            Material recommendations with cost-strength-durability analysis.
          </p>
        </div>
      </div>
    </div>
  );
};

export default HomePage;
