import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  Input,
  Tag,
  Space,
  Tooltip,
  Typography,
  Tabs,
  Empty,
  Spin,
  message,
} from 'antd';
import {
  SearchOutlined,
  ThunderboltOutlined,
  HistoryOutlined,
  BulbOutlined,
  LikeOutlined,
  DislikeOutlined,
  RobotOutlined,
} from '@ant-design/icons';
import { suggestionApi } from '@/services/suggestion';
import type { CommandSuggestion } from '@/types';

const { Text } = Typography;

const CATEGORY_COLORS: Record<string, string> = {
  docker: '#2496ed',
  system: '#52c41a',
  network: '#722ed1',
  file: '#fa8c16',
  process: '#eb2f96',
  security: '#f5222d',
  deploy: '#13c2c2',
  other: '#8c8c8c',
};

const SOURCE_LABELS: Record<string, { label: string; icon: React.ReactNode; color: string }> = {
  history: { label: '历史', icon: <HistoryOutlined />, color: '#1677ff' },
  template: { label: '模板', icon: <BulbOutlined />, color: '#52c41a' },
  collaborative: { label: '推荐', icon: <ThunderboltOutlined />, color: '#722ed1' },
  nlp: { label: 'NLP', icon: <RobotOutlined />, color: '#fa8c16' },
  nlp_keyword: { label: 'NLP', icon: <RobotOutlined />, color: '#fa8c16' },
};

interface CommandSuggestionProps {
  value: string;
  onChange: (value: string) => void;
  onExecute?: () => void;
  placeholder?: string;
  style?: React.CSSProperties;
}

