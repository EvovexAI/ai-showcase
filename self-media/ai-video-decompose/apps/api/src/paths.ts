// AI Video Decompose - 路径解析工具

import path from 'path';
import fs from 'fs';

// 默认数据目录
const DEFAULT_DATA_ROOT = 'data';

// 解析数据根目录
export function resolveDataRoot(): string {
  // 可以通过环境变量覆盖
  return process.env.CONTENTOS_DATA_DIR || 
         path.resolve(process.cwd(), DEFAULT_DATA_ROOT);
}

// 解析视频项目目录
export function resolveProjectPath(input: string): string {
  // 如果是完整路径，直接返回
  if (path.isAbsolute(input)) {
    return input;
  }
  
  // 如果是相对路径，基于数据根目录
  return path.resolve(resolveDataRoot(), 'projects', input);
}

// 解析输出目录
export function resolveOutputDir(input: string, outputDir?: string): string {
  if (outputDir) {
    return path.isAbsolute(outputDir) ? outputDir : path.resolve(process.cwd(), outputDir);
  }
  
  // 默认输出到数据目录下的项目文件夹
  return resolveProjectPath(input);
}

// 确保目录存在
export function ensureDir(dirPath: string): void {
  if (!fs.existsSync(dirPath)) {
    fs.mkdirSync(dirPath, { recursive: true });
  }
}

// 从 URL 或 ID 提取 awemeId
export function extractAwemeId(input: string): string | null {
  // 如果已经是纯数字 ID
  if (/^\d+$/.test(input)) {
    return input;
  }
  
  // 从分享链接提取
  const match = input.match(/video\/(\d+)/) || 
                input.match(/(\d{19})/) ||
                input.match(/aweme_id[=:]?\s*(\d+)/i);
  
  return match ? match[1] : null;
}
