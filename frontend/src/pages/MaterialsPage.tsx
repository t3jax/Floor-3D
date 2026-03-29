import React from 'react';
import { useUpload } from '../contexts/UploadContext';
import MaterialRecommendations from '../components/MaterialRecommendations';

const MaterialsPage: React.FC = () => {
  const { result } = useUpload();

  if (!result) {
    return (
      <div className="text-center py-12">
        <div className="text-gray-400 text-6xl mb-4">🧱</div>
        <h3 className="text-lg font-medium text-gray-900 mb-2">No Material Data Available</h3>
        <p className="text-gray-600 mb-6">
          Please upload a floor plan on the home page first to get material recommendations.
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
        <h2 className="text-2xl font-bold text-gray-900 mb-2">Material Recommendations</h2>
        <p className="text-gray-600">
          Intelligent material suggestions based on cost-strength-durability analysis for your floor plan.
        </p>
      </div>

      {/* Material Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
          <div className="text-2xl font-bold text-gray-900">
            {Object.keys(result.material_recommendations).length}
          </div>
          <div className="text-sm text-gray-600">Categories Analyzed</div>
        </div>
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
          <div className="text-2xl font-bold text-gray-900">
            {result.graph?.edges.filter(e => e.kind === 'exterior').length || 0}
          </div>
          <div className="text-sm text-gray-600">Exterior Walls</div>
        </div>
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
          <div className="text-2xl font-bold text-gray-900">
            {result.graph?.edges.filter(e => e.kind === 'interior').length || 0}
          </div>
          <div className="text-sm text-gray-600">Interior Walls</div>
        </div>
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
          <div className="text-2xl font-bold text-gray-900">{result.graph?.rooms.length || 0}</div>
          <div className="text-sm text-gray-600">Rooms</div>
        </div>
      </div>

      {/* Material Recommendations */}
      <MaterialRecommendations result={result} />

      {/* Scoring Formula */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <h3 className="text-lg font-medium text-gray-900 mb-4">Scoring Formula</h3>
        <div className="bg-gray-50 rounded-lg p-4">
          <div className="text-center">
            <div className="text-lg font-mono font-semibold text-gray-900 mb-2">
              Score = (Strength × 0.6 + Durability × 0.4) / Cost
            </div>
            <p className="text-sm text-gray-600">
              Higher scores indicate better cost-performance ratios. The formula prioritizes strength (60%) 
              while considering durability (40%) and normalizes by cost.
            </p>
          </div>
        </div>
      </div>

      {/* Material Database Info */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <h3 className="text-lg font-medium text-gray-900 mb-4">Available Materials</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <div className="border border-gray-200 rounded-lg p-4">
            <h4 className="font-medium text-gray-900 mb-2">AAC</h4>
            <p className="text-sm text-gray-600">Autoclaved Aerated Concrete</p>
            <p className="text-xs text-gray-500 mt-1">Lightweight, good thermal insulation</p>
          </div>
          <div className="border border-gray-200 rounded-lg p-4">
            <h4 className="font-medium text-gray-900 mb-2">Red Brick</h4>
            <p className="text-sm text-gray-600">Traditional Clay Brick</p>
            <p className="text-xs text-gray-500 mt-1">Widely available, conventional masonry</p>
          </div>
          <div className="border border-gray-200 rounded-lg p-4">
            <h4 className="font-medium text-gray-900 mb-2">RCC</h4>
            <p className="text-sm text-gray-600">Reinforced Cement Concrete</p>
            <p className="text-xs text-gray-500 mt-1">High strength for structural elements</p>
          </div>
          <div className="border border-gray-200 rounded-lg p-4">
            <h4 className="font-medium text-gray-900 mb-2">Steel</h4>
            <p className="text-sm text-gray-600">Structural Steel</p>
            <p className="text-xs text-gray-500 mt-1">Best strength-to-weight ratio</p>
          </div>
          <div className="border border-gray-200 rounded-lg p-4">
            <h4 className="font-medium text-gray-900 mb-2">Fly Ash</h4>
            <p className="text-sm text-gray-600">Fly Ash Brick/Block</p>
            <p className="text-xs text-gray-500 mt-1">Eco-friendly, suitable for partitions</p>
          </div>
          <div className="border border-gray-200 rounded-lg p-4">
            <h4 className="font-medium text-gray-900 mb-2">Precast</h4>
            <p className="text-sm text-gray-600">Precast Concrete</p>
            <p className="text-xs text-gray-500 mt-1">Factory quality, fast construction</p>
          </div>
        </div>
      </div>

      {/* Analysis Context */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <h3 className="text-lg font-medium text-gray-900 mb-4">Analysis Context</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <h4 className="text-sm font-medium text-gray-900 mb-3">Geometric Analysis</h4>
            <dl className="space-y-2 text-sm">
              <div className="flex justify-between">
                <dt className="text-gray-600">Total Wall Length:</dt>
                <dd className="text-gray-900">
                  {result.graph?.edges?.reduce((sum, e) => sum + e.length_px, 0).toFixed(0) || 0} px
                </dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-gray-600">Average Wall Length:</dt>
                <dd className="text-gray-900">
                  {result.graph?.edges && result.graph.edges.length > 0 
                    ? (result.graph.edges.reduce((sum, e) => sum + e.length_px, 0) / result.graph.edges.length).toFixed(0)
                    : 0} px
                </dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-gray-600">Max Wall Span:</dt>
                <dd className="text-gray-900">
                  {result.graph?.edges && result.graph.edges.length > 0 
                    ? Math.max(...result.graph.edges.map(e => e.length_px)).toFixed(0)
                    : 0} px
                </dd>
              </div>
            </dl>
          </div>
          <div>
            <h4 className="text-sm font-medium text-gray-900 mb-3">Recommendation Strategy</h4>
            <ul className="space-y-1 text-sm text-gray-600">
              <li>• Exterior walls prioritized for high-strength materials</li>
              <li>• Interior walls optimized for cost-effectiveness</li>
              <li>• Room-specific recommendations based on size</li>
              <li>• Tradeoff analysis between cost and performance</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
};

export default MaterialsPage;
