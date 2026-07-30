import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Card,
  Table,
  Button,
  Space,
  Upload,
  message,
  Modal,
  Typography,
  Tag,
  Tooltip,
  Empty,
  Select,
  Form,
  Input,
} from 'antd';
import {
  UploadOutlined,
  DeleteOutlined,
  ReloadOutlined,
  FileOutlined,
  ArrowLeftOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  SyncOutlined,
  ClockCircleOutlined,
  HistoryOutlined,
  SearchOutlined,
  PlusOutlined,
} from '@ant-design/icons';
import { useParams, useNavigate } from 'react-router-dom';
import { kbApi, docApi, versionApi } from '../../services/api';
import type { UploadProps } from 'antd';
import './Documents.css';

const { Text, Title } = Typography;

interface Document {
  id: string;
  file_name: string;
  file_type: string;
  file_size: number;
  status: string;
  chunk_count: number;
  created_at: string;
  processed_at?: string;
  error_message?: string;
}

interface KnowledgeBase {
  id: string;
  name: string;
  description?: string;
  document_count: number;
  chunk_count: number;
  version?: number;
}

interface VersionItem {
  id: string;
  version: number;
  description?: string;
  document_count: number;
  chunk_count: number;
  is_active: boolean;
  tags?: string;
  created_at: string;
}

