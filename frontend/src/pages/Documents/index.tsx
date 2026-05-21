import React, { useEffect, useState } from 'react';
import { 
  Card, Table, Button, Space, Upload, message, Modal, 
  Typography, Descriptions, Tag, Tooltip, Empty
} from 'antd';
import { 
  UploadOutlined, DeleteOutlined, ReloadOutlined, 
  FileOutlined, ArrowLeftOutlined,
  CheckCircleOutlined, CloseCircleOutlined, SyncOutlined, ClockCircleOutlined
} from '@ant-design/icons';
import { useParams, useNavigate } from 'react-router-dom';
import { kbApi, docApi } from '../../services/api';
import type { UploadProps } from 'antd';

const { Text } = Typography;

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
}

const DocumentsPage: React.FC = () => {
  const { kbId } = useParams<{ kbId: string }>();
  const navigate = useNavigate();
  const [kb, setKB] = useState<KnowledgeBase | null>(null);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);

  const fetchKB = async () => {
    if (!kbId) return;
    try {
      const response = await kbApi.get(kbId);
      setKB(response.data);
    } catch {
      message.error('获取知识库信息失败');
    }
  };

  const fetchDocuments = async () => {
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
  };

  useEffect(() => {
    fetchKB();
    fetchDocuments();
  }, [kbId, page]);

  // 轮询处理中的文档状态
  useEffect(() => {
    const processingDocs = documents.filter(d => d.status === 'processing' || d.status === 'pending');
    if (processingDocs.length > 0) {
      const timer = setInterval(fetchDocuments, 5000);
      return () => clearInterval(timer);
    }
  }, [documents]);

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
    return <Tag color={color} icon={icon}>{text}</Tag>;
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
      render: (text: string) => <Tag>{text.toUpperCase()}</Tag>,
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
        <Tooltip title={record.error_message}>
          {getStatusTag(status)}
        </Tooltip>
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
      render: (_: any, record: Document) => (
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
    <div style={{ padding: 24 }}>
      <Card style={{ marginBottom: 16 }}>
        <Space style={{ marginBottom: 16 }}>
          <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/knowledge-bases')}>
            返回
          </Button>
        </Space>
        
        {kb && (
          <Descriptions title={kb.name} bordered column={4}>
            <Descriptions.Item label="描述" span={2}>{kb.description || '-'}</Descriptions.Item>
            <Descriptions.Item label="文档数">{kb.document_count}</Descriptions.Item>
            <Descriptions.Item label="分块数">{kb.chunk_count}</Descriptions.Item>
          </Descriptions>
        )}
      </Card>

      <Card 
        title="文档管理"
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
            <Button icon={<ReloadOutlined />} onClick={fetchDocuments}>
              刷新
            </Button>
          </Space>
        }
      >
        <Table
          columns={columns}
          dataSource={documents}
          rowKey="id"
          loading={loading}
          pagination={{
            current: page,
            total,
            pageSize: 20,
            onChange: setPage,
            showTotal: (t) => `共 ${t} 个文档`,
          }}
          locale={{ 
            emptyText: (
              <Empty description="暂无文档">
                <Upload customRequest={handleUpload} showUploadList={false}>
                  <Button type="primary" icon={<UploadOutlined />}>上传第一个文档</Button>
                </Upload>
              </Empty>
            ) 
          }}
        />
      </Card>
    </div>
  );
};

export default DocumentsPage;
