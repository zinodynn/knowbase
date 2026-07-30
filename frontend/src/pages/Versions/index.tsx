import React, { useEffect, useState } from 'react';
import {
  Card,
  Table,
  Button,
  Space,
  Modal,
  Form,
  Input,
  message,
  Tag,
  Popconfirm,
  Tooltip,
} from 'antd';
import {
  PlusOutlined,
  SwapOutlined,
  DeleteOutlined,
  EyeOutlined,
  DiffOutlined,
  HistoryOutlined,
} from '@ant-design/icons';
import { useParams, useNavigate } from 'react-router-dom';
import { versionApi } from '../../services/api';
import VersionDiff from './VersionDiff';

interface VersionItem {
  id: string;
  kb_id: string;
  version: number;
  description?: string;
  document_count: number;
  chunk_count: number;
  is_active: boolean;
  tags?: string;
  created_by?: string;
  created_at: string;
}

interface CompareData {
  version_1: { id: string; version: number; description?: string; document_count: number; chunk_count: number };
  version_2: { id: string; version: number; description?: string; document_count: number; chunk_count: number };
  added_docs: { document_id: string; file_name: string }[];
  removed_docs: { document_id: string; file_name: string }[];
  modified_docs: { document_id: string; file_name: string; old_hash?: string; new_hash?: string }[];
  summary: { added_count: number; removed_count: number; modified_count: number; total_changes: number };
}

