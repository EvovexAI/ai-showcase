// AI Video Decompose - API Server
// 独立的视频拆解 API 服务

import Fastify from 'fastify';
import cors from '@fastify/cors';
import { z } from 'zod';
import { decomposeVideo } from './analyzer.js';
import { downloadDouyin } from './downloader.js';
import { listDecompositions, getDecomposition, persistDecomposition, persistDownloadAsStub } from './persist.js';

const fastify = Fastify({
  logger: true,
});

// 注册 CORS
await fastify.register(cors, {
  origin: true,
});

// ============ 路由定义 ============

// 健康检查
fastify.get('/health', async (_request, reply) => {
  return reply.send({ success: true, data: { ok: true, timestamp: new Date().toISOString() } });
});

// 列出所有拆解
fastify.get('/api/video-decompose', async (request, reply) => {
  const q = request.query as { limit?: string };
  const limit = q.limit ? Number(q.limit) : 50;
  const data = await listDecompositions(Number.isFinite(limit) ? limit : 50);
  return reply.send({ success: true, data });
});

// 获取单个拆解详情
fastify.get('/api/video-decompose/:id', async (request, reply) => {
  const { id } = request.params as { id: string };
  const row = await getDecomposition(id);
  if (!row) {
    return reply.code(404).send({ success: false, error: 'Not found' });
  }
  return reply.send({ success: true, data: row });
});

// 下载视频
const downloadBodySchema = z.object({
  url: z.string().min(1),
  cookiesPath: z.string().optional(),
  audioOnly: z.boolean().optional(),
  persist: z.boolean().optional().default(false),
});

fastify.post('/api/video-decompose/download', async (request, reply) => {
  const body = downloadBodySchema.parse(request.body);
  
  let result;
  try {
    result = await downloadDouyin({
      url: body.url,
      cookiesPath: body.cookiesPath,
      audioOnly: body.audioOnly,
    });
  } catch (error) {
    return reply.code(500).send({ 
      success: false, 
      error: error instanceof Error ? error.message : 'Download failed' 
    });
  }
  
  if (body.persist) {
    await persistDownloadAsStub(result);
  }
  
  return reply.send({ success: true, data: result });
});

// 分析视频
const analyzeBodySchema = z.object({
  input: z.string().min(1),
  outputDir: z.string().optional(),
  model: z.enum(['tiny', 'base', 'small', 'medium']).optional(),
  full: z.boolean().optional().default(true),
  visionPrep: z.boolean().optional().default(false),
  keyframeMode: z.enum(['transcript', 'custom', 'scene']).optional(),
  frameCount: z.number().int().positive().optional(),
  force: z.boolean().optional(),
  awemeId: z.string().optional(),
  contentId: z.string().optional(),
  persist: z.boolean().optional().default(true),
});

fastify.post('/api/video-decompose/analyze', async (request, reply) => {
  const body = analyzeBodySchema.parse(request.body);
  
  let result;
  try {
    result = await decomposeVideo({
      input: body.input,
      outputDir: body.outputDir,
      model: body.model,
      full: body.full,
      visionPrep: body.visionPrep,
      keyframeMode: body.keyframeMode,
      frameCount: body.frameCount,
      force: body.force,
    });
  } catch (error) {
    return reply.code(500).send({ 
      success: false, 
      error: error instanceof Error ? error.message : 'Analysis failed' 
    });
  }
  
  let saved = null;
  if (body.persist) {
    saved = await persistDecomposition({
      result,
      awemeId: body.awemeId ?? null,
      contentId: body.contentId ?? null,
    });
  }
  
  return reply.send({ success: true, data: { ...result, saved } });
});

