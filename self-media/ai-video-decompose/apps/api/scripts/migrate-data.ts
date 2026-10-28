import fs from 'fs';
import path from 'path';
import { prisma } from '../src/db.js';

const sourceProjectPath = 'd:\\dev\\github\\evo\\ContentOS\\data\\projects\\7689897956208189583';

async function migrate() {
  console.log('🔄 开始迁移数据...');
  console.log(`📂 源目录: ${sourceProjectPath}`);

  // 读取 report.json
  const reportPath = path.join(sourceProjectPath, 'analysis', 'report.json');
  if (!fs.existsSync(reportPath)) {
    console.error(`✗ report.json not found: ${reportPath}`);
    process.exit(1);
  }

  const report = JSON.parse(fs.readFileSync(reportPath, 'utf-8'));

  // 读取关键帧列表
  const scenesDir = path.join(sourceProjectPath, 'analysis', 'scenes');
  const keyframes: string[] = [];
  if (fs.existsSync(scenesDir)) {
    const files = fs.readdirSync(scenesDir).filter(f => f.endsWith('.jpg'));
    keyframes.push(...files.map(f => path.join(scenesDir, f)));
  }

  // 创建数据库记录
  const data = {
    awemeId: '7689897956208189583',
    title: 'Opus5.5 演示视频 - 1830帧代码生成',
    videoPath: path.join(sourceProjectPath, 'video.mp4'),
    reportJson: JSON.stringify(report),
    durationSeconds: report.duration_seconds || null,
    sceneCount: report.scenes ? (report.scenes as unknown[]).length : 0,
    keyframePaths: JSON.stringify(keyframes),
    contentId: null,
  };

  console.log('');
  console.log('📋 准备插入数据:');
  console.log(`  - 标题: ${data.title}`);
  console.log(`  - 视频时长: ${data.durationSeconds}s`);
  console.log(`  - 关键帧数: ${keyframes.length}`);
  console.log('');

  try {
    const result = await prisma.videoDecomposition.create({ data });
    console.log('✅ 数据迁移成功!');
    console.log(`   ID: ${result.id}`);
    console.log(`   标题: ${result.title}`);
  } catch (error) {
    console.error('❌ 迁移失败:', error);
    process.exit(1);
  } finally {
    await prisma.$disconnect();
  }
}

migrate();
