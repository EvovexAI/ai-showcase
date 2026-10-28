'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';

interface Decomposition {
  id: string;
  awemeId: string | null;
  title: string;
  videoPath: string;
  reportJson: {
    duration_seconds: number;
    duration_label: string;
    script?: { total_chars: number; segment_count: number };
    voice?: { gender_guess: string; chars_per_minute: number };
    chapters?: { title: string; duration_seconds: number }[];
  };
  sceneCount: number;
  createdAt: string;
  // 新增字段
  contentSummary?: string;
  targetAudience?: string;
  hooks?: string;
  keyPoints?: string;
  emotions?: string;
  userGain?: string;
  engagementStrategy?: string;
  contentType?: string;
}

export default function VideoDecomposePage() {
  const [input, setInput] = useState('');
  const [model, setModel] = useState('base');
  const [isLoading, setIsLoading] = useState(false);
  const [history, setHistory] = useState<Decomposition[]>([]);
  const [error, setError] = useState<string | null>(null);

  // API 基础 URL - 直接调用后端服务
  const API_BASE = 'http://localhost:3001';

  // 加载历史记录
  useEffect(() => {
    console.log('Component mounted, fetching history...');
    fetchHistory();
  }, []);

  async function fetchHistory() {
    try {
      const res = await fetch(`${API_BASE}/api/video-decompose?limit=50`);
      const data = await res.json();
      console.log('API Response:', data);
      if (data.success) {
        setHistory(data.data);
      } else {
        console.error('API returned success: false', data);
      }
    } catch (err) {
      console.error('Failed to fetch history:', err);
    }
  }

  async function handleAnalyze() {
    if (!input.trim()) return;
    
    setIsLoading(true);
    setError(null);
    
    try {
      const res = await fetch(`${API_BASE}/api/video-decompose/analyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          input: input.trim(),
          model,
          full: true,
          keyframeMode: 'transcript',
          persist: true,
        }),
      });
      
      const data = await res.json();
      
      if (data.success) {
        // 刷新历史
        await fetchHistory();
        setInput('');
      } else {
        setError(data.error || '分析失败');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : '分析失败');
    } finally {
      setIsLoading(false);
    }
  }

  async function handleRefresh() {
    await fetchHistory();
  }

  return (
    <div style={{ minHeight: '100vh', background: '#f5f5f5' }}>
      {/* 头部 */}
      <div style={{ background: '#1a1a2e', color: 'white', padding: '20px 40px' }}>
        <h1 style={{ margin: 0, fontSize: '24px' }}>
          🎬 AI Video Decompose
        </h1>
        <p style={{ margin: '8px 0 0', opacity: 0.8, fontSize: '14px' }}>
          抖音视频一键分析 - 关键帧 / 口播脚本 / 章节结构
        </p>
      </div>

      <div style={{ maxWidth: '1200px', margin: '0 auto', padding: '40px 20px' }}>
        {/* 输入区域 */}
        <div style={{ 
          background: 'white', 
          borderRadius: '12px', 
          padding: '24px',
          boxShadow: '0 2px 8px rgba(0,0,0,0.08)',
          marginBottom: '32px'
        }}>
          <h2 style={{ margin: '0 0 16px', fontSize: '18px' }}>视频输入</h2>
          
          <div style={{ display: 'flex', gap: '12px', marginBottom: '16px' }}>
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleAnalyze()}
              placeholder="粘贴分享链接 / awemeId / 本地视频路径"
              disabled={isLoading}
              style={{
                flex: 1,
                padding: '12px 16px',
                fontSize: '16px',
                border: '2px solid #e0e0e0',
                borderRadius: '8px',
                outline: 'none',
              }}
            />
            
            <select
              value={model}
              onChange={(e) => setModel(e.target.value)}
              disabled={isLoading}
              style={{
                padding: '12px 16px',
                fontSize: '16px',
                border: '2px solid #e0e0e0',
                borderRadius: '8px',
                background: 'white',
              }}
            >
              <option value="tiny">tiny (最快)</option>
              <option value="base">base (推荐)</option>
              <option value="small">small</option>
              <option value="medium">medium (最准)</option>
            </select>
            
            <button
              onClick={handleAnalyze}
              disabled={isLoading || !input.trim()}
              style={{
                padding: '12px 32px',
                fontSize: '16px',
                fontWeight: 'bold',
                color: 'white',
                background: isLoading ? '#9e9e9e' : '#4caf50',
                border: 'none',
                borderRadius: '8px',
                cursor: isLoading ? 'not-allowed' : 'pointer',
                transition: 'background 0.2s',
              }}
            >
              {isLoading ? '⏳ 分析中...' : '🚀 一键拆解'}
            </button>
            
            <button
              onClick={handleRefresh}
              style={{
                padding: '12px 16px',
                fontSize: '16px',
                background: 'white',
                border: '2px solid #e0e0e0',
                borderRadius: '8px',
                cursor: 'pointer',
              }}
            >
              🔄 刷新
            </button>
          </div>

          {error && (
            <div style={{ 
              padding: '12px', 
              background: '#ffebee', 
              color: '#c62828',
              borderRadius: '8px',
              fontSize: '14px'
            }}>
              ❌ {error}
            </div>
          )}

          <p style={{ margin: 0, color: '#666', fontSize: '13px' }}>
            💡 支持：抖音分享链接 / 视频ID / 本地 .mp4 文件路径
          </p>
        </div>

        {/* 历史记录 */}
        <div style={{ 
          background: 'white', 
          borderRadius: '12px', 
          padding: '24px',
          boxShadow: '0 2px 8px rgba(0,0,0,0.08)'
        }}>
          <h2 style={{ margin: '0 0 20px', fontSize: '18px' }}>
            📋 最近拆解 ({history.length})
          </h2>

          <div style={{ display: 'grid', gap: '16px' }}>
            {history.length === 0 ? (
              <div style={{
                padding: '40px 20px',
                textAlign: 'center',
                color: '#999'
              }}>
                <p style={{ fontSize: '16px', margin: 0 }}>还没有拆解过视频</p>
                <p style={{ fontSize: '13px', margin: '8px 0 0' }}>在上面输入视频链接开始拆解吧 →</p>
              </div>
            ) : (
              history.map((item) => (
                <Link
                  key={item.id}
                  href={`/video-decompose/${item.id}`}
                  style={{
                    padding: '16px',
                    border: '1px solid #e0e0e0',
                    borderRadius: '8px',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    textDecoration: 'none',
                    color: 'inherit',
                    transition: 'all 0.2s',
                    cursor: 'pointer'
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.borderColor = '#4caf50';
                    e.currentTarget.style.boxShadow = '0 4px 12px rgba(76,175,80,0.15)';
                    e.currentTarget.style.backgroundColor = '#fafafa';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.borderColor = '#e0e0e0';
                    e.currentTarget.style.boxShadow = 'none';
                    e.currentTarget.style.backgroundColor = 'transparent';
                  }}
                >
                  <div>
                    <h3 style={{ margin: '0 0 8px', fontSize: '16px', fontWeight: 'bold', color: '#1a1a2e' }}>
                      {item.title || '未命名视频'}
                    </h3>
                    
                    {/* 作者信息和内容类型 */}
                    <div style={{ display: 'flex', gap: '12px', marginBottom: '8px', fontSize: '13px', color: '#666', flexWrap: 'wrap' }}>
                      {item.contentType && (
                        <span style={{ padding: '2px 8px', background: '#e1f5fe', borderRadius: '4px', color: '#01579b' }}>
                          📂 {item.contentType}
                        </span>
                      )}
                      {item.targetAudience && (
                        <span style={{ padding: '2px 8px', background: '#f3e5f5', borderRadius: '4px', color: '#4a148c' }}>
                          👥 {item.targetAudience}
                        </span>
                      )}
                    </div>
                    
                    {/* 钩子标签 */}
                    {item.hooks && (
                      <div style={{ display: 'flex', gap: '6px', marginBottom: '8px', flexWrap: 'wrap' }}>
                        {item.hooks.split(',').slice(0, 3).map((hook: string, i: number) => (
                          <span key={i} style={{
                            padding: '4px 10px',
                            background: '#fff3e0',
                            borderRadius: '12px',
                            fontSize: '12px',
                            color: '#e65100'
                          }}>
                            🎣 {hook.trim()}
                          </span>
                        ))}
                        {item.hooks.split(',').length > 3 && (
                          <span style={{
                            padding: '4px 10px',
                            background: '#f5f5f5',
                            borderRadius: '12px',
                            fontSize: '12px',
                            color: '#999'
                          }}>
                            +{item.hooks.split(',').length - 3}
                          </span>
                        )}
                      </div>
                    )}
                    
                    {/* 情绪标签 */}
                    {item.emotions && (
                      <div style={{ display: 'flex', gap: '6px', marginBottom: '8px', flexWrap: 'wrap' }}>
                        {item.emotions.split(',').slice(0, 3).map((emotion: string, i: number) => (
                          <span key={i} style={{
                            padding: '4px 10px',
                            background: '#ffe0b2',
                            borderRadius: '12px',
                            fontSize: '12px',
                            color: '#bf360c'
                          }}>
                            😊 {emotion.trim()}
                          </span>
                        ))}
                      </div>
                    )}
                    
                    {/* 基础信息 */}
                    <div style={{ display: 'flex', gap: '16px', fontSize: '13px', color: '#666', flexWrap: 'wrap' }}>
                      <span>⏱️ {item.reportJson?.duration_label || '-'}</span>
                      <span>🎬 {item.sceneCount} 个分镜</span>
                      <span>📝 {item.reportJson?.script?.total_chars || 0} 字</span>
                      <span>🆔 {item.awemeId || '本地视频'}</span>
                    </div>
                  </div>
                  <div style={{ textAlign: 'right', color: '#999', fontSize: '12px', minWidth: '150px' }}>
                    <div style={{ marginBottom: '8px' }}>
                      {new Date(item.createdAt).toLocaleString('zh-CN')}
                    </div>
                    <button
                      onClick={(e) => {
                        e.preventDefault();
                        e.stopPropagation();
                      }}
                      style={{
                        padding: '6px 12px',
                        background: '#4caf50',
                        color: 'white',
                        border: 'none',
                        borderRadius: '4px',
                        fontSize: '12px',
                        fontWeight: 'bold',
                        cursor: 'pointer',
                        transition: 'background 0.2s'
                      }}
                      onMouseEnter={(e) => e.currentTarget.style.background = '#45a049'}
                      onMouseLeave={(e) => e.currentTarget.style.background = '#4caf50'}
                    >
                      查看详情 →
                    </button>
                  </div>
                </Link>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