// 导出报告（Markdown）
fastify.get('/api/video-decompose/:id/export/report.md', async (request, reply) => {
  const { id } = request.params as { id: string };
  const row = await getDecomposition(id);
  if (!row) {
    return reply.code(404).send({ success: false, error: 'Not found' });
  }
  
  const md = formatReportMarkdown(row);
  const filename = `report_${row.id}.md`;
  
  return reply
    .header('Content-Type', 'text/markdown; charset=utf-8')
    .header('Content-Disposition', `attachment; filename="${filename}"`)
    .send(md);
});

// 导出脚本（Markdown）
fastify.get('/api/video-decompose/:id/export/script.md', async (request, reply) => {
  const { id } = request.params as { id: string };
  const row = await getDecomposition(id);
  if (!row) {
    return reply.code(404).send({ success: false, error: 'Not found' });
  }
  
  const report = row.reportJson as any;
  const md = formatScriptMarkdown(report);
  const filename = `script_${row.id}.md`;
  
  return reply
    .header('Content-Type', 'text/markdown; charset=utf-8')
    .header('Content-Disposition', `attachment; filename="${filename}"`)
    .send(md);
});

// 导出章节表（JSON）
fastify.get('/api/video-decompose/:id/export/chapters.json', async (request, reply) => {
  const { id } = request.params as { id: string };
  const row = await getDecomposition(id);
  if (!row) {
    return reply.code(404).send({ success: false, error: 'Not found' });
  }
  
  const report = row.reportJson as any;
  const data = {
    title: row.title,
    duration: report.duration_label,
    chapters: report.chapters || [],
  };
  const filename = `chapters_${row.id}.json`;
  
  return reply
    .header('Content-Type', 'application/json')
    .header('Content-Disposition', `attachment; filename="${filename}"`)
    .send(data);
});

// 导出分镜表（JSON）
fastify.get('/api/video-decompose/:id/export/scenes.json', async (request, reply) => {
  const { id } = request.params as { id: string };
  const row = await getDecomposition(id);
  if (!row) {
    return reply.code(404).send({ success: false, error: 'Not found' });
  }
  
  const report = row.reportJson as any;
  const scenes = Array.isArray(report.scenes) ? report.scenes : [];
  const filename = `scenes_${row.id}.json`;
  
  return reply
    .header('Content-Type', 'application/json')
    .header('Content-Disposition', `attachment; filename="${filename}"`)
    .send({
      title: row.title,
      totalScenes: scenes.length,
      scenes: scenes.map((s: any) => ({
        index: s.index,
        time: s.time_range,
        duration: s.duration_seconds,
        visualType: s.visual_type,
        visualHint: s.visual_hint,
        speechText: s.speech_text,
      })),
    });
});

