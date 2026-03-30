import React, { useState, useEffect } from 'react';
import axios from 'axios';

interface DatabaseStats {
  total_materials: number;
  total_structural_elements: number;
  total_projects_analyzed: number;
}

interface StructuralElement {
  id: string;
  project_id: string;
  type: string;
  length_px: number;
  real_world_length_m: number;
  thickness_m: number;
  thickness_category: string;
  coordinates: string;
}

interface ScaleRecord {
  project_id: string;
  scale_factor: number;
  scaling_method: string;
  confidence: number;
  created_at: string;
}

interface MaterialRecord {
  id: string;
  name: string;
  cost_per_unit: number;
  unit: string;
  strength: number;
  durability: number;
}

const DatabasePage: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [stats, setStats] = useState<DatabaseStats | null>(null);
  const [elements, setElements] = useState<StructuralElement[]>([]);
  const [scaleRecords, setScaleRecords] = useState<ScaleRecord[]>([]);
  const [materials, setMaterials] = useState<MaterialRecord[]>([]);
  const [activeTab, setActiveTab] = useState<'overview' | 'elements' | 'scale' | 'materials'>('overview');

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setLoading(true);
    try {
      const response = await axios.get('http://localhost:8000/api/database/stats');
      if (response.data.success) {
        setStats(response.data.stats);
        setElements(response.data.recent_elements || []);
        setScaleRecords(response.data.scale_metadata || []);
        setMaterials(response.data.materials || []);
      } else {
        setError(response.data.error || 'Failed to fetch data');
      }
    } catch (err) {
      setError('Failed to connect to database');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="text-center">
          <div className="w-12 h-12 mx-auto mb-4 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin"></div>
          <p className="text-slate-400">Loading database...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white">Database Viewer</h1>
          <p className="text-slate-400 mt-1">Real-time view of stored measurements and data</p>
        </div>
        <button
          onClick={fetchData}
          className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors flex items-center gap-2"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          Refresh
        </button>
      </div>

      {error && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-4 text-red-400">
          {error}
        </div>
      )}

      {/* Stats Cards */}
      <div className="grid grid-cols-3 gap-6">
        <div className="relative overflow-hidden bg-gradient-to-br from-slate-900 to-slate-800 border border-emerald-500/20 rounded-2xl p-6">
          <div className="absolute top-0 right-0 w-24 h-24 bg-gradient-to-br from-emerald-500/10 to-transparent rounded-full -translate-y-1/2 translate-x-1/2"></div>
          <div className="relative">
            <div className="text-4xl font-bold bg-gradient-to-r from-emerald-400 to-teal-400 bg-clip-text text-transparent">
              {stats?.total_projects_analyzed || 0}
            </div>
            <div className="text-slate-400 text-sm mt-2 font-medium">Projects Analyzed</div>
          </div>
        </div>

        <div className="relative overflow-hidden bg-gradient-to-br from-slate-900 to-slate-800 border border-indigo-500/20 rounded-2xl p-6">
          <div className="absolute top-0 right-0 w-24 h-24 bg-gradient-to-br from-indigo-500/10 to-transparent rounded-full -translate-y-1/2 translate-x-1/2"></div>
          <div className="relative">
            <div className="text-4xl font-bold bg-gradient-to-r from-indigo-400 to-purple-400 bg-clip-text text-transparent">
              {stats?.total_structural_elements || 0}
            </div>
            <div className="text-slate-400 text-sm mt-2 font-medium">Structural Elements</div>
          </div>
        </div>

        <div className="relative overflow-hidden bg-gradient-to-br from-slate-900 to-slate-800 border border-amber-500/20 rounded-2xl p-6">
          <div className="absolute top-0 right-0 w-24 h-24 bg-gradient-to-br from-amber-500/10 to-transparent rounded-full -translate-y-1/2 translate-x-1/2"></div>
          <div className="relative">
            <div className="text-4xl font-bold bg-gradient-to-r from-amber-400 to-orange-400 bg-clip-text text-transparent">
              {stats?.total_materials || 0}
            </div>
            <div className="text-slate-400 text-sm mt-2 font-medium">Materials Available</div>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-slate-800">
        <div className="flex gap-1">
          {(['overview', 'elements', 'scale', 'materials'] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-6 py-3 font-medium text-sm rounded-t-lg transition-colors ${
                activeTab === tab
                  ? 'bg-slate-800 text-white border-t border-l border-r border-slate-700'
                  : 'text-slate-400 hover:text-white hover:bg-slate-800/50'
              }`}
            >
              {tab === 'overview' && '📊 Overview'}
              {tab === 'elements' && '🏗️ Structural Elements'}
              {tab === 'scale' && '📏 Scale Data'}
              {tab === 'materials' && '🧱 Materials'}
            </button>
          ))}
        </div>
      </div>

      {/* Tab Content */}
      <div className="bg-slate-900/50 border border-slate-800 rounded-xl overflow-hidden">
        {activeTab === 'overview' && (
          <div className="p-6">
            <h3 className="text-lg font-semibold text-white mb-4">Database Status</h3>
            <div className="grid grid-cols-2 gap-6">
              <div className="space-y-4">
                <div className="flex items-center justify-between p-4 bg-slate-800/50 rounded-lg">
                  <span className="text-slate-400">Database Type</span>
                  <span className="text-white font-medium">SQLite</span>
                </div>
                <div className="flex items-center justify-between p-4 bg-slate-800/50 rounded-lg">
                  <span className="text-slate-400">Status</span>
                  <span className="text-emerald-400 font-medium flex items-center gap-2">
                    <span className="w-2 h-2 bg-emerald-400 rounded-full animate-pulse"></span>
                    Connected
                  </span>
                </div>
                <div className="flex items-center justify-between p-4 bg-slate-800/50 rounded-lg">
                  <span className="text-slate-400">Total Records</span>
                  <span className="text-white font-medium">
                    {(stats?.total_structural_elements || 0) + (stats?.total_projects_analyzed || 0) + (stats?.total_materials || 0)}
                  </span>
                </div>
              </div>
              <div className="bg-slate-800/30 rounded-lg p-4">
                <h4 className="text-sm font-medium text-slate-300 mb-3">What's Stored</h4>
                <ul className="space-y-2 text-sm text-slate-400">
                  <li className="flex items-center gap-2">
                    <span className="w-1.5 h-1.5 bg-emerald-400 rounded-full"></span>
                    Wall coordinates (x1, y1, x2, y2)
                  </li>
                  <li className="flex items-center gap-2">
                    <span className="w-1.5 h-1.5 bg-emerald-400 rounded-full"></span>
                    Real-world dimensions (meters)
                  </li>
                  <li className="flex items-center gap-2">
                    <span className="w-1.5 h-1.5 bg-emerald-400 rounded-full"></span>
                    Scale factors & methods
                  </li>
                  <li className="flex items-center gap-2">
                    <span className="w-1.5 h-1.5 bg-emerald-400 rounded-full"></span>
                    Wall thickness categories
                  </li>
                  <li className="flex items-center gap-2">
                    <span className="w-1.5 h-1.5 bg-emerald-400 rounded-full"></span>
                    Material recommendations
                  </li>
                </ul>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'elements' && (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-slate-800/50">
                <tr>
                  <th className="px-6 py-4 text-left text-xs font-medium text-slate-400 uppercase">Project</th>
                  <th className="px-6 py-4 text-left text-xs font-medium text-slate-400 uppercase">Type</th>
                  <th className="px-6 py-4 text-right text-xs font-medium text-slate-400 uppercase">Length (px)</th>
                  <th className="px-6 py-4 text-right text-xs font-medium text-slate-400 uppercase">Length (m)</th>
                  <th className="px-6 py-4 text-center text-xs font-medium text-slate-400 uppercase">Thickness</th>
                  <th className="px-6 py-4 text-left text-xs font-medium text-slate-400 uppercase">Coordinates</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800">
                {elements.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="px-6 py-12 text-center text-slate-500">
                      No structural elements recorded yet. Upload a floor plan to see data here.
                    </td>
                  </tr>
                ) : (
                  elements.map((el, idx) => (
                    <tr key={idx} className="hover:bg-slate-800/30">
                      <td className="px-6 py-4 text-slate-300 font-mono text-sm">{el.project_id}</td>
                      <td className="px-6 py-4">
                        <span className={`px-2 py-1 text-xs font-medium rounded ${
                          el.type === 'exterior' ? 'bg-indigo-500/20 text-indigo-400' : 'bg-slate-700 text-slate-300'
                        }`}>
                          {el.type || 'wall'}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-right text-slate-300">{el.length_px}</td>
                      <td className="px-6 py-4 text-right text-emerald-400 font-medium">{el.real_world_length_m}m</td>
                      <td className="px-6 py-4 text-center">
                        <span className={`px-2 py-1 text-xs rounded ${
                          el.thickness_category === 'major' ? 'bg-amber-500/20 text-amber-400' : 'bg-slate-700 text-slate-400'
                        }`}>
                          {el.thickness_category || '-'} {el.thickness_m ? `(${el.thickness_m}m)` : ''}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-slate-500 font-mono text-xs max-w-xs truncate">
                        {el.coordinates || '-'}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        )}

        {activeTab === 'scale' && (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-slate-800/50">
                <tr>
                  <th className="px-6 py-4 text-left text-xs font-medium text-slate-400 uppercase">Project</th>
                  <th className="px-6 py-4 text-right text-xs font-medium text-slate-400 uppercase">Scale Factor</th>
                  <th className="px-6 py-4 text-center text-xs font-medium text-slate-400 uppercase">Method</th>
                  <th className="px-6 py-4 text-right text-xs font-medium text-slate-400 uppercase">Confidence</th>
                  <th className="px-6 py-4 text-left text-xs font-medium text-slate-400 uppercase">Created</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800">
                {scaleRecords.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="px-6 py-12 text-center text-slate-500">
                      No scale data recorded yet. Upload a floor plan to see calibration data.
                    </td>
                  </tr>
                ) : (
                  scaleRecords.map((rec, idx) => (
                    <tr key={idx} className="hover:bg-slate-800/30">
                      <td className="px-6 py-4 text-slate-300 font-mono text-sm">{rec.project_id}</td>
                      <td className="px-6 py-4 text-right text-cyan-400 font-medium">{rec.scale_factor}</td>
                      <td className="px-6 py-4 text-center">
                        <span className={`px-3 py-1 text-xs font-medium rounded-full ${
                          rec.scaling_method === 'OCR' 
                            ? 'bg-emerald-500/20 text-emerald-400'
                            : rec.scaling_method === 'HEURISTIC'
                            ? 'bg-amber-500/20 text-amber-400'
                            : 'bg-slate-700 text-slate-400'
                        }`}>
                          {rec.scaling_method}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-right">
                        <div className="flex items-center justify-end gap-2">
                          <div className="w-16 h-2 bg-slate-700 rounded-full overflow-hidden">
                            <div 
                              className="h-full bg-gradient-to-r from-indigo-500 to-purple-500 rounded-full"
                              style={{ width: `${rec.confidence}%` }}
                            ></div>
                          </div>
                          <span className="text-slate-300 text-sm">{rec.confidence}%</span>
                        </div>
                      </td>
                      <td className="px-6 py-4 text-slate-500 text-sm">
                        {rec.created_at ? new Date(rec.created_at).toLocaleString() : '-'}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        )}

        {activeTab === 'materials' && (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-slate-800/50">
                <tr>
                  <th className="px-6 py-4 text-left text-xs font-medium text-slate-400 uppercase">Material</th>
                  <th className="px-6 py-4 text-right text-xs font-medium text-slate-400 uppercase">Cost</th>
                  <th className="px-6 py-4 text-left text-xs font-medium text-slate-400 uppercase">Unit</th>
                  <th className="px-6 py-4 text-center text-xs font-medium text-slate-400 uppercase">Strength</th>
                  <th className="px-6 py-4 text-center text-xs font-medium text-slate-400 uppercase">Durability</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800">
                {materials.map((mat, idx) => (
                  <tr key={idx} className="hover:bg-slate-800/30">
                    <td className="px-6 py-4">
                      <div className="font-medium text-white">{mat.name}</div>
                      <div className="text-xs text-slate-500">{mat.id}</div>
                    </td>
                    <td className="px-6 py-4 text-right text-emerald-400 font-medium">
                      ₹{mat.cost_per_unit}
                    </td>
                    <td className="px-6 py-4 text-slate-400 text-sm">{mat.unit}</td>
                    <td className="px-6 py-4 text-center">
                      <div className="flex items-center justify-center gap-2">
                        <div className="w-12 h-2 bg-slate-700 rounded-full overflow-hidden">
                          <div 
                            className="h-full bg-gradient-to-r from-indigo-500 to-purple-500 rounded-full"
                            style={{ width: `${mat.strength}%` }}
                          ></div>
                        </div>
                        <span className="text-slate-300 text-xs w-8">{mat.strength}</span>
                      </div>
                    </td>
                    <td className="px-6 py-4 text-center">
                      <div className="flex items-center justify-center gap-2">
                        <div className="w-12 h-2 bg-slate-700 rounded-full overflow-hidden">
                          <div 
                            className="h-full bg-gradient-to-r from-cyan-500 to-teal-500 rounded-full"
                            style={{ width: `${mat.durability}%` }}
                          ></div>
                        </div>
                        <span className="text-slate-300 text-xs w-8">{mat.durability}</span>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Info Box */}
      <div className="bg-gradient-to-r from-indigo-500/10 to-purple-500/10 border border-indigo-500/20 rounded-xl p-6">
        <div className="flex items-start gap-4">
          <div className="w-10 h-10 rounded-lg bg-indigo-500/20 flex items-center justify-center flex-shrink-0">
            <svg className="w-5 h-5 text-indigo-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <div>
            <h4 className="text-white font-medium mb-1">Data Storage Demo</h4>
            <p className="text-slate-400 text-sm">
              This page shows real-time data from your SQLite database. Every floor plan you upload stores:
              wall coordinates, real-world measurements (in meters), scale factors from AI analysis, 
              and material recommendations. Use this page to demonstrate that your system properly persists all analyzed data.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default DatabasePage;
