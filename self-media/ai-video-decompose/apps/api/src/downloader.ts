// AI Video Decompose - 抖音下载器
// 使用 yt-dlp 下载抖音视频

import { spawn } from 'child_process';
import path from 'path';
import fs from 'fs';

export interface DownloadOptions {
  url: string;
  cookiesPath?: string;
  audioOnly?: boolean;
}

export interface DownloadResult {
  awemeId: string;
  title: string;
  videoPath: string;
  meta?: Record<string, unknown>;
}

export async function downloadDouyin(options: DownloadOptions): Promise<DownloadResult> {
  const { url, cookiesPath, audioOnly = false } = options;
  
  return new Promise((resolve, reject) => {
    const scriptsDir = path.resolve(process.cwd(), 'scripts');
    const scriptPath = path.join(scriptsDir, 'download-douyin.py');
    
    const args: string[] = [url];
    if (cookiesPath) args.push('--cookies', cookiesPath);
    if (audioOnly) args.push('--audio-only');
    
    const env = {
      ...process.env,
      CONTENTOS_DATA_DIR: path.resolve(process.cwd(), 'data'),
    };
    
    const python = spawn('python', [scriptPath, ...args], { env });
    
    let stdout = '';
    let stderr = '';
    
    python.stdout.on('data', (data) => {
      stdout += data.toString();
      process.stdout.write(data);
    });
    
    python.stderr.on('data', (data) => {
      stderr += data.toString();
      process.stderr.write(data);
    });
    
    python.on('close', (code) => {
      if (code === 0) {
        // 解析输出
        const awemeIdMatch = stdout.match(/aweme_id[=:]\s*"?([^"\s]+)"?/);
        const titleMatch = stdout.match(/title[=:]\s*"?([^"\n]+)"?/);
        const videoMatch = stdout.match(/video_path[=:]\s*"?([^"\n]+)"?/);
        
        const awemeId = awemeIdMatch ? awemeIdMatch[1] : '';
        const title = titleMatch ? titleMatch[1] : 'Untitled';
        const videoPath = videoMatch ? videoMatch[1] : '';
        
        resolve({
          awemeId,
          title,
          videoPath,
          meta: { url },
        });
      } else {
        reject(new Error(`Download failed: ${stderr}`));
      }
    });
    
    python.on('error', (err) => {
      reject(err);
    });
  });
}
