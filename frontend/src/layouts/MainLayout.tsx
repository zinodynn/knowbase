import React, { useEffect } from 'react';
import { Avatar, Dropdown, Space, Typography, Spin } from 'antd';
import {
  FolderOutlined,
  SettingOutlined,
  UserOutlined,
  LogoutOutlined,
  ApiOutlined,
} from '@ant-design/icons';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import { useAuthStore } from '../stores';
import './MainLayout.css';

const { Text } = Typography;

const NAV_ITEMS = [
  {
    key: '/knowledge-bases',
    icon: <FolderOutlined />,
    label: '知识库',
  },
  {
    key: '/model-configs',
    icon: <ApiOutlined />,
    label: '模型',
  },
  {
    key: '/settings',
    icon: <SettingOutlined />,
    label: '设置',
  },
];

const MainLayout: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { user, isAuthenticated, isLoading, logout, checkAuth } = useAuthStore();

  useEffect(() => {
    checkAuth();
  }, []);

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      navigate('/login');
    }
  }, [isLoading, isAuthenticated, navigate]);

  if (isLoading) {
    return (
      <div className="kb-shell-loading">
        <Spin size="large" tip="加载中..." />
      </div>
    );
  }

  if (!isAuthenticated) {
    return null;
  }

  const userMenuItems = [
    {
      key: 'profile',
      icon: <UserOutlined />,
      label: '个人信息',
    },
    { type: 'divider' as const },
    {
      key: 'logout',
      icon: <LogoutOutlined />,
      label: '退出登录',
      danger: true,
    },
  ];

  const handleUserMenuClick = ({ key }: { key: string }) => {
    if (key === 'logout') {
      logout();
      navigate('/login');
    } else if (key === 'profile') {
      navigate('/settings');
    }
  };

  const getSelectedKey = () => {
    const path = location.pathname;
    if (path.startsWith('/knowledge-bases')) return '/knowledge-bases';
    if (path.startsWith('/model-configs')) return '/model-configs';
    if (path.startsWith('/settings')) return '/settings';
    return '/knowledge-bases';
  };

  const selectedKey = getSelectedKey();

  return (
    <div className="kb-shell">
      <header className="kb-topbar">
        <div className="kb-topbar-brand" onClick={() => navigate('/knowledge-bases')}>
          <span className="kb-brand-mark">KB</span>
          <span className="kb-brand-name">KnowBase</span>
        </div>

        <nav className="kb-topbar-nav" aria-label="主导航">
          {NAV_ITEMS.map((item) => {
            const active = selectedKey === item.key;
            return (
              <button
                key={item.key}
                type="button"
                className={`kb-nav-item${active ? ' is-active' : ''}`}
                onClick={() => navigate(item.key)}
              >
                <span className="kb-nav-icon">{item.icon}</span>
                <span>{item.label}</span>
              </button>
            );
          })}
        </nav>

        <div className="kb-topbar-actions">
          <Dropdown
            menu={{ items: userMenuItems, onClick: handleUserMenuClick }}
            placement="bottomRight"
          >
            <Space className="kb-user-trigger" size={8}>
              <Avatar size={32} icon={<UserOutlined />} className="kb-user-avatar" />
              <Text className="kb-user-name">{user?.full_name || user?.username}</Text>
            </Space>
          </Dropdown>
        </div>
      </header>

      <main className="kb-main">
        <Outlet />
      </main>
    </div>
  );
};

export default MainLayout;