const DocumentsPage: React.FC = () => {
  const { kbId } = useParams<{ kbId: string }>();
  const navigate = useNavigate();
  const [kb, setKB] = useState<KnowledgeBase | null>(null);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [versions, setVersions] = useState<VersionItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [switching, setSwitching] = useState(false);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [snapshotOpen, setSnapshotOpen] = useState(false);
  const [snapshotLoading, setSnapshotLoading] = useState(false);
  const [form] = Form.useForm();

  const activeVersion = useMemo(
    () => versions.find((v) => v.is_active) || null,
    [versions]
  );

  const fetchKB = useCallback(async () => {
    if (!kbId) return;
    try {
      const response = await kbApi.get(kbId);
      setKB(response.data);
    } catch {
      message.error('获取知识库信息失败');
    }
  }, [kbId]);

  const fetchDocuments = useCallback(async () => {
    if (!kbId) return;
    setLoading(true);
    try {
      const response = await docApi.list(kbId, page, 20);
      setDocuments(response.data.items || response.data);
      setTotal(response.data.total || response.data.length);
    } catch {
      message.error('获取文档列表失败');
    } finally {
      setLoading(false);
    }
  }, [kbId, page]);

  const fetchVersions = useCallback(async () => {
    if (!kbId) return;
    try {
      const response = await versionApi.list(kbId, 1, 50);
      setVersions(response.data.items || []);
    } catch {
      // 无版本时不打扰用户
      setVersions([]);
    }
  }, [kbId]);

  const refreshAll = useCallback(async () => {
    await Promise.all([fetchKB(), fetchDocuments(), fetchVersions()]);
  }, [fetchKB, fetchDocuments, fetchVersions]);

  useEffect(() => {
    fetchKB();
    fetchVersions();
  }, [fetchKB, fetchVersions]);

  useEffect(() => {
    fetchDocuments();
  }, [fetchDocuments]);

  useEffect(() => {
    const processingDocs = documents.filter(
      (d) => d.status === 'processing' || d.status === 'pending'
    );
    if (processingDocs.length > 0) {
      const timer = setInterval(fetchDocuments, 5000);
      return () => clearInterval(timer);
    }
  }, [documents, fetchDocuments]);

  const handleUpload: UploadProps['customRequest'] = async (options) => {
    const { file, onSuccess, onError } = options;
    if (!kbId) return;

    setUploading(true);
    try {
      await docApi.upload(kbId, file as File);
      message.success('上传成功，正在处理中...');
      onSuccess?.({});
      fetchDocuments();
      fetchKB();
    } catch (error: any) {
      message.error(error.response?.data?.detail || '上传失败');
      onError?.(error);
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (docId: string) => {
    if (!kbId) return;
    Modal.confirm({
      title: '确认删除',
      content: '删除文档将同时删除所有分块和向量数据',
      okText: '确认',
      cancelText: '取消',
      onOk: async () => {
        try {
          await docApi.delete(kbId, docId);
          message.success('删除成功');
          fetchDocuments();
          fetchKB();
        } catch {
          message.error('删除失败');
        }
      },
    });
  };

  const handleReprocess = async (docId: string) => {
    if (!kbId) return;
    try {
      await docApi.reprocess(kbId, docId);
      message.success('重新处理已触发');
      fetchDocuments();
    } catch {
      message.error('重新处理失败');
    }
  };

  const handleSwitchVersion = async (versionId: string) => {
    if (!versionId || versionId === activeVersion?.id) return;
    const target = versions.find((v) => v.id === versionId);
    Modal.confirm({
      title: `切换到 v${target?.version ?? ''}？`,
      content: '将按该版本快照调整文档可见性，不会删除数据。',
      okText: '确认切换',
      cancelText: '取消',
      onOk: async () => {
        setSwitching(true);
        try {
          await versionApi.switch(versionId);
          message.success(`已切换到 v${target?.version}`);
          setPage(1);
          await refreshAll();
        } catch (error: any) {
          message.error(error.response?.data?.detail || '版本切换失败');
        } finally {
          setSwitching(false);
        }
      },
    });
  };

  const handleCreateSnapshot = async () => {
    if (!kbId) return;
    try {
      const values = await form.validateFields();
      setSnapshotLoading(true);
      await versionApi.create(kbId, values);
      message.success('版本快照已创建');
      setSnapshotOpen(false);
      form.resetFields();
      await refreshAll();
    } catch (error: any) {
      if (error?.errorFields) return;
      message.error(error.response?.data?.detail || '创建快照失败');
    } finally {
      setSnapshotLoading(false);
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const getStatusTag = (status: string) => {
    const config: Record<string, { color: string; icon: React.ReactNode; text: string }> = {
      pending: { color: 'default', icon: <ClockCircleOutlined />, text: '等待处理' },
      processing: { color: 'processing', icon: <SyncOutlined spin />, text: '处理中' },
      completed: { color: 'success', icon: <CheckCircleOutlined />, text: '已完成' },
      failed: { color: 'error', icon: <CloseCircleOutlined />, text: '失败' },
    };
    const { color, icon, text } = config[status] || config.pending;
    return (
      <Tag color={color} icon={icon}>
        {text}
      </Tag>
    );
  };

  const columns = [
    {
      title: '文件名',
      dataIndex: 'file_name',
      key: 'file_name',
      render: (text: string) => (
        <Space>
          <FileOutlined />
          <Text>{text}</Text>
        </Space>
      ),
    },
    {
      title: '类型',
      dataIndex: 'file_type',
      key: 'file_type',
      render: (text: string) => <Tag>{text?.toUpperCase()}</Tag>,
    },
    {
      title: '大小',
      dataIndex: 'file_size',
      key: 'file_size',
      render: (size: number) => formatFileSize(size),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string, record: Document) => (
        <Tooltip title={record.error_message}>{getStatusTag(status)}</Tooltip>
      ),
    },
    {
      title: '分块数',
      dataIndex: 'chunk_count',
      key: 'chunk_count',
      align: 'center' as const,
    },
    {
      title: '上传时间',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (text: string) => new Date(text).toLocaleString(),
    },
    {
      title: '操作',
      key: 'action',
      render: (_: unknown, record: Document) => (
        <Space>
          {record.status === 'failed' && (
            <Button
              type="link"
              icon={<ReloadOutlined />}
              onClick={() => handleReprocess(record.id)}
            >
              重试
            </Button>
          )}
          <Button
            type="link"
            danger
            icon={<DeleteOutlined />}
            onClick={() => handleDelete(record.id)}
          >
            删除
          </Button>
        </Space>
      ),
    },
  ];

  return (
    <div className="docs-page">
      <div className="docs-header">
        <div className="docs-header-top">
          <Button
            type="text"
            icon={<ArrowLeftOutlined />}
            onClick={() => navigate('/knowledge-bases')}
          >
            知识库
          </Button>
          <Space wrap>
            <Button
              icon={<SearchOutlined />}
              onClick={() => navigate(`/knowledge-bases/${kbId}/search`)}
            >
              搜索
            </Button>
            <Button
              icon={<HistoryOutlined />}
              onClick={() => navigate(`/knowledge-bases/${kbId}/versions`)}
            >
              版本管理
            </Button>
          </Space>
        </div>

        <div className="docs-header-main">
          <div className="docs-title-block">
            <Title level={3} className="docs-title">
              {kb?.name || '知识库'}
            </Title>
            <Text type="secondary" className="docs-desc">
              {kb?.description || '管理文档、检索与版本'}
            </Text>
            <div className="docs-meta">
              <span>{kb?.document_count ?? 0} 文档</span>
              <span className="docs-meta-dot" />
              <span>{kb?.chunk_count ?? 0} 分块</span>
              <span className="docs-meta-dot" />
              <span>{total} 当前可见</span>
            </div>
          </div>

          <div className="docs-version-bar">
            <div className="docs-version-label">
              <HistoryOutlined />
              <span>当前版本</span>
              {activeVersion ? (
                <Tag color="blue" className="docs-version-tag">
                  v{activeVersion.version}
                </Tag>
              ) : (
                <Tag className="docs-version-tag">尚未创建</Tag>
              )}
            </div>

            <Select
              className="docs-version-select"
              placeholder={versions.length ? '切换版本' : '暂无版本'}
              value={activeVersion?.id}
              loading={switching}
              disabled={!versions.length || switching}
              options={versions.map((v) => ({
                value: v.id,
                label: `v${v.version}${v.description ? ` · ${v.description}` : ''}${
                  v.is_active ? '（当前）' : ''
                }`,
              }))}
              onChange={handleSwitchVersion}
            />

            <Button
              icon={<PlusOutlined />}
              onClick={() => {
                form.resetFields();
                setSnapshotOpen(true);
              }}
            >
              创建快照
            </Button>
          </div>
        </div>
      </div>

      <Card
        className="docs-card"
        title="文档"
        extra={
          <Space>
            <Upload
              customRequest={handleUpload}
              showUploadList={false}
              accept=".pdf,.doc,.docx,.txt,.md,.html,.xlsx,.xls,.csv"
              multiple
            >
              <Button type="primary" icon={<UploadOutlined />} loading={uploading}>
                上传文档
              </Button>
            </Upload>
            <Button icon={<ReloadOutlined />} onClick={refreshAll}>
              刷新
            </Button>
          </Space>
        }
      >
        <Table
          columns={columns}
          dataSource={documents}
          rowKey="id"
          loading={loading || switching}
          pagination={{
            current: page,
            total,
            pageSize: 20,
            onChange: setPage,
            showTotal: (t) => `共 ${t} 个文档`,
          }}
          locale={{
            emptyText: (
              <Empty
                description={
                  activeVersion
                    ? `当前版本 v${activeVersion.version} 下暂无可见文档`
                    : '暂无文档'
                }
              >
                <Upload customRequest={handleUpload} showUploadList={false}>
                  <Button type="primary" icon={<UploadOutlined />}>
                    上传文档
                  </Button>
                </Upload>
              </Empty>
            ),
          }}
        />
      </Card>

      <Modal
        title="创建版本快照"
        open={snapshotOpen}
        onOk={handleCreateSnapshot}
        onCancel={() => setSnapshotOpen(false)}
        confirmLoading={snapshotLoading}
        okText="创建"
        cancelText="取消"
      >
        <Form form={form} layout="vertical">
          <Form.Item
            name="description"
            label="版本描述"
            rules={[{ required: true, message: '请输入版本描述' }]}
          >
            <Input.TextArea
              rows={3}
              placeholder="例如：初始版本、新增产品手册..."
            />
          </Form.Item>
          <Form.Item name="tags" label="标签（可选）">
            <Input placeholder="例如：v1.0, stable" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default DocumentsPage;
