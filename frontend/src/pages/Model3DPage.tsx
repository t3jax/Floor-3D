import React from 'react';
import { useUpload } from '../contexts/UploadContext';
import ThreeViewer from '../components/ThreeViewer';

const Model3DPage: React.FC = () => {
  const { result } = useUpload();

  if (!result || !result.graph) {
    return (
      <div className="text-center py-12">
        <div className="text-gray-400 text-6xl mb-4">🏗️</div>
        <h3 className="text-lg font-medium text-gray-900 mb-2">No 3D Model Available</h3>
        <p className="text-gray-600 mb-6">
          Please upload a floor plan on the home page first to generate a 3D model.
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

  const hasSecondFloor = result.graph.has_second_floor;
  const totalCost = result.total_construction_cost || 0;
  const floorMultiplier = hasSecondFloor ? 2 : 1;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900 mb-2">3D Model Visualization</h2>
          <p className="text-gray-600">
            Interactive 3D representation with {hasSecondFloor ? 'dual-floor' : 'single-floor'} support and Voyager navigation.
          </p>
        </div>
        {hasSecondFloor && (
          <div className="bg-gradient-to-r from-green-400 to-emerald-500 text-white px-4 py-2 rounded-full text-sm font-semibold shadow-lg">
            ✨ Multi-Floor Detected
          </div>
        )}
      </div>

      {/* Model Stats */}
      <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
          <div className="text-2xl font-bold text-gray-900">{result.graph.nodes.length}</div>
          <div className="text-sm text-gray-600">Vertices</div>
        </div>
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
          <div className="text-2xl font-bold text-gray-900">{result.graph.edges.length}</div>
          <div className="text-sm text-gray-600">Wall Segments</div>
        </div>
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
          <div className="text-2xl font-bold text-gray-900">{result.graph.rooms.length}</div>
          <div className="text-sm text-gray-600">Rooms</div>
        </div>
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
          <div className="text-2xl font-bold text-gray-900">{floorMultiplier}</div>
          <div className="text-sm text-gray-600">Floor{floorMultiplier > 1 ? 's' : ''}</div>
        </div>
        <div className="bg-gradient-to-br from-emerald-50 to-green-50 rounded-lg shadow-sm border border-emerald-200 p-4">
          <div className="text-2xl font-bold text-emerald-700">
            ₹{(totalCost * floorMultiplier).toLocaleString('en-IN')}
          </div>
          <div className="text-sm text-emerald-600">Est. Total Cost</div>
        </div>
      </div>

      {/* 3D Viewer */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <div className="mb-4">
          <h3 className="text-lg font-medium text-gray-900 mb-2">Interactive 3D Model</h3>
          <p className="text-sm text-gray-600">
            Orbit view by default • Enter Voyager mode for first-person exploration • Use floor selector to toggle levels
          </p>
        </div>
        <ThreeViewer 
          graph={result.graph} 
          totalCost={totalCost * floorMultiplier}
        />
      </div>

      {/* Wall Classification */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <h3 className="text-lg font-medium text-gray-900 mb-4">Wall Classification</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <h4 className="text-sm font-medium text-gray-900 mb-3">Exterior Walls (Load-Bearing)</h4>
            <div className="space-y-2">
              <div className="flex items-center">
                <div className="w-4 h-4 bg-cyan-600 rounded mr-3"></div>
                <span className="text-sm text-gray-700">Blue wireframe indicates exterior walls</span>
              </div>
              <div className="text-sm text-gray-600">
                Count: {result.graph.edges.filter(e => e.kind === 'exterior').length} walls
                {hasSecondFloor && ` × ${floorMultiplier} floors`}
              </div>
            </div>
          </div>
          <div>
            <h4 className="text-sm font-medium text-gray-900 mb-3">Interior Walls (Partitions)</h4>
            <div className="space-y-2">
              <div className="flex items-center">
                <div className="w-4 h-4 bg-slate-500 rounded mr-3"></div>
                <span className="text-sm text-gray-700">Slate wireframe indicates interior walls</span>
              </div>
              <div className="text-sm text-gray-600">
                Count: {result.graph.edges.filter(e => e.kind === 'interior').length} walls
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Room Information */}
      {result.graph.rooms.length > 0 && (
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <h3 className="text-lg font-medium text-gray-900 mb-4">Detected Rooms</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {result.graph.rooms.map((room) => (
              <div key={room.id} className="border border-gray-200 rounded-lg p-4">
                <h4 className="font-medium text-gray-900 mb-2">{room.id}</h4>
                <dl className="space-y-1 text-sm">
                  <div className="flex justify-between">
                    <dt className="text-gray-600">Area:</dt>
                    <dd className="text-gray-900">{room.area_px.toFixed(0)} px²</dd>
                  </div>
                  <div className="flex justify-between">
                    <dt className="text-gray-600">Vertices:</dt>
                    <dd className="text-gray-900">{room.polygon.length}</dd>
                  </div>
                  <div className="flex justify-between">
                    <dt className="text-gray-600">Center:</dt>
                    <dd className="text-gray-900">
                      ({room.centroid.x.toFixed(0)}, {room.centroid.y.toFixed(0)})
                    </dd>
                  </div>
                </dl>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Controls Help */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-6">
        <h3 className="text-lg font-medium text-blue-900 mb-3">Navigation Controls</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm text-blue-800">
          <div>
            <h4 className="font-medium mb-2">🖱️ Orbit Mode (Default):</h4>
            <ul className="space-y-1">
              <li>• Left-click + drag: Rotate view</li>
              <li>• Right-click + drag: Pan</li>
              <li>• Scroll: Zoom in/out</li>
            </ul>
          </div>
          <div>
            <h4 className="font-medium mb-2">🚀 Voyager Mode:</h4>
            <ul className="space-y-1">
              <li>• WASD: Move forward/left/back/right</li>
              <li>• Mouse: Look around</li>
              <li>• Walk into stairs to climb</li>
              <li>• ESC: Exit Voyager mode</li>
            </ul>
          </div>
          <div>
            <h4 className="font-medium mb-2">🏢 Floor Controls:</h4>
            <ul className="space-y-1">
              <li>• L0: Show only ground floor</li>
              <li>• L1: Show only second floor</li>
              <li>• All: Show entire building</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Model3DPage;
