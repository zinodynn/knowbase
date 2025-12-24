import { create } from 'zustand';
import { authApi } from '../services/api';

interface User {
  id: string;
  username: string;
  email: string;
  full_name?: string;
  is_superuser: boolean;
}

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
  checkAuth: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  isAuthenticated: false,
  isLoading: true,

  login: async (username: string, password: string) => {
    const response = await authApi.login(username, password);
    
    // 正确获取 token（axios response.data 就是响应体）
    const tokenData = response.data;
    console.log('Login response:', tokenData); // 调试日志
    
    if (tokenData.access_token) {
      localStorage.setItem('access_token', tokenData.access_token);
      if (tokenData.refresh_token) {
        localStorage.setItem('refresh_token', tokenData.refresh_token);
      }
      
      // 获取用户信息
      const userResponse = await authApi.me();
      set({ user: userResponse.data, isAuthenticated: true, isLoading: false });
    } else {
      throw new Error('登录响应中没有 access_token');
    }
  },

  logout: () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    set({ user: null, isAuthenticated: false });
  },

  checkAuth: async () => {
    const token = localStorage.getItem('access_token');
    if (!token) {
      set({ isLoading: false, isAuthenticated: false });
      return;
    }
    try {
      const response = await authApi.me();
      set({ user: response.data, isAuthenticated: true, isLoading: false });
    } catch {
      localStorage.removeItem('access_token');
      set({ user: null, isAuthenticated: false, isLoading: false });
    }
  },
}));

// Knowledge Base Store
interface KnowledgeBase {
  id: string;
  name: string;
  description?: string;
  visibility: string;
  document_count: number;
  chunk_count: number;
  created_at: string;
}

interface KBState {
  knowledgeBases: KnowledgeBase[];
  currentKB: KnowledgeBase | null;
  isLoading: boolean;
  setKnowledgeBases: (kbs: KnowledgeBase[]) => void;
  setCurrentKB: (kb: KnowledgeBase | null) => void;
  setLoading: (loading: boolean) => void;
}

export const useKBStore = create<KBState>((set) => ({
  knowledgeBases: [],
  currentKB: null,
  isLoading: false,
  setKnowledgeBases: (kbs) => set({ knowledgeBases: kbs }),
  setCurrentKB: (kb) => set({ currentKB: kb }),
  setLoading: (loading) => set({ isLoading: loading }),
}));
