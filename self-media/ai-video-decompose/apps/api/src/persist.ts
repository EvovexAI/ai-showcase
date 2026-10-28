import { prisma } from './db.js';
import fs from 'fs';
import path from 'path';
import { generateContentAnalysis } from './content-analyzer.js';

export interface DecomposeResult {
  projectPath: string;
  report: Record<string, unknown>;
  keyframes: string[];
}

export interface DownloadResult {
  awemeId: string;
  title: string;
  videoPath: string;
  meta?: Record<string, unknown>;
}

export interface PersistDecompositionInput {
  result: DecomposeResult;
  awemeId?: string | null;
  contentId?: string | null;
  title?: string;
}

export async function persistDecomposition(input: PersistDecompositionInput) {
  const { result } = input;
  const report = result.report as Record<string, unknown>;
  const title = input.title || (report.title as string) || input.awemeId || 'Untitled video';
  const sceneCount = Array.isArray(report.scenes) ? (report.scenes as unknown[]).length : 0;
  
  // 生成内容分析
  const contentAnalysis = generateContentAnalysis({
    title,
    script: typeof report.script === 'object' && report.script !== null 
      ? (report.script as any).full_text || ''
      : String(report.script || ''),
    duration: typeof report.duration_seconds === 'number' ? report.duration_seconds : 0,
    hashtags: Array.isArray(report.hashtags) ? report.hashtags as string[] : [],
  });

  return prisma.videoDecomposition.create({
    data: {
      awemeId: input.awemeId ?? null,
      title,
      videoPath: String(report.source_video ?? result.projectPath),
      reportJson: JSON.stringify(report),
      durationSeconds: typeof report.duration_seconds === 'number' ? report.duration_seconds : null,
      sceneCount,
      keyframePaths: JSON.stringify(result.keyframes),
      contentId: input.contentId ?? null,
      // 保存内容分析
      contentSummary: contentAnalysis.contentSummary,
      targetAudience: contentAnalysis.targetAudience,
      hooks: contentAnalysis.hooks.join(','),
      keyPoints: contentAnalysis.keyPoints,
      emotions: contentAnalysis.emotions.join(','),
      userGain: contentAnalysis.userGain,
      engagementStrategy: contentAnalysis.engagementStrategy,
      contentType: contentAnalysis.contentType,
    },
  });
}

export async function persistDownloadAsStub(download: DownloadResult) {
  return prisma.videoDecomposition.create({
    data: {
      awemeId: download.awemeId,
      title: download.title,
      videoPath: download.videoPath,
      reportJson: JSON.stringify({
        status: 'downloaded',
        meta: download.meta,
      }),
      durationSeconds: null,
      sceneCount: 0,
      keyframePaths: '[]',
    },
  });
}

export async function listDecompositions(limit = 50) {
  const rows = await prisma.videoDecomposition.findMany({
    orderBy: { createdAt: 'desc' },
    take: limit,
  });
  
  // Parse JSON strings back to objects
  return rows.map(row => ({
    ...row,
    reportJson: JSON.parse(row.reportJson),
    keyframePaths: JSON.parse(row.keyframePaths),
  }));
}

export async function getDecomposition(id: string) {
  const row = await prisma.videoDecomposition.findUnique({ where: { id } });
  if (!row) return null;
  
  return {
    ...row,
    reportJson: JSON.parse(row.reportJson),
    keyframePaths: JSON.parse(row.keyframePaths),
  };
}
