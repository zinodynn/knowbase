import React, { useEffect, useState } from 'react';
import { 
  Card, Table, Button, Space, Modal, Form, Input, Select, 
  message, Typography, Tag, Switch, InputNumber
} from 'antd';
import { 
  PlusOutlined, EditOutlined, DeleteOutlined, 
  CheckCircleOutlined, CloseCircleOutlined, ApiOutlined
} from '@ant-design/icons';
import { modelApi } from '../../services/api';

const { Text } = Typography;

interface ModelConfig {
  id: string;
  name: string;
  description?: string;
  config_type: string;
  model_type: string;
  provider: string;
  model_name: string;
  api_base?: string;
  is_active: boolean;
  is_default: boolean;
  created_at: string;
}

const ModelConfigsPage: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<ModelConfig[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [modalVisible, setModalVisible] = useState(false);
  const [editingConfig, setEditingConfig] = useState<ModelConfig | null>(null);
  const [testing, setTesting] = useState<string | null>(null);
  const [form] = Form.useForm();

  const fetchData = async () => {
    setLoading(true);
    try {
      const response = await modelApi.list(page, 20);
      setData(response.data.items || response.data);
      setTotal(response.data.total || response.data.length);
    } catch {
      message.error('获取模型配置失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [page]);

  const handleCreate = () => {
    setEditingConfig(null);
    form.resetFields();
    form.setFieldsValue({
      config_type: 'system_default',
      model_type: 'embedding',
      provider: 'openai',
      is_active: true,
      is_default: false,
      timeout_seconds: 30,
      max_retries: 3,
    });
    setModalVisible(true);
  };

  const handleEdit = (record: ModelConfig) => {
    setEditingConfig(record);
    form.setFieldsValue(record);
    setModalVisible(true);
  };

  const handleDelete = async (id: string) => {
    Modal.confirm({
      title: '确认删除',
      content: '确定要删除此模型配置吗？',
      onOk: async () => {
        try {
          await modelApi.delete(id);
          message.success('删除成功');
          fetchData();
        } catch {
          message.error('删除失败');
        }
      },
    });
  };

  const handleTest = async (id: string) => {
    setTesting(id);
    try {
      const response = await modelApi.test(id);
      if (response.data.success) {
        message.success('连接测试成功');
      } else {
        message.error(`测试失败: ${response.data.error}`);
      }
    } catch (error: any) {
      message.error(error.response?.data?.detail || '测试失败');
    } finally {
      setTesting(null);
    }
  };

  const handleSubmit = async (values: any) => {
    try {
      if (editingConfig) {
        await modelApi.update(editingConfig.id, values);
        message.success('更新成功');
      } else {
        await modelApi.create(values);
        message.success('创建成功');
      }
      setModalVisible(false);
      fetchData();
    } catch (error: any) {
      message.error(error.response?.data?.detail || '操作失败');
    }
  };

  const columns = [
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
      render: (text: string, record: ModelConfig) => (
        <Space>
          <ApiOutlined />
          <Text strong>{text}</Text>
          {record.is_default && <Tag color="gold">默认</Tag>}
        </Space>
      ),
    },
    {
      title: '类型',
      dataIndex: 'model_type',
      key: 'model_type',
      render: (type: string) => {
        const colors: Record<string, string> = {
          embedding: 'blue',
          rerank: 'green',
          LLM: 'purple',
        };
        return <Tag color={colors[type]}>{type.toUpperCase()}</Tag>;
      },
    },
    {
      title: '提供商',
      dataIndex: 'provider',
      key: 'provider',
      render: (provider: string) => <Tag>{provider}</Tag>,
    },
    {
      title: '模型名称',
      dataIndex: 'model_name',
      key: 'model_name',
    },
    {
      title: '配置级别',
      dataIndex: 'config_type',
      key: 'config_type',
      render: (type: string) => {
        const labels: Record<string, string> = {
          system_default: '系统默认',
          kb_specific: '知识库级',
          user_specific: '用户级',
        };
        return labels[type] || type;
      },
    },
    {
      title: '状态',
      dataIndex: 'is_active',
      key: 'is_active',
      render: (active: boolean) => (
        active 
          ? <Tag color="success" icon={<CheckCircleOutlined />}>启用</Tag>
          : <Tag color="default" icon={<CloseCircleOutlined />}>禁用</Tag>
      ),
    },
    {
      title: '操作',
      key: 'action',
      render: (_: any, record: ModelConfig) => (
        <Space>
          <Button 
            type="link" 
            loading={testing === record.id}
            onClick={() => handleTest(record.id)}
          >
            测试
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
      <Card 
        title="模型配置管理"
        extra={
          <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
            添加配置
          </Button>
        }
      >
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
          }}
        />
      </Card>

      <Modal
        title={editingConfig ? '编辑模型配置' : '添加模型配置'}
        open={modalVisible}
        onCancel={() => setModalVisible(false)}
        footer={null}
        width={600}
      >
        <Form form={form} onFinish={handleSubmit} layout="vertical">
          <Form.Item name="name" label="配置名称" rules={[{ required: true }]}>
            <Input placeholder="如: OpenAI Embedding" />
          </Form.Item>
          
          <Form.Item name="description" label="描述">
            <Input.TextArea rows={2} />
          </Form.Item>

          <Space style={{ width: '100%' }} size="large">
            <Form.Item name="config_type" label="配置级别" rules={[{ required: true }]}>
              <Select style={{ width: 150 }}>
                <Select.Option value="system_default">系统默认</Select.Option>
                <Select.Option value="kb_specific">知识库级</Select.Option>
                <Select.Option value="user_specific">用户级</Select.Option>
              </Select>
            </Form.Item>

            <Form.Item name="model_type" label="模型类型" rules={[{ required: true }]}>
              <Select style={{ width: 150 }}>
                <Select.Option value="embedding">Embedding</Select.Option>
                <Select.Option value="rerank">Rerank</Select.Option>
                <Select.Option value="LLM">LLM</Select.Option>
              </Select>
            </Form.Item>
          </Space>

          <Form.Item name="provider" label="提供商" rules={[{ required: true }]}>
            <Select>
              <Select.Option value="openai">OpenAI</Select.Option>
              <Select.Option value="azure">Azure OpenAI</Select.Option>
              <Select.Option value="cohere">Cohere</Select.Option>
              <Select.Option value="jina">Jina AI</Select.Option>
              <Select.Option value="custom">自定义</Select.Option>
            </Select>
          </Form.Item>

          <Form.Item name="model_name" label="模型名称" rules={[{ required: true }]}>
            <Input placeholder="如: text-embedding-3-small" />
          </Form.Item>

          <Form.Item name="api_base" label="API 地址">
            <Input placeholder="如: https://api.openai.com/v1" />
          </Form.Item>

          <Form.Item name="api_key_encrypted" label="API Key">
            <Input.Password placeholder="输入 API Key" />
          </Form.Item>

          <Space style={{ width: '100%' }} size="large">
            <Form.Item name="timeout_seconds" label="超时(秒)">
              <InputNumber min={5} max={300} />
            </Form.Item>
            <Form.Item name="max_retries" label="重试次数">
              <InputNumber min={0} max={10} />
            </Form.Item>
            <Form.Item name="is_active" label="启用" valuePropName="checked">
              <Switch />
            </Form.Item>
            <Form.Item name="is_default" label="设为默认" valuePropName="checked">
              <Switch />
            </Form.Item>
          </Space>

          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit">
                {editingConfig ? '保存' : '创建'}
              </Button>
              <Button onClick={() => setModalVisible(false)}>取消</Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default ModelConfigsPage;
