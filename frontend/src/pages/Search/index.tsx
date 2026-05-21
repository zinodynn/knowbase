import React, { useState, useEffect } from 'react';
import { 
  Card, Input, Button, Select, Slider, Space, List, Typography, 
  Tag, Spin, Empty, Collapse, message, InputNumber, Row, Col
} from 'antd';
import { SearchOutlined, ArrowLeftOutlined, FileTextOutlined } from '@ant-design/icons';
import { useParams, useNavigate } from 'react-router-dom';
import { searchApi, kbApi } from '../../services/api';

const { Title, Text, Paragraph } = Typography;
const { Panel } = Collapse;

interface SearchResult {
  chunk_id: string;
  document_id: string;
  document_name: string;
  content: string;
  score: number;
  metadata?: Record<string, any>;
}

interface KnowledgeBase {
  id: string;
  name: string;
  description?: string;
}

const SearchPage: React.FC = () => {
  const { kbId } = useParams<{ kbId: string }>();
  const navigate = useNavigate();
  const [kb, setKB] = useState<KnowledgeBase | null>(null);
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);
  
  // Search parameters
  const [topK, setTopK] = useState(10);
  const [searchType, setSearchType] = useState('hybrid');
  const [scoreThreshold, setScoreThreshold] = useState(0.5);

  useEffect(() => {
    if (kbId) {
      kbApi.get(kbId).then(res => setKB(res.data)).catch(() => {});
    }
  }, [kbId]);

  const handleSearch = async () => {
    if (!kbId || !query.trim()) {
      message.warning('请输入搜索内容');
      return;
    }

    setLoading(true);
    setSearched(true);
    try {
      const response = await searchApi.search(kbId, query, topK, searchType);
      const hits = response.data.hits || response.data.results || response.data || [];
      // Filter by score threshold
      const filteredHits = hits.filter((h: SearchResult) => h.score >= scoreThreshold);
      setResults(filteredHits);
    } catch (error: any) {
      message.error(error.response?.data?.detail || '搜索失败');
      setResults([]);
    } finally {
      setLoading(false);
    }
  };

  const highlightText = (text: string, query: string) => {
    if (!query.trim()) return text;
    const parts = text.split(new RegExp(`(${query})`, 'gi'));
    return parts.map((part, i) => 
      part.toLowerCase() === query.toLowerCase() 
        ? <mark key={i} style={{ backgroundColor: '#ffe58f', padding: '0 2px' }}>{part}</mark>
        : part
    );
  };

  const getScoreColor = (score: number) => {
    if (score >= 0.8) return '#52c41a';
    if (score >= 0.6) return '#1890ff';
    if (score >= 0.4) return '#faad14';
    return '#ff4d4f';
  };

  return (
    <div style={{ padding: 24 }}>
      <Card style={{ marginBottom: 16 }}>
        <Space style={{ marginBottom: 16 }}>
          <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/knowledge-bases')}>
            返回
          </Button>
          {kb && <Title level={4} style={{ margin: 0 }}>搜索: {kb.name}</Title>}
        </Space>

        <Row gutter={16}>
          <Col span={16}>
            <Input.Search
              size="large"
              placeholder="输入搜索内容..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onSearch={handleSearch}
              enterButton={<><SearchOutlined /> 搜索</>}
              loading={loading}
            />
          </Col>
          <Col span={8}>
            <Space>
              <Select 
                value={searchType} 
                onChange={setSearchType}
                style={{ width: 120 }}
                options={[
                  { value: 'semantic', label: '语义搜索' },
                  { value: 'keyword', label: '关键词' },
                  { value: 'hybrid', label: '混合搜索' },
                ]}
              />
              <InputNumber 
                min={1} 
                max={100} 
                value={topK} 
                onChange={(v) => setTopK(v || 10)}
                addonBefore="Top"
                style={{ width: 100 }}
              />
            </Space>
          </Col>
        </Row>

        <Collapse ghost style={{ marginTop: 16 }}>
          <Panel header="高级选项" key="1">
            <Space direction="vertical" style={{ width: '100%' }}>
              <div>
                <Text>最低相关度阈值: {scoreThreshold}</Text>
                <Slider
                  min={0}
                  max={1}
                  step={0.05}
                  value={scoreThreshold}
                  onChange={setScoreThreshold}
                  marks={{ 0: '0', 0.5: '0.5', 1: '1' }}
                />
              </div>
            </Space>
          </Panel>
        </Collapse>
      </Card>

      <Card title={`搜索结果 ${results.length > 0 ? `(${results.length})` : ''}`}>
        {loading ? (
          <div style={{ textAlign: 'center', padding: 50 }}>
            <Spin size="large" tip="搜索中..." />
          </div>
        ) : !searched ? (
          <Empty description="输入关键词开始搜索" />
        ) : results.length === 0 ? (
          <Empty description="未找到相关结果，请尝试其他关键词" />
        ) : (
          <List
            itemLayout="vertical"
            dataSource={results}
            renderItem={(item, index) => (
              <List.Item
                key={item.chunk_id}
                style={{ 
                  borderLeft: `4px solid ${getScoreColor(item.score)}`,
                  paddingLeft: 16,
                  marginBottom: 16,
                  background: '#fafafa',
                  borderRadius: 4,
                }}
              >
                <List.Item.Meta
                  title={
                    <Space>
                      <Tag color="blue">#{index + 1}</Tag>
                      <FileTextOutlined />
                      <Text strong>{item.document_name}</Text>
                      <Tag color={getScoreColor(item.score)}>
                        相关度: {(item.score * 100).toFixed(1)}%
                      </Tag>
                    </Space>
                  }
                />
                <Paragraph 
                  style={{ 
                    marginTop: 8, 
                    whiteSpace: 'pre-wrap',
                    lineHeight: 1.8,
                    fontSize: 14,
                  }}
                >
                  {highlightText(item.content, query)}
                </Paragraph>
                {item.metadata && Object.keys(item.metadata).length > 0 && (
                  <div style={{ marginTop: 8 }}>
                    {Object.entries(item.metadata).map(([key, value]) => (
                      <Tag key={key} style={{ marginRight: 4 }}>
                        {key}: {String(value)}
                      </Tag>
                    ))}
                  </div>
                )}
              </List.Item>
            )}
          />
        )}
      </Card>
    </div>
  );
};

export default SearchPage;
