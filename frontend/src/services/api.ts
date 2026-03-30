import axios, { AxiosError } from 'axios';
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
  
  try {
    // Use relative URL - proxy will forward to backend
    const response = await axios.post('/api/process-floorplan', formData, {
      timeout: 60000, // 60 second timeout for large images
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    
    return response.data;
  } catch (error) {
    if (axios.isAxiosError(error)) {
      const axiosError = error as AxiosError;
      
      // Check if it's a network error
      if (!axiosError.response) {
        throw new Error('Network error: Cannot connect to server. Please ensure the backend is running.');
      }
      
      // Check for specific error status codes
      const status = axiosError.response.status;
      const data = axiosError.response.data as any;
      
      if (status === 500) {
        // Server error - try to extract detail
        const detail = data?.detail || data?.message || 'Server processing error';
        throw new Error(`Server error: ${detail}`);
      } else if (status === 400) {
        throw new Error(`Invalid request: ${data?.detail || 'Bad file format'}`);
      } else if (status === 413) {
        throw new Error('File too large. Please upload a smaller image.');
      } else {
        throw new Error(`Request failed with status code ${status}`);
      }
    }
    throw error;
  }
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
