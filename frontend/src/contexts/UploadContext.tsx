import React, { createContext, useContext, useState, ReactNode } from 'react';
import { ProcessResult } from '../types';

interface UploadContextType {
  result: ProcessResult | null;
  originalImage: string | null;
  loading: boolean;
  error: string | null;
  setResult: (result: ProcessResult | null) => void;
  setOriginalImage: (image: string | null) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
}

const UploadContext = createContext<UploadContextType | undefined>(undefined);

export const useUpload = () => {
  const context = useContext(UploadContext);
  if (context === undefined) {
    throw new Error('useUpload must be used within an UploadProvider');
  }
  return context;
};

interface UploadProviderProps {
  children: ReactNode;
}

export const UploadProvider: React.FC<UploadProviderProps> = ({ children }) => {
  const [result, setResult] = useState<ProcessResult | null>(null);
  const [originalImage, setOriginalImage] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  return (
    <UploadContext.Provider
      value={{
        result,
        originalImage,
        loading,
        error,
        setResult,
        setOriginalImage,
        setLoading,
        setError,
      }}
    >
      {children}
    </UploadContext.Provider>
  );
};