const CommandSuggestionComponent: React.FC<CommandSuggestionProps> = ({
  value,
  onChange,
  onExecute,
  placeholder = '输入命令或自然语言查询...',
  style,
}) => {
  const [suggestions, setSuggestions] = useState<CommandSuggestion[]>([]);
  const [loading, setLoading] = useState(false);
  const [visible, setVisible] = useState(false);
  const [activeIndex, setActiveIndex] = useState(-1);
  const [nlpQuery, setNlpQuery] = useState('');
  const [nlpResults, setNlpResults] = useState<CommandSuggestion[]>([]);
  const [nlpLoading, setNlpLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<'autocomplete' | 'nlp'>('autocomplete');
  const [feedbackGiven, setFeedbackGiven] = useState<Record<string, 'like' | 'dislike'>>({});

  const debounceRef = useRef<ReturnType<typeof setTimeout>>();
  const containerRef = useRef<HTMLDivElement>(null);

  const fetchSuggestions = useCallback(async (prefix: string) => {
    if (!prefix || prefix.trim().length === 0) {
      setSuggestions([]);
      return;
    }
    setLoading(true);
    try {
      const resp = await suggestionApi.getSuggestions(prefix, 15);
      setSuggestions(resp.suggestions);
      setVisible(true);
      setActiveIndex(-1);
    } catch {
      setSuggestions([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (debounceRef.current) {
      clearTimeout(debounceRef.current);
    }
    if (activeTab === 'autocomplete') {
      debounceRef.current = setTimeout(() => {
        fetchSuggestions(value);
      }, 150);
    }
    return () => {
      if (debounceRef.current) {
        clearTimeout(debounceRef.current);
      }
    };
  }, [value, activeTab, fetchSuggestions]);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setVisible(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  const handleSelect = (cmd: string) => {
    onChange(cmd);
    setVisible(false);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    const list = activeTab === 'autocomplete' ? suggestions : nlpResults;
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setActiveIndex(prev => Math.min(prev + 1, list.length - 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setActiveIndex(prev => Math.max(prev - 1, -1));
    } else if (e.key === 'Tab') {
      e.preventDefault();
      if (activeIndex >= 0 && list[activeIndex]) {
        handleSelect(list[activeIndex].command);
      }
    } else if (e.key === 'Enter' && e.ctrlKey) {
      onExecute?.();
    } else if (e.key === 'Escape') {
      setVisible(false);
    }
  };

  const handleNlpSearch = useCallback(async () => {
    if (!nlpQuery.trim()) return;
    setNlpLoading(true);
    try {
      const resp = await suggestionApi.nlpQuery(nlpQuery);
      setNlpResults(resp.suggestions);
    } catch {
      message.error('自然语言查询失败');
      setNlpResults([]);
    } finally {
      setNlpLoading(false);
    }
  }, [nlpQuery]);

  const handleFeedback = async (cmd: string, useful: boolean) => {
    try {
      await suggestionApi.submitFeedback({ command: cmd, useful });
      setFeedbackGiven(prev => ({ ...prev, [cmd]: useful ? 'like' : 'dislike' }));
      message.success(useful ? '感谢反馈，我们会优先展示此建议' : '已记录，将减少类似建议');
    } catch {
      message.error('反馈提交失败');
    }
  };

  const renderSuggestionItem = (item: CommandSuggestion, index: number, isActive: boolean) => {
    const sourceInfo = SOURCE_LABELS[item.source] || SOURCE_LABELS.template;
    const categoryColor = CATEGORY_COLORS[item.category] || CATEGORY_COLORS.other;
    const feedback = feedbackGiven[item.command];

    return (
      <div
        key={`${item.command}-${index}`}
        style={{
          padding: '6px 10px',
          cursor: 'pointer',
          background: isActive ? '#e6f4ff' : 'transparent',
          borderRadius: 4,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: 8,
          borderLeft: isActive ? '3px solid #1677ff' : '3px solid transparent',
        }}
        onClick={() => handleSelect(item.command)}
        onMouseEnter={() => setActiveIndex(index)}
      >
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <Text
              style={{
                fontFamily: 'Consolas, Monaco, monospace',
                fontSize: 13,
                whiteSpace: 'nowrap',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
              }}
            >
              {item.command}
            </Text>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 4, marginTop: 2 }}>
            <Tag color={categoryColor} style={{ fontSize: 10, lineHeight: '16px', padding: '0 4px', margin: 0 }}>
              {item.category || 'other'}
            </Tag>
            <span style={{ color: sourceInfo.color, fontSize: 10 }}>
              {sourceInfo.icon} {sourceInfo.label}
            </span>
            {item.is_history && (
              <span style={{ color: '#999', fontSize: 10 }}>
                ×{item.frequency}
              </span>
            )}
            {item.score > 0 && (
              <span style={{ color: '#bbb', fontSize: 10 }}>
                {item.score.toFixed(1)}
              </span>
            )}
          </div>
        </div>
        <Space size={2} onClick={e => e.stopPropagation()}>
          {feedback === 'like' ? (
            <LikeOutlined style={{ color: '#52c41a', fontSize: 12 }} />
          ) : feedback === 'dislike' ? (
            <DislikeOutlined style={{ color: '#ff4d4f', fontSize: 12 }} />
          ) : (
            <>
              <Tooltip title="有用">
                <LikeOutlined
                  style={{ color: '#bbb', fontSize: 12 }}
                  onClick={(e) => { e.stopPropagation(); handleFeedback(item.command, true); }}
                />
              </Tooltip>
              <Tooltip title="无用">
                <DislikeOutlined
                  style={{ color: '#bbb', fontSize: 12 }}
                  onClick={(e) => { e.stopPropagation(); handleFeedback(item.command, false); }}
                />
              </Tooltip>
            </>
          )}
        </Space>
      </div>
    );
  };

  const currentList = activeTab === 'autocomplete' ? suggestions : nlpResults;
  const showDropdown = visible || (activeTab === 'nlp' && nlpResults.length > 0);

  return (
    <div ref={containerRef} style={{ position: 'relative', ...style }}>
      <Input.TextArea
        value={value}
        onChange={e => onChange(e.target.value)}
        onFocus={() => {
          if (value.trim()) setVisible(true);
        }}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        autoSize={{ minRows: 3, maxRows: 8 }}
        style={{
          fontFamily: 'Consolas, Monaco, monospace',
          fontSize: 13,
          paddingRight: 80,
        }}
      />

      <div
        style={{
          position: 'absolute',
          right: 8,
          top: 6,
          display: 'flex',
          gap: 4,
          zIndex: 1,
        }}
      >
        <Tooltip title="自然语言查询">
          <RobotOutlined
            style={{
              color: activeTab === 'nlp' ? '#1677ff' : '#999',
              fontSize: 14,
              cursor: 'pointer',
              padding: 4,
              background: activeTab === 'nlp' ? '#e6f4ff' : 'transparent',
              borderRadius: 4,
            }}
            onClick={() => {
              setActiveTab(prev => prev === 'nlp' ? 'autocomplete' : 'nlp');
              setVisible(true);
            }}
          />
        </Tooltip>
      </div>

      {showDropdown && (
        <div
          style={{
            position: 'absolute',
            top: '100%',
            left: 0,
            right: 0,
            zIndex: 1000,
            background: '#fff',
            border: '1px solid #d9d9d9',
            borderRadius: '0 0 8px 8px',
            boxShadow: '0 6px 16px rgba(0,0,0,0.12)',
            maxHeight: 400,
            overflowY: 'auto',
          }}
        >
          <Tabs
            activeKey={activeTab}
            onChange={key => setActiveTab(key as 'autocomplete' | 'nlp')}
            size="small"
            style={{ padding: '0 8px' }}
            items={[
              {
                key: 'autocomplete',
                label: (
                  <span>
                    <SearchOutlined /> 自动补全
                    {suggestions.length > 0 && (
                      <Tag style={{ marginLeft: 4, fontSize: 10 }}>{suggestions.length}</Tag>
                    )}
                  </span>
                ),
                children: (
                  <div style={{ maxHeight: 300, overflowY: 'auto' }}>
                    {loading ? (
                      <div style={{ textAlign: 'center', padding: 20 }}>
                        <Spin size="small" />
                      </div>
                    ) : suggestions.length === 0 ? (
                      <Empty
                        image={Empty.PRESENTED_IMAGE_SIMPLE}
                        description="输入命令前缀获取建议"
                        style={{ padding: '12px 0' }}
                      />
                    ) : (
                      suggestions.map((item, i) => renderSuggestionItem(item, i, activeIndex === i))
                    )}
                  </div>
                ),
              },
              {
                key: 'nlp',
                label: (
                  <span>
                    <RobotOutlined /> 自然语言
                  </span>
                ),
                children: (
                  <div>
                    <div style={{ padding: '4px 4px 8px' }}>
                      <Input
                        size="small"
                        prefix={<RobotOutlined />}
                        placeholder="如: 帮我找出CPU占用最高的进程"
                        value={nlpQuery}
                        onChange={e => setNlpQuery(e.target.value)}
                        onPressEnter={handleNlpSearch}
                        suffix={
                          <SearchOutlined
                            style={{ color: '#1677ff', cursor: 'pointer' }}
                            onClick={handleNlpSearch}
                          />
                        }
                      />
                    </div>
                    <div style={{ maxHeight: 240, overflowY: 'auto' }}>
                      {nlpLoading ? (
                        <div style={{ textAlign: 'center', padding: 20 }}>
                          <Spin size="small" />
                        </div>
                      ) : nlpResults.length === 0 ? (
                        <Empty
                          image={Empty.PRESENTED_IMAGE_SIMPLE}
                          description="输入自然语言查询，按回车搜索"
                          style={{ padding: '12px 0' }}
                        />
                      ) : (
                        nlpResults.map((item, i) => renderSuggestionItem(item, i, activeIndex === i))
                      )}
                    </div>
                  </div>
                ),
              },
            ]}
          />
        </div>
      )}
    </div>
  );
};

export default CommandSuggestionComponent;
