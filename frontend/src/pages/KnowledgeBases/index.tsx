import React, { useEffect, useState } from 'react';
import { 
  Card, Row, Col, Button, Table, Space, Modal, Form, Input, 
  Select, message, Statistic, Empty, Tag 
} from 'antd';
import { 
  PlusOutlined, SearchOutlined, DeleteOutlined, 
  EditOutlined, EyeOutlined, FolderOutlined 
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { kbApi } from '../../services/api';
import { useKBStore } from '../../stores';

interface KnowledgeBase {
  id: string;
  name: string;
  description?: string;
  visibility: string;
  document_count: number;
  chunk_count: number;
  created_at: string;
}

const KnowledgeBasesPage: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<KnowledgeBase[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [modalVisible, setModalVisible] = useState(false);
  const [editingKB, setEditingKB] = useState<KnowledgeBase | null>(null);
  const [form] = Form.useForm();
  const navigate = useNavigate();
  const { setCurrentKB } = useKBStore();

  const fetchData = async () => {
    setLoading(true);
    try {
      const response = await kbApi.list(page, 20);
      setData(response.data.items || response.data);
      setTotal(response.data.total || response.data.length);
    } catch (error: any) {
      message.error('获取知识库列表失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [page]);

  const handleCreate = () => {
    setEditingKB(null);
    form.resetFields();
    setModalVisible(true);
  };

  const handleEdit = (record: KnowledgeBase) => {
    setEditingKB(record);
    form.setFieldsValue(record);
    setModalVisible(true);
  };

  const handleDelete = async (id: string) => {
    Modal.confirm({
      title: '确认删除',
      content: '删除知识库将同时删除所有文档和向量数据，此操作不可恢复！',
      okText: '确认删除',
      okType: 'danger',
      cancelText: '取消',
      onOk: async () => {
        try {
          await kbApi.delete(id);
          message.success('删除成功');
          fetchData();
        } catch {
          message.error('删除失败');
        }
      },
    });
  };

  const handleSubmit = async (values: any) => {
    try {
      if (editingKB) {
        await kbApi.update(editingKB.id, values);
        message.success('更新成功');
      } else {
        await kbApi.create(values);
        message.success('创建成功');
      }
      setModalVisible(false);
      fetchData();
    } catch (error: any) {
      message.error(error.response?.data?.detail || '操作失败');
    }
  };

  const handleView = (record: KnowledgeBase) => {
    setCurrentKB(record);
    navigate(`/knowledge-bases/${record.id}`);
  };

  const columns = [
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
      render: (text: string, record: KnowledgeBase) => (
        <a onClick={() => handleView(record)}>
          <FolderOutlined style={{ marginRight: 8 }} />
          {text}
        </a>
      ),
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
      render: (text: string) => text || '-',
    },
    {
      title: '可见性',
      dataIndex: 'visibility',
      key: 'visibility',
      render: (visibility: string) => {
        const colors: Record<string, string> = {
          private: 'default',
          team: 'blue',
          public: 'green',
        };
        const labels: Record<string, string> = {
          private: '私有',
          team: '团队',
          public: '公开',
        };
        return <Tag color={colors[visibility]}>{labels[visibility] || visibility}</Tag>;
      },
    },
    {
      title: '文档数',
      dataIndex: 'document_count',
      key: 'document_count',
      align: 'center' as const,
    },
    {
      title: '分块数',
      dataIndex: 'chunk_count',
      key: 'chunk_count',
      align: 'center' as const,
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (text: string) => new Date(text).toLocaleDateString(),
    },
    {
      title: '操作',
      key: 'action',
      render: (_: any, record: KnowledgeBase) => (
        <Space>
          <Button type="link" icon={<EyeOutlined />} onClick={() => handleView(record)}>
            查看
          </Button>
          <Button type="link" icon={<SearchOutlined />} onClick={() => navigate(`/knowledge-bases/${record.id}/search`)}>
            搜索
          </Button>
          <Button type="link" icon={<EditOutlined />} onClick={() => handleEdit(record)}>
            编辑
          </Button>
          <Button type="link" danger icon={<DeleteOutlined />} onClick={() => handleDelete(record.id)}>
            删除
          </Button>
        </Space>
      ),
    },
  ];

  return (
    <div style={{ padding: 24 }}>
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <Card>
            <Statistic title="知识库总数" value={total} prefix={<FolderOutlined />} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic 
              title="文档总数" 
              value={data.reduce((sum, kb) => sum + kb.document_count, 0)} 
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic 
              title="分块总数" 
              value={data.reduce((sum, kb) => sum + kb.chunk_count, 0)} 
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <Button type="primary" icon={<PlusOutlined />} size="large" onClick={handleCreate}>
              创建知识库
            </Button>
          </Card>
        </Col>
      </Row>

      <Card title="知识库列表">
        <Table
          columns={columns}
          dataSource={data}
          rowKey="id"
          loading={loading}
          pagination={{
            current: page,
            total,
            pageSize: 20,
            onChange: setPage,
            showTotal: (t) => `共 ${t} 个知识库`,
          }}
          locale={{ emptyText: <Empty description="暂无知识库，点击上方按钮创建" /> }}
        />
      </Card>

      <Modal
        title={editingKB ? '编辑知识库' : '创建知识库'}
        open={modalVisible}
        onCancel={() => setModalVisible(false)}
        footer={null}
      >
        <Form form={form} onFinish={handleSubmit} layout="vertical">
          <Form.Item 
            name="name" 
            label="名称" 
            rules={[{ required: true, message: '请输入知识库名称' }]}
          >
            <Input placeholder="请输入知识库名称" />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <Input.TextArea rows={3} placeholder="请输入知识库描述" />
          </Form.Item>
          <Form.Item name="visibility" label="可见性" initialValue="private">
            <Select>
              <Select.Option value="private">私有</Select.Option>
              <Select.Option value="team">团队</Select.Option>
              <Select.Option value="public">公开</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit">
                {editingKB ? '保存' : '创建'}
              </Button>
              <Button onClick={() => setModalVisible(false)}>取消</Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default KnowledgeBasesPage;
