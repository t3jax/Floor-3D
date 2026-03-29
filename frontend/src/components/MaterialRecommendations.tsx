import React from 'react';
import { ProcessResult, MaterialRecommendation } from '../types';

interface MaterialRecommendationsProps {
  result: ProcessResult | null;
}

const MaterialRecommendations: React.FC<MaterialRecommendationsProps> = ({ result }) => {
  if (!result || !result.material_recommendations) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Material Recommendations</h3>
        <p className="text-gray-500">No material data available</p>
      </div>
    );
  }

  const recommendations = result.material_recommendations;

  // Only show exterior_walls and interior_walls categories
  const filteredRecommendations = Object.entries(recommendations).filter(
    ([key]) => key === 'exterior_walls' || key === 'interior_walls'
  );

  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
      <div className="px-6 py-4 border-b border-gray-100">
        <h3 className="text-lg font-semibold text-gray-900">Material Recommendations</h3>
        <p className="text-sm text-gray-500 mt-1">Best materials ranked by performance-to-cost ratio</p>
      </div>
      
      <div className="p-6 space-y-8">
        {filteredRecommendations.map(([key, materials]) => (
          <div key={key}>
            <h4 className="text-sm font-semibold text-gray-700 mb-4 uppercase tracking-wide">
              {key.replace(/_/g, ' ')}
            </h4>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {materials.slice(0, 3).map((material: MaterialRecommendation, index: number) => (
                <MaterialCard 
                  key={material.material_id} 
                  material={material} 
                  rank={index + 1}
                />
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

interface MaterialCardProps {
  material: MaterialRecommendation;
  rank: number;
}

const MaterialCard: React.FC<MaterialCardProps> = ({ material, rank }) => {
  const getRankLabel = (rank: number) => {
    switch (rank) {
      case 1: return 'Recommended';
      case 2: return 'Alternative';
      case 3: return 'Option';
      default: return '';
    }
  };

  const getRankColor = (rank: number) => {
    switch (rank) {
      case 1: return 'bg-green-50 border-green-200 text-green-700';
      case 2: return 'bg-blue-50 border-blue-200 text-blue-700';
      case 3: return 'bg-gray-50 border-gray-200 text-gray-700';
      default: return 'bg-gray-50 border-gray-200 text-gray-700';
    }
  };

  return (
    <div className={`rounded-lg border p-4 ${rank === 1 ? 'border-green-200 bg-green-50/50' : 'border-gray-200 bg-white'}`}>
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <div>
          <h5 className="font-semibold text-gray-900">{material.name}</h5>
          <span className={`inline-block mt-1 px-2 py-0.5 text-xs font-medium rounded ${getRankColor(rank)}`}>
            {getRankLabel(rank)}
          </span>
        </div>
        <div className="text-right">
          <div className="text-lg font-bold text-gray-900">
            ₹{material.cost_per_unit.toLocaleString('en-IN')}
          </div>
          <div className="text-xs text-gray-500">per unit</div>
        </div>
      </div>
      
      {/* Properties */}
      <div className="space-y-2 pt-3 border-t border-gray-100">
        <div className="flex justify-between text-sm">
          <span className="text-gray-600">Strength</span>
          <span className="font-medium text-gray-900">{material.strength}/10</span>
        </div>
        <div className="flex justify-between text-sm">
          <span className="text-gray-600">Durability</span>
          <span className="font-medium text-gray-900">{material.durability}/10</span>
        </div>
        <div className="flex justify-between text-sm">
          <span className="text-gray-600">Score</span>
          <span className="font-medium text-gray-900">{(material.score * 1000).toFixed(2)}</span>
        </div>
      </div>
    </div>
  );
};

export default MaterialRecommendations;
