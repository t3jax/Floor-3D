import React from 'react';
import { ProcessResult, MaterialRecommendation } from '../types';

interface MaterialRecommendationsProps {
  result: ProcessResult | null;
}

const MaterialRecommendations: React.FC<MaterialRecommendationsProps> = ({ result }) => {
  if (!result || !result.material_recommendations) {
    return (
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <h3 className="text-lg font-semibold text-gray-800 mb-4">Material Recommendations</h3>
        <p className="text-gray-500">No material data available</p>
      </div>
    );
  }

  const recommendations = result.material_recommendations;

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
      <h3 className="text-lg font-semibold text-gray-800 mb-6">Material Recommendations</h3>
      
      <div className="space-y-6">
        {Object.entries(recommendations).map(([key, materials]) => (
          <div key={key} className="border-b border-gray-200 pb-4 last:border-b-0">
            <h4 className="text-md font-medium text-gray-700 mb-3 capitalize">
              {key.replace(/_/g, ' ')}
            </h4>
            <div className="space-y-2">
              {materials.map((material: MaterialRecommendation, index: number) => (
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
  const getScoreColor = (score: number) => {
    if (score >= 0.8) return 'text-green-600';
    if (score >= 0.6) return 'text-yellow-600';
    return 'text-red-600';
  };

  const getRankBadge = (rank: number) => {
    const colors = ['bg-yellow-100 text-yellow-800', 'bg-gray-100 text-gray-800', 'bg-orange-100 text-orange-800'];
    return colors[rank - 1] || 'bg-gray-100 text-gray-800';
  };

  return (
    <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors">
      <div className="flex items-center space-x-3">
        <span className={`px-2 py-1 rounded-full text-xs font-semibold ${getRankBadge(rank)}`}>
          #{rank}
        </span>
        <div>
          <h5 className="font-medium text-gray-800">{material.name}</h5>
          <p className="text-xs text-gray-500">ID: {material.material_id}</p>
        </div>
      </div>
      
      <div className="text-right">
        <div className={`text-sm font-semibold ${getScoreColor(material.score)}`}>
          Score: {material.score.toFixed(4)}
        </div>
        <div className="text-xs text-gray-500 space-y-1">
          <div>Strength: {material.strength}</div>
          <div>Durability: {material.durability}</div>
          <div>Cost: ${material.cost_per_unit}</div>
        </div>
      </div>
    </div>
  );
};

export default MaterialRecommendations;
