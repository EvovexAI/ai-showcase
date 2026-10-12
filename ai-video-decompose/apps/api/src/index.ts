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

// 导出脚本（Markdown）
fastify.get('/api/video-decompose/:id/export/script.md', async (request, reply) => {
  const { id } = request.params as { id: string };
  const row = await getDecomposition(id);
  if (!row) {
    return reply.code(404).send({ success: false, error: 'Not found' });
  }
  
  const report = row.reportJson as any;
  const md = formatScriptMarkdown(report);
  
  return reply
    .header('Content-Type', 'text/markdown; charset=utf-8')
    .header('Content-Disposition', `attachment; filename="${row.title || 'script'}.md"`)
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
  
  return reply
    .header('Content-Type', 'application/json')
    .header('Content-Disposition', `attachment; filename="${row.title || 'chapters'}.json"`)
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
  
  return reply
    .header('Content-Type', 'application/json')
    .header('Content-Disposition', `attachment; filename="${row.title || 'scenes'}.json"`)
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