function formatReportMarkdown(row: any): string {
  const lines: string[] = [];
  
  lines.push(`# 📊 ${row.title || '视频分析报告'}\n`);
  
  lines.push(`**创建时间：** ${row.createdAt}\n`);
  lines.push(`**视频时长：** ${row.durationSeconds ? Math.round(row.durationSeconds / 60) + '分' + (row.durationSeconds % 60) + '秒' : '未知'}\n`);
  lines.push(`**分镜数：** ${row.sceneCount}\n\n`);
  
  if (row.contentSummary) {
    lines.push(`## 📝 视频内容\n`);
    lines.push(`${row.contentSummary}\n`);
  }
  
  if (row.targetAudience) {
    lines.push(`## 👥 目标人群\n`);
    lines.push(`${row.targetAudience}\n`);
  }
  
  if (row.hooks) {
    lines.push(`## 🎣 视频钩子\n`);
    const hooks = row.hooks.split(',').filter((h: string) => h.trim());
    hooks.forEach((hook: string) => {
      lines.push(`- ${hook.trim()}`);
    });
    lines.push('');
  }
  
  if (row.keyPoints) {
    lines.push(`## ⭐ 重点\n`);
    lines.push(`${row.keyPoints}\n`);
  }
  
  if (row.emotions) {
    lines.push(`## 😊 情绪\n`);
    const emotions = row.emotions.split(',').filter((e: string) => e.trim());
    lines.push(`${emotions.join('、')}\n`);
  }
  
  if (row.userGain) {
    lines.push(`## 🎁 观众获取\n`);
    lines.push(`${row.userGain}\n`);
  }
  
  if (row.engagementStrategy) {
    lines.push(`## 💬 吸引观众停留策略\n`);
    lines.push(`${row.engagementStrategy}\n`);
  }
  
  if (row.contentType) {
    lines.push(`## 🎬 作品类型\n`);
    lines.push(`${row.contentType}\n`);
  }
  
  // 添加脚本信息
  const report = row.reportJson as any;
  if (report.script) {
    const script = report.script;
    lines.push(`## 📄 脚本统计\n`);
    lines.push(`- **总字数：** ${script.total_chars || 0} 字\n`);
    lines.push(`- **段落数：** ${script.segment_count || 0} 段\n`);
    lines.push(`- **平均每段：** ${script.avg_chars_per_segment || 0} 字\n`);
  }
  
  if (report.voice) {
    lines.push(`\n## 🎙️ 语音信息\n`);
    lines.push(`- **性别猜测：** ${report.voice.gender_guess || '-'}\n`);
    lines.push(`- **说话速度：** ${report.voice.chars_per_minute || 0} 字/分钟\n`);
    lines.push(`- **是否AI合成：** ${report.voice.likely_ai_tts ? '是' : '否'}\n`);
  }
  
  return lines.join('\n');
}

function formatScriptMarkdown(report: any): string {
  const script = report.script || {};
  const lines: string[] = [];
  
  lines.push(`# 🎬 ${report.title || '视频脚本'}\n`);
  lines.push(`**时长：** ${report.duration_label}\n`);
  lines.push(`**总字数：** ${script.total_chars || 0} 字\n`);
  lines.push(`**段落数：** ${script.segment_count || 0}\n`);
  lines.push(`**平均每段：** ${script.avg_chars_per_segment || 0} 字\n`);
  
  if (report.voice) {
    lines.push(`\n## 📢 语音信息\n`);
    lines.push(`- **性别猜测：** ${report.voice.gender_guess || '-'}\n`);
    lines.push(`- **节奏：** ${report.voice.chars_per_minute || 0} 字/分钟\n`);
    lines.push(`- **可能是AI合成：** ${report.voice.likely_ai_tts ? '是' : '否'}\n`);
  }
  
  lines.push(`\n## 📝 完整脚本\n`);
  lines.push('```\n');
  lines.push(script.full_text || '');
  lines.push('\n```\n');
  
  if (Array.isArray(script.segments) && script.segments.length > 0) {
    lines.push(`\n## 📋 按段落拆解\n`);
    script.segments.forEach((seg: any) => {
      lines.push(`### 第 ${seg.index + 1} 段 (${seg.time_range})\n`);
      lines.push(`**角色：** ${seg.role_guess || '-'}\n`);
      lines.push(`**内容：**\n> ${seg.text}\n`);
    });
  }
  
  return lines.join('\n');
}

// ============ 启动服务 ============

const PORT = 3001;
const HOST = '0.0.0.0';

async function start() {
  try {
    await fastify.listen({ port: PORT, host: HOST });
    console.log(`
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║   🎬 AI Video Decompose - 视频拆解服务                    ║
║                                                           ║
║   API:    http://localhost:${PORT}                           ║
║   Health: http://localhost:${PORT}/health                   ║
║                                                           ║
║   Endpoints:                                             ║
║   - GET  /api/video-decompose        列出所有拆解          ║
║   - GET  /api/video-decompose/:id   获取详情              ║
║   - POST /api/video-decompose/download  下载视频            ║
║   - POST /api/video-decompose/analyze  分析视频            ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
    `);
  } catch (err) {
    fastify.log.error(err);
    process.exit(1);
  }
}

start();
