import React from 'react';
import { Card, Descriptions, List, Space, Tag, Typography, Statistic, Row, Col, Empty } from 'antd';
import {
  PlusCircleOutlined,
  MinusCircleOutlined,
  EditOutlined,
  FileTextOutlined,
} from '@ant-design/icons';

const { Text } = Typography;

interface CompareDoc {
  document_id: string;
  file_name: string;
}

interface CompareModifiedDoc {
  document_id: string;
  file_name: string;
  old_hash?: string;
  new_hash?: string;
}

interface VersionInfo {
  id: string;
  version: number;
  description?: string;
  document_count: number;
  chunk_count: number;
}

interface CompareData {
  version_1: VersionInfo;
  version_2: VersionInfo;
  added_docs: CompareDoc[];
  removed_docs: CompareDoc[];
  modified_docs: CompareModifiedDoc[];
  summary: {
    added_count: number;
    removed_count: number;
    modified_count: number;
    total_changes: number;
  };
}

const VersionDiff: React.FC<{ data: CompareData }> = ({ data }) => {
  const { version_1, version_2, added_docs, removed_docs, modified_docs, summary } = data;

  return (
    <div>
      {/* 版本信息 */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={12}>
          <Card size="small" title={`版本 ${version_1.version}（旧）`}>
            <Descriptions column={1} size="small">
              <Descriptions.Item label="描述">
                {version_1.description || '-'}
              </Descriptions.Item>
              <Descriptions.Item label="文档数">
                {version_1.document_count}
              </Descriptions.Item>
              <Descriptions.Item label="分块数">
                {version_1.chunk_count}
              </Descriptions.Item>
            </Descriptions>
          </Card>
        </Col>
        <Col span={12}>
          <Card size="small" title={`版本 ${version_2.version}（新）`}>
            <Descriptions column={1} size="small">
              <Descriptions.Item label="描述">
                {version_2.description || '-'}
              </Descriptions.Item>
              <Descriptions.Item label="文档数">
                {version_2.document_count}
              </Descriptions.Item>
              <Descriptions.Item label="分块数">
                {version_2.chunk_count}
              </Descriptions.Item>
            </Descriptions>
          </Card>
        </Col>
      </Row>

      {/* 变更摘要 */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <Statistic
            title="新增文档"
            value={summary.added_count}
            valueStyle={{ color: '#52c41a' }}
            prefix={<PlusCircleOutlined />}
          />
        </Col>
        <Col span={6}>
          <Statistic
            title="删除文档"
            value={summary.removed_count}
            valueStyle={{ color: '#ff4d4f' }}
            prefix={<MinusCircleOutlined />}
          />
        </Col>
        <Col span={6}>
          <Statistic
            title="修改文档"
            value={summary.modified_count}
            valueStyle={{ color: '#faad14' }}
            prefix={<EditOutlined />}
          />
        </Col>
        <Col span={6}>
          <Statistic
            title="总变更"
            value={summary.total_changes}
            prefix={<FileTextOutlined />}
          />
        </Col>
      </Row>

      {/* 新增文档 */}
      <Card
        size="small"
        title={
          <span style={{ color: '#52c41a' }}>
            <PlusCircleOutlined /> 新增文档 ({added_docs.length})
          </span>
        }
        style={{ marginBottom: 16 }}
      >
        {added_docs.length === 0 ? (
          <Empty description="无新增文档" image={Empty.PRESENTED_IMAGE_SIMPLE} />
        ) : (
          <List
            size="small"
            dataSource={added_docs}
            renderItem={(item) => (
              <List.Item>
                <Text code>{item.file_name}</Text>
              </List.Item>
            )}
          />
        )}
      </Card>

      {/* 删除文档 */}
      <Card
        size="small"
        title={
          <span style={{ color: '#ff4d4f' }}>
            <MinusCircleOutlined /> 删除文档 ({removed_docs.length})
          </span>
        }
        style={{ marginBottom: 16 }}
      >
        {removed_docs.length === 0 ? (
          <Empty description="无删除文档" image={Empty.PRESENTED_IMAGE_SIMPLE} />
        ) : (
          <List
            size="small"
            dataSource={removed_docs}
            renderItem={(item) => (
              <List.Item>
                <Text delete type="danger">
                  {item.file_name}
                </Text>
              </List.Item>
            )}
          />
        )}
      </Card>

      {/* 修改文档 */}
      <Card
        size="small"
        title={
          <span style={{ color: '#faad14' }}>
            <EditOutlined /> 修改文档 ({modified_docs.length})
          </span>
        }
      >
        {modified_docs.length === 0 ? (
          <Empty description="无修改文档" image={Empty.PRESENTED_IMAGE_SIMPLE} />
        ) : (
          <List
            size="small"
            dataSource={modified_docs}
            renderItem={(item) => (
              <List.Item>
                <List.Item.Meta
                  avatar={<Tag color="orange">修改</Tag>}
                  title={<Text>{item.file_name}</Text>}
                  description={
                    <Space direction="vertical" size={0}>
                      {item.old_hash && (
                        <Text type="secondary" style={{ fontSize: 12 }}>
                          旧哈希: {item.old_hash.substring(0, 16)}...
                        </Text>
                      )}
                      {item.new_hash && (
                        <Text type="secondary" style={{ fontSize: 12 }}>
                          新哈希: {item.new_hash.substring(0, 16)}...
                        </Text>
                      )}
                    </Space>
                  }
                />
              </List.Item>
            )}
          />
        )}
      </Card>
    </div>
  );
};

export default VersionDiff;
