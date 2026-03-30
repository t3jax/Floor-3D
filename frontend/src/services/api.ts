import axios from 'axios';
import { ProcessResult, Point2D } from '../types';

// In development with proxy, use relative URLs
// In production, adjust as needed
const API_BASE = '';

export const api = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const uploadFloorPlan = async (file: File): Promise<ProcessResult> => {
  const formData = new FormData();
  formData.append('file', file);
  
  // Use relative URL - proxy will forward to backend
  const response = await axios.post('/api/process-floorplan', formData);
  
  return response.data;
};

export const processFallback = async (
  nodes: Point2D[],
  edges: [number, number][],
  rooms?: number[][]
): Promise<ProcessResult> => {
  const payload = {
    nodes,
    edges,
    rooms,
  };
  
  const response = await api.post('/api/process-fallback', payload);
  return response.data;
};

export const getMaterials = async () => {
  const response = await api.get('/api/materials');
  return response.data;
};

export const getTopMaterials = async (k: number = 3) => {
  const response = await api.get(`/api/materials/top?k=${k}`);
  return response.data;
};
