import { createBrowserRouter, Navigate } from 'react-router-dom';
import MainLayout from '../layouts/MainLayout';
import LoginPage from '../pages/Login';
import KnowledgeBasesPage from '../pages/KnowledgeBases';
import DocumentsPage from '../pages/Documents';
import SearchPage from '../pages/Search';
import ModelConfigsPage from '../pages/ModelConfigs';

const router = createBrowserRouter([
  {
    path: '/login',
    element: <LoginPage />,
  },
  {
    path: '/',
    element: <MainLayout />,
    children: [
      {
        index: true,
        element: <Navigate to="/knowledge-bases" replace />,
      },
      {
        path: 'knowledge-bases',
        element: <KnowledgeBasesPage />,
      },
      {
        path: 'knowledge-bases/:kbId',
        element: <DocumentsPage />,
      },
      {
        path: 'knowledge-bases/:kbId/search',
        element: <SearchPage />,
      },
      {
        path: 'model-configs',
        element: <ModelConfigsPage />,
      },
      {
        path: 'settings',
        element: <div style={{ padding: 24 }}>设置页面（开发中）</div>,
      },
    ],
  },
]);

export default router;
