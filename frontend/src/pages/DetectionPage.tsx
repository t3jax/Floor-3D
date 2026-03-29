import React from 'react';
import { useUpload } from '../contexts/UploadContext';
import ImageViewer from '../components/ImageViewer';

const DetectionPage: React.FC = () => {
  const { result, originalImage } = useUpload();

  if (!result) {
    return (
      <div className="text-center py-12">
        <div className="text-gray-400 text-6xl mb-4">🔍</div>
        <h3 className="text-lg font-medium text-gray-900 mb-2">No Detection Data Available</h3>
        <p className="text-gray-600 mb-6">
          Please upload a floor plan on the home page first to see detection results.
        </p>
        <a
          href="/"
          className="inline-flex items-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-primary-600 hover:bg-primary-700"
        >
          Go to Home Page
        </a>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-gray-900 mb-2">2D Detection Results</h2>
        <p className="text-gray-600">
          View the detected walls, nodes, and room boundaries from your floor plan analysis.
        </p>
      </div>

      {/* Detection Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
          <div className="text-2xl font-bold text-gray-900">{result.graph?.nodes.length || 0}</div>
          <div className="text-sm text-gray-600">Nodes Detected</div>
        </div>
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
          <div className="text-2xl font-bold text-gray-900">{result.raw_lines.length}</div>
          <div className="text-sm text-gray-600">Raw Lines</div>
        </div>
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
          <div className="text-2xl font-bold text-gray-900">{result.snapped_segments.length}</div>
          <div className="text-sm text-gray-600">Snapped Segments</div>
        </div>
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
          <div className="text-2xl font-bold text-gray-900">{result.graph?.rooms.length || 0}</div>
          <div className="text-sm text-gray-600">Rooms Found</div>
        </div>
      </div>

      {/* Detection Visualization */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <h3 className="text-lg font-medium text-gray-900 mb-4">Detection Visualization</h3>
        <ImageViewer result={result} originalImage={originalImage} />
      </div>

      {/* Legend */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <h3 className="text-lg font-medium text-gray-900 mb-4">Legend</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="space-y-2">
            <div className="flex items-center">
              <div className="w-4 h-1 bg-blue-500 mr-3"></div>
              <span className="text-sm text-gray-700">Snapped Wall Segments</span>
            </div>
            <div className="flex items-center">
              <div className="w-4 h-1 bg-red-400 mr-3 opacity-30"></div>
              <span className="text-sm text-gray-700">Raw Detected Lines</span>
            </div>
          </div>
          <div className="space-y-2">
            <div className="flex items-center">
              <div className="w-3 h-3 bg-green-500 rounded-full mr-3"></div>
              <span className="text-sm text-gray-700">Nodes/Junction Points</span>
            </div>
            <div className="flex items-center">
              <div className="w-4 h-4 bg-yellow-200 border border-yellow-400 mr-3"></div>
              <span className="text-sm text-gray-700">Detected Rooms</span>
            </div>
          </div>
        </div>
      </div>

      {/* Technical Details */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <h3 className="text-lg font-medium text-gray-900 mb-4">Technical Details</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <h4 className="text-sm font-medium text-gray-900 mb-2">Detection Parameters</h4>
            <dl className="space-y-1">
              <div className="flex justify-between text-sm">
                <dt className="text-gray-600">Detection Mode:</dt>
                <dd className="text-gray-900 capitalize">{result.detection_mode}</dd>
              </div>
              <div className="flex justify-between text-sm">
                <dt className="text-gray-600">Snap Tolerance:</dt>
                <dd className="text-gray-900">{result.meta?.snap_tolerance_px || 10}px</dd>
              </div>
              <div className="flex justify-between text-sm">
                <dt className="text-gray-600">Image Shape:</dt>
                <dd className="text-gray-900">
                  {result.meta?.image_shape ? `${result.meta.image_shape[1]}×${result.meta.image_shape[0]}` : 'N/A'}
                </dd>
              </div>
            </dl>
          </div>
          <div>
            <h4 className="text-sm font-medium text-gray-900 mb-2">Wall Classification</h4>
            <dl className="space-y-1">
              <div className="flex justify-between text-sm">
                <dt className="text-gray-600">Exterior Walls:</dt>
                <dd className="text-gray-900">
                  {result.graph?.edges.filter(e => e.kind === 'exterior').length || 0}
                </dd>
              </div>
              <div className="flex justify-between text-sm">
                <dt className="text-gray-600">Interior Walls:</dt>
                <dd className="text-gray-900">
                  {result.graph?.edges.filter(e => e.kind === 'interior').length || 0}
                </dd>
              </div>
              <div className="flex justify-between text-sm">
                <dt className="text-gray-600">Total Segments:</dt>
                <dd className="text-gray-900">{result.graph?.edges.length || 0}</dd>
              </div>
            </dl>
          </div>
        </div>
      </div>
    </div>
  );
};

export default DetectionPage;