const VersionsPage: React.FC = () => {
  const { kbId } = useParams<{ kbId: string }>();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<VersionItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [modalVisible, setModalVisible] = useState(false);
  const [diffVisible, setDiffVisible] = useState(false);
  const [compareData, setCompareData] = useState<CompareData | null>(null);
  const [selectedVersions, setSelectedVersions] = useState<string[]>([]);
  const [detailVisible, setDetailVisible] = useState(false);
  const [detailData, setDetailData] = useState<Record<string, unknown> | null>(null);
  const [form] = Form.useForm();

  const fetchData = async () => {
    if (!kbId) return;
    setLoading(true);
    try {
      const response = await versionApi.list(kbId, page, 20);
      setData(response.data.items || []);
      setTotal(response.data.total || 0);
    } catch {
      message.error('获取版本列表失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page, kbId]);

  const handleCreateSnapshot = () => {
    form.resetFields();
    setModalVisible(true);
  };

  const handleSubmitSnapshot = async () => {
    try {
      const values = await form.validateFields();
      if (!kbId) return;
      await versionApi.create(kbId, values);
      message.success('版本快照创建成功');
      setModalVisible(false);
      fetchData();
    } catch (error: unknown) {
      if (error && typeof error === 'object' && 'errorFields' in error) return; // form validation error
      message.error('创建快照失败');
    }
  };

  const handleSwitchVersion = async (versionId: string) => {
    try {
      await versionApi.switch(versionId);
      message.success('版本切换成功');
      fetchData();
    } catch {
      message.error('版本切换失败');
    }
  };

  const handleDeleteVersion = async (versionId: string) => {
    try {
      await versionApi.delete(versionId);
      message.success('版本已删除');
      fetchData();
    } catch (error: unknown) {
      const detail = error && typeof error === 'object' && 'response' in error
        ? (error as { response?: { data?: { detail?: string } } }).response?.data?.detail
        : undefined;
      message.error(detail || '删除版本失败');
    }
  };

  const handleViewDetail = async (versionId: string) => {
    try {
      const response = await versionApi.get(versionId);
      setDetailData(response.data);
      setDetailVisible(true);
    } catch {
      message.error('获取版本详情失败');
    }
  };

  const handleCompare = async () => {
    if (selectedVersions.length !== 2) {
      message.warning('请选择两个版本进行对比');
      return;
    }
    try {
      const [v1, v2] = selectedVersions;
      const response = await versionApi.compare(v1, v2);
      setCompareData(response.data);
      setDiffVisible(true);
    } catch {
      message.error('版本对比失败');
    }
  };

  const handleRowSelect = (record: VersionItem, selected: boolean) => {
    if (selected) {
      if (selectedVersions.length >= 2) {
        setSelectedVersions([selectedVersions[1], record.id]);
      } else {
        setSelectedVersions([...selectedVersions, record.id]);
      }
    } else {
      setSelectedVersions(selectedVersions.filter(id => id !== record.id));
    }
  };

  const columns = [
    {
      title: '版本号',
      dataIndex: 'version',
      key: 'version',
      width: 100,
      render: (version: number, record: VersionItem) => (
        <Space>
          <Tag color="blue">v{version}</Tag>
          {record.is_active && <Tag color="green">当前</Tag>}
        </Space>
      ),
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
    },
    {
      title: '标签',
      dataIndex: 'tags',
      key: 'tags',
      width: 120,
      render: (tags: string) => tags ? <Tag>{tags}</Tag> : '-',
    },
    {
      title: '文档数',
      dataIndex: 'document_count',
      key: 'document_count',
      width: 80,
    },
    {
      title: '分块数',
      dataIndex: 'chunk_count',
      key: 'chunk_count',
      width: 80,
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: (val: string) => val ? new Date(val).toLocaleString('zh-CN') : '-',
    },
    {
      title: '操作',
      key: 'actions',
      width: 260,
      render: (_: unknown, record: VersionItem) => (
        <Space size="small">
          <Tooltip title="查看详情">
            <Button
              size="small"
              icon={<EyeOutlined />}
              onClick={() => handleViewDetail(record.id)}
            />
          </Tooltip>
          {!record.is_active && (
            <>
              <Popconfirm
                title="确认切换到该版本？"
                description="切换版本会按快照调整文档可见性（不删除数据）"
                onConfirm={() => handleSwitchVersion(record.id)}
                okText="确认切换"
                cancelText="取消"
              >
                <Tooltip title="切换到此版本">
                  <Button size="small" icon={<SwapOutlined />} type="primary" />
                </Tooltip>
              </Popconfirm>
              <Popconfirm
                title="确认删除此版本？"
                onConfirm={() => handleDeleteVersion(record.id)}
                okText="确认删除"
                cancelText="取消"
              >
                <Tooltip title="删除版本">
                  <Button size="small" danger icon={<DeleteOutlined />} />
                </Tooltip>
              </Popconfirm>
            </>
          )}
        </Space>
      ),
    },
  ];

  return (
    <div style={{ padding: 24, maxWidth: 1200, margin: '0 auto' }}>
      <div style={{ marginBottom: 12 }}>
        <Button type="text" onClick={() => navigate(`/knowledge-bases/${kbId}`)}>
          ← 返回文档
        </Button>
      </div>
      <Card
        title={
          <Space>
            <HistoryOutlined />
            版本管理
          </Space>
        }
        extra={
          <Space>
            <Button
              onClick={handleCompare}
              icon={<DiffOutlined />}
              disabled={selectedVersions.length !== 2}
            >
              对比选中版本 ({selectedVersions.length}/2)
            </Button>
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={handleCreateSnapshot}
            >
              创建快照
            </Button>
          </Space>
        }
      >
        <Table
          rowKey="id"
          columns={columns}
          dataSource={data}
          loading={loading}
          rowSelection={{
            type: 'checkbox',
            selectedRowKeys: selectedVersions,
            onSelect: (record, selected) => handleRowSelect(record, selected),
            onSelectAll: (_, __, changeRows) => {
              const newSelected = changeRows.map((r: VersionItem) => r.id);
              setSelectedVersions(newSelected.slice(0, 2));
            },
          }}
          pagination={{
            current: page,
            total,
            pageSize: 20,
            onChange: setPage,
            showTotal: (t) => `共 ${t} 个版本`,
          }}
          locale={{ emptyText: '暂无版本记录，点击"创建快照"开始版本管理' }}
        />
      </Card>

      <Modal
        title="创建版本快照"
        open={modalVisible}
        onOk={handleSubmitSnapshot}
        onCancel={() => setModalVisible(false)}
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
              placeholder="例如：初始版本、添加了产品文档、修复了索引..."
            />
          </Form.Item>
          <Form.Item name="tags" label="版本标签（可选）">
            <Input placeholder="例如：v1.0, stable, release" />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title="版本对比"
        open={diffVisible}
        onCancel={() => setDiffVisible(false)}
        footer={null}
        width={800}
      >
        {compareData && <VersionDiff data={compareData} />}
      </Modal>

      <Modal
        title="版本详情"
        open={detailVisible}
        onCancel={() => setDetailVisible(false)}
        footer={null}
        width={720}
      >
        {detailData && (
          <pre style={{ maxHeight: 480, overflow: 'auto', whiteSpace: 'pre-wrap' }}>
            {JSON.stringify(detailData, null, 2)}
          </pre>
        )}
      </Modal>
    </div>
  );
};

export default VersionsPage;
