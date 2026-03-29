import React, { useRef } from 'react';
import { Link } from 'react-router-dom';
import { useUpload } from '../contexts/UploadContext';
import { uploadFloorPlan } from '../services/api';

const HomePage: React.FC = () => {
  const { result, originalImage, loading, error, setResult, setOriginalImage, setLoading, setError } = useUpload();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setLoading(true);
    setError(null);
    setOriginalImage(null);
    setResult(null);

    try {
      // Store original image for comparison
      const reader = new FileReader();
      reader.onload = (e) => {
        setOriginalImage(e.target?.result as string);
      };
      reader.readAsDataURL(file);

      // Upload and process
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
      <div className="space-y-8">
        {/* Success Message */}
        <div className="bg-green-50 border border-green-200 rounded-lg p-6">
          <div className="flex">
            <div className="flex-shrink-0">
              <svg className="h-6 w-6 text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <div className="ml-3">
              <h3 className="text-lg font-medium text-green-800">Floor Plan Processed Successfully!</h3>
              <div className="mt-2 text-sm text-green-700">
                <p>Your floor plan has been analyzed and is ready for exploration.</p>
              </div>
            </div>
          </div>
        </div>

        {/* Stats Overview */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
            <div className="text-2xl font-bold text-gray-900">{result.graph?.nodes.length || 0}</div>
            <div className="text-sm text-gray-600">Nodes Detected</div>
          </div>
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
            <div className="text-2xl font-bold text-gray-900">{result.graph?.edges.length || 0}</div>
            <div className="text-sm text-gray-600">Wall Segments</div>
          </div>
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
            <div className="text-2xl font-bold text-gray-900">{result.graph?.rooms.length || 0}</div>
            <div className="text-sm text-gray-600">Rooms Found</div>
          </div>
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
            <div className="text-2xl font-bold text-gray-900 capitalize">{result.detection_mode}</div>
            <div className="text-sm text-gray-600">Detection Mode</div>
          </div>
        </div>

        {/* Navigation Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <Link
            to="/detection"
            className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 hover:shadow-md transition-shadow"
          >
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <div className="text-3xl">🔍</div>
              </div>
              <div className="ml-4">
                <h3 className="text-lg font-medium text-gray-900">2D Detection Results</h3>
                <p className="text-sm text-gray-600 mt-1">View the detected walls and room boundaries</p>
              </div>
            </div>
          </Link>

          <Link
            to="/3d-model"
            className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 hover:shadow-md transition-shadow"
          >
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <div className="text-3xl">🏗️</div>
              </div>
              <div className="ml-4">
                <h3 className="text-lg font-medium text-gray-900">3D Model</h3>
                <p className="text-sm text-gray-600 mt-1">Interactive 3D visualization of your floor plan</p>
              </div>
            </div>
          </Link>

          <Link
            to="/materials"
            className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 hover:shadow-md transition-shadow"
          >
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <div className="text-3xl">🧱</div>
              </div>
              <div className="ml-4">
                <h3 className="text-lg font-medium text-gray-900">Material Recommendations</h3>
                <p className="text-sm text-gray-600 mt-1">Optimized material suggestions with analysis</p>
              </div>
            </div>
          </Link>
        </div>

        {/* Upload New Button */}
        <div className="text-center">
          <button
            onClick={handleUploadClick}
            className="inline-flex items-center px-6 py-3 border border-transparent shadow-sm text-base font-medium rounded-md text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
          >
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
    <div className="space-y-8">
      {/* Welcome Section */}
      <div className="text-center">
        <h2 className="text-3xl font-bold text-gray-900 mb-4">
          Welcome to ASIS
        </h2>
        <p className="text-lg text-gray-600 max-w-2xl mx-auto">
          Upload a floor plan image to analyze its geometry, generate a 3D model, and receive intelligent material recommendations.
        </p>
      </div>

      {/* Upload Section */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-8">
        <div className="text-center">
          <div className="mx-auto w-24 h-24 bg-primary-100 rounded-full flex items-center justify-center mb-4">
            <svg className="w-12 h-12 text-primary-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
            </svg>
          </div>
          
          <h3 className="text-lg font-medium text-gray-900 mb-2">Upload Floor Plan</h3>
          <p className="text-sm text-gray-600 mb-6">
            Supported formats: PNG, JPG, JPEG. Max file size: 10MB
          </p>
          
          <button
            onClick={handleUploadClick}
            disabled={loading}
            className="inline-flex items-center px-6 py-3 border border-transparent shadow-sm text-base font-medium rounded-md text-white bg-primary-600 hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
          >
            {loading ? 'Processing...' : 'Choose File'}
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

      {/* Loading Indicator */}
      {loading && (
        <div className="text-center py-8">
          <div className="loading-spinner mx-auto mb-4"></div>
          <p className="text-gray-600">Processing your floor plan...</p>
        </div>
      )}

      {/* Error Display */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-6">
          <div className="flex">
            <div className="flex-shrink-0">
              <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
              </svg>
            </div>
            <div className="ml-3">
              <h3 className="text-sm font-medium text-red-800">Processing Error</h3>
              <div className="mt-2 text-sm text-red-700">
                <p>{error}</p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Features */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <div className="text-2xl mb-3">🔍</div>
          <h3 className="text-lg font-medium text-gray-900 mb-2">Smart Detection</h3>
          <p className="text-sm text-gray-600">
            Advanced OpenCV algorithms detect walls, rooms, and openings with high precision
          </p>
        </div>
        
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <div className="text-2xl mb-3">🏗️</div>
          <h3 className="text-lg font-medium text-gray-900 mb-2">3D Visualization</h3>
          <p className="text-sm text-gray-600">
            Interactive 3D models with accurate wall representation and room layout
          </p>
        </div>
        
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <div className="text-2xl mb-3">🧱</div>
          <h3 className="text-lg font-medium text-gray-900 mb-2">Material Intelligence</h3>
          <p className="text-sm text-gray-600">
            Optimized material recommendations based on cost-strength-durability analysis
          </p>
        </div>
      </div>
    </div>
  );
};

export default HomePage;
