import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { UploadProvider } from './contexts/UploadContext';
import Layout from './components/Layout';
import HomePage from './pages/HomePage';
import DetectionPage from './pages/DetectionPage';
import Model3DPage from './pages/Model3DPage';
import MaterialsPage from './pages/MaterialsPage';
import DatabasePage from './pages/DatabasePage';

const App: React.FC = () => {
  return (
    <Router>
      <UploadProvider>
        <Layout>
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/detection" element={<DetectionPage />} />
            <Route path="/3d-model" element={<Model3DPage />} />
            <Route path="/materials" element={<MaterialsPage />} />
            <Route path="/database" element={<DatabasePage />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </Layout>
      </UploadProvider>
    </Router>
  );
};

export default App;
