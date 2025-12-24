import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor - add auth token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor - handle errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('access_token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export default api;

// Auth APIs
export const authApi = {
  login: (username: string, password: string) =>
    api.post('/auth/login', { username, password }),
  register: (data: { username: string; email: string; password: string; full_name?: string }) =>
    api.post('/auth/register', data),
  me: () => api.get('/auth/me'),
  refresh: (refresh_token: string) =>
    api.post('/auth/refresh', { refresh_token }),
};

// Knowledge Base APIs
export const kbApi = {
  list: (page = 1, pageSize = 20) =>
    api.get('/knowledge-bases', { params: { page, page_size: pageSize } }),
  get: (id: string) => api.get(`/knowledge-bases/${id}`),
  create: (data: { name: string; description?: string; visibility?: string }) =>
    api.post('/knowledge-bases', data),
  update: (id: string, data: { name?: string; description?: string }) =>
    api.put(`/knowledge-bases/${id}`, data),
  delete: (id: string) => api.delete(`/knowledge-bases/${id}`),
  stats: (id: string) => api.get(`/knowledge-bases/${id}/statistics`),
};

// Document APIs
export const docApi = {
  list: (kbId: string, page = 1, pageSize = 20) =>
    api.get(`/knowledge-bases/${kbId}/documents`, { params: { page, page_size: pageSize } }),
  get: (kbId: string, docId: string) =>
    api.get(`/knowledge-bases/${kbId}/documents/${docId}`),
  upload: (kbId: string, file: File, description?: string) => {
    const formData = new FormData();
    formData.append('file', file);
    if (description) formData.append('description', description);
    return api.post(`/knowledge-bases/${kbId}/documents/upload`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },
  delete: (kbId: string, docId: string) =>
    api.delete(`/knowledge-bases/${kbId}/documents/${docId}`),
  reprocess: (kbId: string, docId: string) =>
    api.post(`/knowledge-bases/${kbId}/documents/${docId}/reprocess`),
};

// Search APIs
export const searchApi = {
  search: (kbId: string, query: string, topK = 10, searchType = 'hybrid') =>
    api.post(`/knowledge-bases/${kbId}/search`, {
      query,
      top_k: topK,
      search_type: searchType,
    }),
};

// Model Config APIs
export const modelApi = {
  list: (page = 1, pageSize = 20) =>
    api.get('/model-configs', { params: { page, page_size: pageSize } }),
  get: (id: string) => api.get(`/model-configs/${id}`),
  create: (data: any) => api.post('/model-configs', data),
  update: (id: string, data: any) => api.put(`/model-configs/${id}`, data),
  delete: (id: string) => api.delete(`/model-configs/${id}`),
  test: (id: string) => api.post(`/model-configs/${id}/test`),
};

// Admin APIs
export const adminApi = {
  users: (page = 1, pageSize = 20) =>
    api.get('/admin/users', { params: { page, page_size: pageSize } }),
  stats: () => api.get('/admin/statistics'),
};
