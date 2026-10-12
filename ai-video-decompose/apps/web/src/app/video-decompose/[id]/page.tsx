'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';

interface Report {
  title: string;
  duration_label: string;
  duration_seconds: number;
  script?: {
    full_text: string;
    total_chars: number;
    segment_count: number;
    segments?: Array<{
      index: number;
      time_range: string;
      text: string;
      role_guess: string;
    }>;
  };
  voice?: {
    gender_guess: string;
    chars_per_minute: number;
    likely_ai_tts: boolean;
  };
  chapters?: Array<{
    index: number;
    title: string;
    duration_seconds: number;
    time_range: string;
    summary: string;
  }>;
  scenes?: Array<{
    index: number;
    time_range: string;
    duration_seconds: number;
    visual_type: string;
    visual_hint: string;
    speech_text: string;
    frame_path: string;
  }>;
}

interface DecompositionData {
  id: string;
  title: string;
  awemeId: string | null;
  reportJson: Report;
  sceneCount: number;
  createdAt: string;
  keyframePaths: string[];
}

export default function DetailPage({ params }: { params: { id: string } }) {
  const [data, setData] = useState<DecompositionData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'overview' | 'script' | 'chapters' | 'scenes'>('overview');

  const API_BASE = 'http://localhost:3001';

  useEffect(() => {
    fetchDetail();
  }, [params.id]);

  async function fetchDetail() {
    try {
      const res = await fetch(`${API_BASE}/api/video-decompose/${params.id}`);
      if (!res.ok) throw new Error('Failed to fetch');
      const result = await res.json();
      if (result.success) {
        setData(result.data);
      } else {
        setError('数据加载失败');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载失败');
    } finally {
      setLoading(false);
    }
  }

  if (loading) {
    return (
      <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <p>加载中...</p>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div style={{ minHeight: '100vh', background: '#f5f5f5' }}>
        <div style={{ background: '#1a1a2e', color: 'white', padding: '20px 40px' }}>
          <Link href="/video-decompose" style={{ color: '#4caf50', textDecoration: 'none' }}>
            ← 返回列表
          </Link>
        </div>
        <div style={{ maxWidth: '1200px', margin: '40px auto', padding: '20px', color: '#c62828' }}>
          {error || '数据不存在'}
        </div>
      </div>
    );
  }

  const report = data.reportJson;

  return (
    <div style={{ minHeight: '100vh', background: '#f5f5f5' }}>
      {/* 头部 */}
      <div style={{ background: '#1a1a2e', color: 'white', padding: '20px 40px' }}>
        <Link href="/video-decompose" style={{ color: '#4caf50', textDecoration: 'none', fontSize: '14px' }}>
          ← 返回列表
        </Link>
        <h1 style={{ margin: '12px 0 0', fontSize: '28px' }}>
          {report.title || data.title}
        </h1>
        <p style={{ margin: '8px 0 0', opacity: 0.8, fontSize: '14px' }}>
          {report.duration_label} • {data.sceneCount} 个分镜 • {report.script?.total_chars || 0} 字
        </p>
      </div>

      <div style={{ maxWidth: '1200px', margin: '0 auto', padding: '40px 20px' }}>
        {/* 快速操作 */}
        <div style={{
          background: 'white',
          borderRadius: '12px',
          padding: '20px',
          marginBottom: '24px',
          boxShadow: '0 2px 8px rgba(0,0,0,0.08)',
          display: 'flex',
          gap: '12px',
          flexWrap: 'wrap',
          alignItems: 'center'
        }}>
          <span style={{ fontSize: '14px', fontWeight: 'bold', color: '#666' }}>📥 导出：</span>
          <a
            href={`${API_BASE}/api/video-decompose/${params.id}/export/script.md`}
            style={{
              padding: '8px 16px',
              background: '#e3f2fd',
              color: '#1565c0',
              borderRadius: '6px',
              textDecoration: 'none',
              fontSize: '14px',
              fontWeight: 'bold'
            }}
          >
            脚本 (Markdown)
          </a>
          <a
            href={`${API_BASE}/api/video-decompose/${params.id}/export/chapters.json`}
            style={{
              padding: '8px 16px',
              background: '#f3e5f5',
              color: '#6a1b9a',
              borderRadius: '6px',
              textDecoration: 'none',
              fontSize: '14px',
              fontWeight: 'bold'
            }}
          >
            章节表 (JSON)
          </a>
          <a
            href={`${API_BASE}/api/video-decompose/${params.id}/export/scenes.json`}
            style={{
              padding: '8px 16px',
              background: '#e8f5e9',
              color: '#2e7d32',
              borderRadius: '6px',
              textDecoration: 'none',
              fontSize: '14px',
              fontWeight: 'bold'
            }}
          >
            分镜表 (JSON)
          </a>
        </div>

        {/* 标签页导航 */}
        <div style={{ display: 'flex', gap: '8px', marginBottom: '24px', borderBottom: '2px solid #e0e0e0' }}>
          {(['overview', 'script', 'chapters', 'scenes'] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              style={{
                padding: '12px 20px',
                border: 'none',
                background: 'transparent',
                color: activeTab === tab ? '#4caf50' : '#999',
                borderBottom: activeTab === tab ? '3px solid #4caf50' : 'none',
                cursor: 'pointer',
                fontWeight: activeTab === tab ? 'bold' : 'normal',
                fontSize: '14px',
                marginBottom: '-2px'
              }}
            >
              {tab === 'overview' && '📊 概览'}
              {tab === 'script' && '📝 脚本'}
              {tab === 'chapters' && '📚 章节'}
              {tab === 'scenes' && '🎬 分镜'}
            </button>
          ))}
        </div>

        {/* 内容区域 */}
        {activeTab === 'overview' && (
          <div style={{ display: 'grid', gap: '20px' }}>
            {/* 基础信息卡 */}
            <div style={{ background: 'white', borderRadius: '12px', padding: '24px', boxShadow: '0 2px 8px rgba(0,0,0,0.08)' }}>
              <h2 style={{ margin: '0 0 16px', fontSize: '18px' }}>📋 基础信息</h2>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '16px' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '12px', color: '#999', marginBottom: '4px' }}>视频标题</label>
                  <p style={{ margin: 0, fontSize: '16px', fontWeight: 'bold' }}>{report.title || '未命名'}</p>
                </div>
                <div>
                  <label style={{ display: 'block', fontSize: '12px', color: '#999', marginBottom: '4px' }}>时长</label>
                  <p style={{ margin: 0, fontSize: '16px', fontWeight: 'bold' }}>{report.duration_label}</p>
                </div>
                <div>
                  <label style={{ display: 'block', fontSize: '12px', color: '#999', marginBottom: '4px' }}>分镜数</label>
                  <p style={{ margin: 0, fontSize: '16px', fontWeight: 'bold' }}>{data.sceneCount}</p>
                </div>
                <div>
                  <label style={{ display: 'block', fontSize: '12px', color: '#999', marginBottom: '4px' }}>抖音ID</label>
                  <p style={{ margin: 0, fontSize: '16px', fontWeight: 'bold' }}>{data.awemeId || '本地视频'}</p>
                </div>
                <div>
                  <label style={{ display: 'block', fontSize: '12px', color: '#999', marginBottom: '4px' }}>创建时间</label>
                  <p style={{ margin: 0, fontSize: '16px', fontWeight: 'bold' }}>
                    {new Date(data.createdAt).toLocaleString('zh-CN')}
                  </p>
                </div>
              </div>
            </div>

            {/* 脚本统计 */}
            {report.script && (
              <div style={{ background: 'white', borderRadius: '12px', padding: '24px', boxShadow: '0 2px 8px rgba(0,0,0,0.08)' }}>
                <h2 style={{ margin: '0 0 16px', fontSize: '18px' }}>📝 脚本统计</h2>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px' }}>
                  <div style={{ padding: '12px', background: '#f5f5f5', borderRadius: '8px' }}>
                    <p style={{ margin: 0, fontSize: '12px', color: '#999' }}>总字数</p>
                    <p style={{ margin: '4px 0 0', fontSize: '24px', fontWeight: 'bold', color: '#4caf50' }}>
                      {report.script.total_chars}
                    </p>
                  </div>
                  <div style={{ padding: '12px', background: '#f5f5f5', borderRadius: '8px' }}>
                    <p style={{ margin: 0, fontSize: '12px', color: '#999' }}>段落数</p>
                    <p style={{ margin: '4px 0 0', fontSize: '24px', fontWeight: 'bold', color: '#2196f3' }}>
                      {report.script.segment_count}
                    </p>
                  </div>
                  <div style={{ padding: '12px', background: '#f5f5f5', borderRadius: '8px' }}>
                    <p style={{ margin: 0, fontSize: '12px', color: '#999' }}>平均每段</p>
                    <p style={{ margin: '4px 0 0', fontSize: '24px', fontWeight: 'bold', color: '#ff9800' }}>
                      {Math.round(report.script.total_chars / (report.script.segment_count || 1))}
                    </p>
                  </div>
                </div>
              </div>
            )}

            {/* 语音分析 */}
            {report.voice && (
              <div style={{ background: 'white', borderRadius: '12px', padding: '24px', boxShadow: '0 2px 8px rgba(0,0,0,0.08)' }}>
                <h2 style={{ margin: '0 0 16px', fontSize: '18px' }}>🎙️ 语音分析</h2>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px' }}>
                  <div>
                    <label style={{ display: 'block', fontSize: '12px', color: '#999', marginBottom: '4px' }}>性别猜测</label>
                    <p style={{ margin: 0, fontSize: '16px', fontWeight: 'bold' }}>
                      {report.voice.gender_guess === 'Male' ? '👨 男性' : report.voice.gender_guess === 'Female' ? '👩 女性' : report.voice.gender_guess}
                    </p>
                  </div>
                  <div>
                    <label style={{ display: 'block', fontSize: '12px', color: '#999', marginBottom: '4px' }}>说话速度</label>
                    <p style={{ margin: 0, fontSize: '16px', fontWeight: 'bold' }}>{report.voice.chars_per_minute} 字/分钟</p>
                  </div>
                  <div>
                    <label style={{ display: 'block', fontSize: '12px', color: '#999', marginBottom: '4px' }}>是否AI合成</label>
                    <p style={{ margin: 0, fontSize: '16px', fontWeight: 'bold' }}>
                      {report.voice.likely_ai_tts ? '✓ 可能是' : '✗ 不太可能'}
                    </p>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* 脚本标签页 */}
        {activeTab === 'script' && (
          <div style={{ background: 'white', borderRadius: '12px', padding: '24px', boxShadow: '0 2px 8px rgba(0,0,0,0.08)' }}>
            <h2 style={{ margin: '0 0 16px', fontSize: '18px' }}>📝 完整脚本</h2>
            {report.script ? (
              <>
                <div style={{
                  padding: '16px',
                  background: '#f5f5f5',
                  borderRadius: '8px',
                  marginBottom: '24px',
                  fontSize: '14px',
                  lineHeight: '1.8',
                  whiteSpace: 'pre-wrap',
                  wordBreak: 'break-word',
                  color: '#333'
                }}>
                  {report.script.full_text}
                </div>

                {report.script.segments && report.script.segments.length > 0 && (
                  <div>
                    <h3 style={{ margin: '0 0 16px', fontSize: '16px' }}>按段落拆解</h3>
                    <div style={{ display: 'grid', gap: '12px' }}>
                      {report.script.segments.map((seg, i) => (
                        <div key={i} style={{ padding: '12px', border: '1px solid #e0e0e0', borderRadius: '8px' }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                            <strong>第 {seg.index + 1} 段</strong>
                            <span style={{ fontSize: '12px', color: '#999' }}>
                              {seg.time_range} • {seg.role_guess || '-'}
                            </span>
                          </div>
                          <p style={{ margin: 0, fontSize: '14px', color: '#333', lineHeight: '1.6' }}>
                            {seg.text}
                          </p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </>
            ) : (
              <p style={{ color: '#999' }}>暂无脚本数据</p>
            )}
          </div>
        )}

        {/* 章节标签页 */}
        {activeTab === 'chapters' && (
          <div style={{ background: 'white', borderRadius: '12px', padding: '24px', boxShadow: '0 2px 8px rgba(0,0,0,0.08)' }}>
            <h2 style={{ margin: '0 0 16px', fontSize: '18px' }}>📚 章节结构</h2>
            {report.chapters && report.chapters.length > 0 ? (
              <div style={{ display: 'grid', gap: '12px' }}>
                {report.chapters.map((ch, i) => (
                  <div key={i} style={{
                    padding: '16px',
                    border: '1px solid #e0e0e0',
                    borderRadius: '8px',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'start'
                  }}>
                    <div style={{ flex: 1 }}>
                      <div style={{ display: 'flex', gap: '12px', alignItems: 'baseline', marginBottom: '8px' }}>
                        <span style={{ background: '#4caf50', color: 'white', padding: '2px 8px', borderRadius: '4px', fontSize: '12px', fontWeight: 'bold' }}>
                          {ch.index + 1}
                        </span>
                        <h3 style={{ margin: 0, fontSize: '16px', fontWeight: 'bold' }}>{ch.title}</h3>
                        <span style={{ fontSize: '12px', color: '#999' }}>{ch.time_range}</span>
                      </div>
                      <p style={{ margin: '8px 0 0', fontSize: '14px', color: '#666' }}>{ch.summary}</p>
                    </div>
                    <div style={{ textAlign: 'right', fontSize: '12px', color: '#999', marginLeft: '16px' }}>
                      ⏱️ {ch.duration_seconds.toFixed(1)}s
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p style={{ color: '#999' }}>暂无章节数据</p>
            )}
          </div>
        )}

        {/* 分镜标签页 */}
        {activeTab === 'scenes' && (
          <div style={{ background: 'white', borderRadius: '12px', padding: '24px', boxShadow: '0 2px 8px rgba(0,0,0,0.08)' }}>
            <h2 style={{ margin: '0 0 16px', fontSize: '18px' }}>🎬 分镜详情 ({data.sceneCount})</h2>
            {report.scenes && report.scenes.length > 0 ? (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: '16px' }}>
                {report.scenes.map((scene, i) => (
                  <div key={i} style={{
                    border: '1px solid #e0e0e0',
                    borderRadius: '8px',
                    overflow: 'hidden',
                  }}>
                    {scene.frame_path && (
                      <img
                        src={scene.frame_path}
                        alt={`Scene ${scene.index}`}
                        style={{ width: '100%', height: '200px', objectFit: 'cover', background: '#f5f5f5' }}
                      />
                    )}
                    <div style={{ padding: '12px' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px', alignItems: 'center' }}>
                        <span style={{ background: '#e3f2fd', color: '#1565c0', padding: '2px 8px', borderRadius: '4px', fontSize: '12px', fontWeight: 'bold' }}>
                          分镜 {scene.index + 1}
                        </span>
                        <span style={{ fontSize: '12px', color: '#999' }}>{scene.time_range}</span>
                      </div>
                      <div style={{ fontSize: '12px', color: '#666', marginBottom: '8px' }}>
                        <strong>{scene.visual_type}</strong> • {scene.duration_seconds.toFixed(1)}s
                      </div>
                      <p style={{ margin: 0, fontSize: '13px', color: '#333', lineHeight: '1.5' }}>
                        {scene.speech_text || scene.visual_hint}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p style={{ color: '#999' }}>暂无分镜数据</p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
