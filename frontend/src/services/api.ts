import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

const AUTH_WHITELIST = ['/auth/login', '/auth/register', '/auth/refresh'];

let isRefreshing = false;
let pendingQueue: Array<{
  resolve: (token: string) => void;
  reject: (err: unknown) => void;
}> = [];

function processQueue(error: unknown, token: string | null) {
  pendingQueue.forEach(({ resolve, reject }) => {
    if (error || !token) {
      reject(error);
    } else {
      resolve(token);
    }
  });
  pendingQueue = [];
}

function clearAuthAndRedirect() {
  localStorage.removeItem('access_token');
  localStorage.removeItem('refresh_token');
  if (!window.location.pathname.startsWith('/login')) {
    window.location.href = '/login';
  }
}

function toSkipLimit(page = 1, pageSize = 20) {
  return { skip: (page - 1) * pageSize, limit: pageSize };
}

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

// Response interceptor - refresh on 401, whitelist auth endpoints
api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & {
      _retry?: boolean;
    };
    const status = error.response?.status;
    const url = originalRequest?.url || '';

    const isWhitelisted = AUTH_WHITELIST.some((path) => url.includes(path));
    if (status !== 401 || isWhitelisted || !originalRequest) {
      return Promise.reject(error);
    }

    if (originalRequest._retry) {
      clearAuthAndRedirect();
      return Promise.reject(error);
    }

    const refreshToken = localStorage.getItem('refresh_token');
    if (!refreshToken) {
      clearAuthAndRedirect();
      return Promise.reject(error);
    }

    if (isRefreshing) {
      return new Promise((resolve, reject) => {
        pendingQueue.push({
          resolve: (token: string) => {
            originalRequest.headers.Authorization = `Bearer ${token}`;
            resolve(api(originalRequest));
          },
          reject,
        });
      });
    }

    originalRequest._retry = true;
    isRefreshing = true;

    try {
      const { data } = await axios.post(`${API_BASE_URL}/auth/refresh`, {
        refresh_token: refreshToken,
      });
      const newToken = data.access_token as string;
      localStorage.setItem('access_token', newToken);
      if (data.refresh_token) {
        localStorage.setItem('refresh_token', data.refresh_token);
      }
      processQueue(null, newToken);
      originalRequest.headers.Authorization = `Bearer ${newToken}`;
      return api(originalRequest);
    } catch (refreshError) {
      processQueue(refreshError, null);
      clearAuthAndRedirect();
      return Promise.reject(refreshError);
    } finally {
      isRefreshing = false;
    }
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
    api.get('/knowledge-bases', { params: toSkipLimit(page, pageSize) }),
  get: (id: string) => api.get(`/knowledge-bases/${id}`),
  create: (data: { name: string; description?: string; visibility?: string }) =>
    api.post('/knowledge-bases', data),
  update: (id: string, data: { name?: string; description?: string }) =>
    api.put(`/knowledge-bases/${id}`, data),
  delete: (id: string) => api.delete(`/knowledge-bases/${id}`),
  stats: (id: string) => api.get(`/knowledge-bases/${id}/stats`),
};

// Document APIs
export const docApi = {
  list: (kbId: string, page = 1, pageSize = 20) =>
    api.get(`/knowledge-bases/${kbId}/documents`, { params: { page, page_size: pageSize } }),
  get: (_kbId: string, docId: string) =>
    api.get(`/documents/${docId}`),
  upload: (kbId: string, file: File, description?: string) => {
    const formData = new FormData();
    formData.append('files', file);
    if (description) formData.append('description', description);
    return api.post(`/knowledge-bases/${kbId}/documents/upload`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },
  delete: (_kbId: string, docId: string) =>
    api.delete(`/documents/${docId}`),
  reprocess: (_kbId: string, docId: string) =>
    api.post('/documents/reprocess', { document_ids: [docId] }),
};

// Search APIs
export const searchApi = {
  search: (kbId: string, query: string, topK = 10, searchType = 'hybrid', scoreThreshold = 0) =>
    api.post('/search', {
      query,
      knowledge_base_id: kbId,
      mode: searchType,
      top_k: topK,
      score_threshold: scoreThreshold,
      use_cache: true,
    }),
};

// Model Config APIs
export const modelApi = {
  list: (page = 1, pageSize = 20) =>
    api.get('/model-configs', { params: toSkipLimit(page, pageSize) }),
  get: (id: string) => api.get(`/model-configs/${id}`),
  create: (data: any) => api.post('/model-configs', data),
  update: (id: string, data: any) => api.put(`/model-configs/${id}`, data),
  delete: (id: string) => api.delete(`/model-configs/${id}`),
  test: (id: string) => api.post(`/model-configs/${id}/test`),
};

// Version APIs
export const versionApi = {
  list: (kbId: string, page = 1, pageSize = 20) =>
    api.get(`/knowledge-bases/${kbId}/versions`, { params: { page, page_size: pageSize } }),
  get: (versionId: string) => api.get(`/versions/${versionId}`),
  create: (kbId: string, data: { description: string; tags?: string }) =>
    api.post(`/knowledge-bases/${kbId}/versions`, data),
  switch: (versionId: string) => api.post(`/versions/${versionId}/switch`),
  delete: (versionId: string) => api.delete(`/versions/${versionId}`),
  compare: (v1: string, v2: string) =>
    api.get('/versions/compare', { params: { v1, v2 } }),
};

// Admin APIs
export const adminApi = {
  users: (page = 1, pageSize = 20) =>
    api.get('/admin/users', { params: toSkipLimit(page, pageSize) }),
  stats: () => api.get('/admin/statistics'),
};
