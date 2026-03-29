import React, { useState } from 'react';
import { useUpload } from '../contexts/UploadContext';
import MaterialRecommendations from '../components/MaterialRecommendations';
import { MaterialComparison } from '../types';

const MaterialsPage: React.FC = () => {
  const { result } = useUpload();
  const [selectedMaterial, setSelectedMaterial] = useState<string | null>(null);

  if (!result) {
    return (
      <div className="text-center py-16">
        <div className="w-16 h-16 mx-auto mb-6 rounded-lg bg-gray-100 flex items-center justify-center">
          <span className="text-3xl">🧱</span>
        </div>
        <h3 className="text-xl font-semibold text-gray-900 mb-2">No Material Data Available</h3>
        <p className="text-gray-500 mb-6 max-w-md mx-auto">
          Please upload a floor plan first to get material recommendations and cost estimates.
        </p>
        <a
          href="/"
          className="inline-flex items-center px-5 py-2.5 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 transition-colors"
        >
          Go to Home Page
        </a>
      </div>
    );
  }

  const totalCost = result.total_construction_cost || 0;
  const costEstimates = result.cost_estimates || [];
  const materialComparisons = result.material_comparisons || [];
  const exteriorWalls = result.graph?.edges.filter(e => e.kind === 'exterior').length || 0;
  const interiorWalls = result.graph?.edges.filter(e => e.kind === 'interior').length || 0;
  const totalRooms = result.graph?.rooms.length || 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-semibold text-gray-900">Material Recommendations & Cost Analysis</h2>
        <p className="text-gray-500 mt-1">
          Cost breakdown and material suggestions for your floor plan.
        </p>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <div className="text-sm text-gray-500 mb-1">Total Construction Cost</div>
          <div className="text-2xl font-bold text-gray-900">
            ₹{totalCost.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
          </div>
        </div>
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <div className="text-sm text-gray-500 mb-1">Exterior Walls</div>
          <div className="text-2xl font-bold text-gray-900">{exteriorWalls}</div>
        </div>
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <div className="text-sm text-gray-500 mb-1">Interior Walls</div>
          <div className="text-2xl font-bold text-gray-900">{interiorWalls}</div>
        </div>
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <div className="text-sm text-gray-500 mb-1">Rooms Detected</div>
          <div className="text-2xl font-bold text-gray-900">{totalRooms}</div>
        </div>
      </div>

      {/* Material Cost Comparison */}
      {materialComparisons.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-100">
            <h3 className="text-lg font-semibold text-gray-900">Material Cost Comparison</h3>
            <p className="text-sm text-gray-500 mt-1">Compare costs across different material options</p>
          </div>
          
          <div className="p-6">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {materialComparisons.map((comparison: MaterialComparison) => (
                <div 
                  key={comparison.material_id}
                  onClick={() => setSelectedMaterial(selectedMaterial === comparison.material_id ? null : comparison.material_id)}
                  className={`rounded-lg border p-5 cursor-pointer transition-all ${
                    selectedMaterial === comparison.material_id 
                      ? 'border-blue-500 bg-blue-50' 
                      : 'border-gray-200 bg-white hover:border-gray-300'
                  }`}
                >
                  <div className="flex justify-between items-start mb-3">
                    <div>
                      <h4 className="font-semibold text-gray-900">{comparison.material_name}</h4>
                      <span className={`inline-block mt-1 px-2 py-0.5 text-xs font-medium rounded ${
                        comparison.rating === 'Budget-Friendly' 
                          ? 'bg-green-100 text-green-700' 
                          : comparison.rating === 'Moderate' 
                            ? 'bg-yellow-100 text-yellow-700' 
                            : 'bg-red-100 text-red-700'
                      }`}>
                        {comparison.rating}
                      </span>
                    </div>
                    <div className="text-right">
                      <div className="text-xl font-bold text-gray-900">
                        ₹{Math.round(comparison.estimated_cost).toLocaleString('en-IN')}
                      </div>
                      <div className="text-xs text-gray-500">
                        ₹{comparison.cost_per_unit}/{comparison.unit}
                      </div>
                    </div>
                  </div>
                  
                  {selectedMaterial === comparison.material_id && (
                    <div className="mt-4 pt-4 border-t border-gray-200 space-y-3">
                      {comparison.pros.length > 0 && (
                        <div>
                          <p className="text-xs font-medium text-green-700 mb-1">Advantages</p>
                          <ul className="text-xs text-gray-600 space-y-1">
                            {comparison.pros.map((pro, idx) => (
                              <li key={idx}>• {pro}</li>
                            ))}
                          </ul>
                        </div>
                      )}
                      {comparison.cons.length > 0 && (
                        <div>
                          <p className="text-xs font-medium text-red-700 mb-1">Considerations</p>
                          <ul className="text-xs text-gray-600 space-y-1">
                            {comparison.cons.map((con, idx) => (
                              <li key={idx}>• {con}</li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Cost Breakdown Table */}
      {costEstimates.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-100">
            <h3 className="text-lg font-semibold text-gray-900">Detailed Cost Breakdown</h3>
            <p className="text-sm text-gray-500 mt-1">Cost analysis by material type</p>
          </div>
          
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 border-b border-gray-100">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Material</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Volume (m³)</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Unit Cost</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Total Cost</th>
                  <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase">Strength</th>
                  <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase">Durability</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {costEstimates.map((estimate, idx) => (
                  <tr key={estimate.material_id} className="hover:bg-gray-50">
                    <td className="px-6 py-4">
                      <div className="font-medium text-gray-900">{estimate.material_name}</div>
                    </td>
                    <td className="px-6 py-4 text-right text-gray-600">{estimate.total_volume_m3}</td>
                    <td className="px-6 py-4 text-right text-gray-600">₹{estimate.unit_cost.toLocaleString('en-IN')}</td>
                    <td className="px-6 py-4 text-right font-semibold text-gray-900">₹{Math.round(estimate.total_cost).toLocaleString('en-IN')}</td>
                    <td className="px-6 py-4 text-center text-gray-600">{estimate.strength || '-'}/10</td>
                    <td className="px-6 py-4 text-center text-gray-600">{estimate.durability || '-'}/10</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Material Recommendations */}
      <MaterialRecommendations result={result} />

      {/* Analysis Context */}
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Analysis Summary</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <h4 className="text-sm font-medium text-gray-700 mb-3">Geometric Data</h4>
            <dl className="space-y-2">
              <div className="flex justify-between py-2 border-b border-gray-100">
                <dt className="text-gray-600">Total Wall Length</dt>
                <dd className="font-medium text-gray-900">
                  {result.graph?.edges?.reduce((sum, e) => sum + e.length_px, 0).toFixed(0) || 0} px
                </dd>
              </div>
              <div className="flex justify-between py-2 border-b border-gray-100">
                <dt className="text-gray-600">Average Wall Length</dt>
                <dd className="font-medium text-gray-900">
                  {result.graph?.edges && result.graph.edges.length > 0 
                    ? (result.graph.edges.reduce((sum, e) => sum + e.length_px, 0) / result.graph.edges.length).toFixed(0)
                    : 0} px
                </dd>
              </div>
              <div className="flex justify-between py-2">
                <dt className="text-gray-600">Max Wall Span</dt>
                <dd className="font-medium text-gray-900">
                  {result.graph?.edges && result.graph.edges.length > 0 
                    ? Math.max(...result.graph.edges.map(e => e.length_px)).toFixed(0)
                    : 0} px
                </dd>
              </div>
            </dl>
          </div>
          <div>
            <h4 className="text-sm font-medium text-gray-700 mb-3">Recommendation Strategy</h4>
            <ul className="space-y-2 text-sm text-gray-600">
              <li className="flex items-center">
                <span className="w-1.5 h-1.5 bg-green-500 rounded-full mr-2"></span>
                Exterior walls prioritized for high-strength materials
              </li>
              <li className="flex items-center">
                <span className="w-1.5 h-1.5 bg-green-500 rounded-full mr-2"></span>
                Interior walls optimized for cost-effectiveness
              </li>
              <li className="flex items-center">
                <span className="w-1.5 h-1.5 bg-green-500 rounded-full mr-2"></span>
                Multi-storey load factors applied when detected
              </li>
            </ul>
          </div>
        </div>
      </div>

      {/* Scoring Info */}
      <div className="bg-gray-50 rounded-xl border border-gray-200 p-6">
        <h3 className="text-sm font-medium text-gray-700 mb-2">Scoring Formula</h3>
        <p className="text-sm text-gray-600">
          <span className="font-mono bg-white px-2 py-1 rounded border border-gray-200">
            Score = (Strength × 0.6 + Durability × 0.4) / Cost
          </span>
          <span className="ml-2">Higher scores indicate better cost-performance ratios.</span>
        </p>
      </div>
    </div>
  );
};

export default MaterialsPage;
