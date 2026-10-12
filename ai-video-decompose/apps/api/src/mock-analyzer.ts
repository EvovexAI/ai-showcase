// Mock 分析器 - 用于演示，生成测试数据
// 在没有真实Python脚本的情况下，生成完整的报告数据

import fs from 'fs';
import path from 'path';
import { DecomposeResult } from './analyzer.js';

export function generateMockReport(videoPath: string): DecomposeResult {
  // 创建临时项目目录
  const projectPath = path.join(process.cwd(), 'data', 'projects', `project_${Date.now()}`);
  const analysisDir = path.join(projectPath, 'analysis');
  const scenesDir = path.join(analysisDir, 'scenes');

  // 确保目录存在
  fs.mkdirSync(scenesDir, { recursive: true });

  // 生成扩展的分析报告数据（包含更多维度）
  const report = {
    generated_at: new Date().toISOString(),
    source_video: videoPath,
    title: `视频拆解 - ${path.basename(videoPath)}`,
    duration_seconds: 90,
    duration_label: '1分30秒',
    hashtags: ['视频拆解', '内容分析', '口播脚本'],
    
    script: {
      total_chars: 1850,
      segment_count: 8,
      avg_chars_per_segment: 231,
      full_text: `大家好，欢迎来到我的频道。今天我要给大家分享一个非常实用的技巧，相信对你会有很大的帮助。

首先我们需要了解这个方法的原理。这个方法基于最新的研究成果，已经被数百万人验证有效。

让我先为大家演示一下整个过程。你看，这样做的好处是可以节省大量时间。

现在我们来看看具体的步骤。第一步非常重要，一定要认真操作。

接下来是第二步，这一步决定了最终的效果。所以请务必按照我说的来做。

然后是第三步，这是整个过程中最关键的环节。很多人就是在这一步失败了。

现在我们已经完成了主要部分，最后一步就是验证结果。如果你看到这个效果，说明操作成功了。

感谢大家的观看，如果觉得有帮助，请点赞、评论、关注，我会继续为大家分享更多实用的内容。`,
      segments: [
        {
          index: 0,
          start: 2,
          end: 10,
          text: '大家好，欢迎来到我的频道。今天我要给大家分享一个非常实用的技巧，相信对你会有很大的帮助。',
          chars: 52,
          time_range: '0:02-0:10',
          role_guess: '女性',
        },
        {
          index: 1,
          start: 10,
          end: 25,
          text: '首先我们需要了解这个方法的原理。这个方法基于最新的研究成果，已经被数百万人验证有效。',
          chars: 48,
          time_range: '0:10-0:25',
          role_guess: '女性',
        },
        {
          index: 2,
          start: 25,
          end: 40,
          text: '让我先为大家演示一下整个过程。你看，这样做的好处是可以节省大量时间。',
          chars: 40,
          time_range: '0:25-0:40',
          role_guess: '女性',
        },
        {
          index: 3,
          start: 40,
          end: 50,
          text: '现在我们来看看具体的步骤。第一步非常重要，一定要认真操作。',
          chars: 32,
          time_range: '0:40-0:50',
          role_guess: '女性',
        },
        {
          index: 4,
          start: 50,
          end: 60,
          text: '接下来是第二步，这一步决定了最终的效果。所以请务必按照我说的来做。',
          chars: 36,
          time_range: '0:50-0:60',
          role_guess: '女性',
        },
        {
          index: 5,
          start: 60,
          end: 70,
          text: '然后是第三步，这是整个过程中最关键的环节。很多人就是在这一步失败了。',
          chars: 36,
          time_range: '0:60-0:70',
          role_guess: '女性',
        },
        {
          index: 6,
          start: 70,
          end: 80,
          text: '现在我们已经完成了主要部分，最后一步就是验证结果。如果你看到这个效果，说明操作成功了。',
          chars: 48,
          time_range: '0:70-0:80',
          role_guess: '女性',
        },
        {
          index: 7,
          start: 80,
          end: 90,
          text: '感谢大家的观看，如果觉得有帮助，请点赞、评论、关注，我会继续为大家分享更多实用的内容。',
          chars: 48,
          time_range: '0:80-0:90',
          role_guess: '女性',
        },
      ],
    },

    voice: {
      pitch_hz_median: 220,
      gender_guess: 'Female',
      energy_mean: 0.65,
      speech_seconds: 85,
      speech_ratio: 0.94,
      chars_per_minute: 1234,
      likely_ai_tts: false,
      note: '清晰的女性人声，口语表达流畅，节奏适中',
    },

    chapters: [
      {
        index: 0,
        start: 0,
        end: 10,
        time_range: '0:00-0:10',
        duration_seconds: 10,
        chars: 52,
        role: '开场',
        title: '问候与引入',
        summary: '主播自我介绍，引出今天的主题',
        text: '大家好，欢迎来到我的频道。今天我要给大家分享一个非常实用的技巧。',
      },
      {
        index: 1,
        start: 10,
        end: 40,
        time_range: '0:10-0:40',
        duration_seconds: 30,
        chars: 120,
        role: '原理讲解',
        title: '方法原理与演示',
        summary: '详细讲解该方法的原理和具体步骤演示',
        text: '首先我们需要了解这个方法的原理。这个方法基于最新的研究成果。让我先为大家演示一下。',
      },
      {
        index: 2,
        start: 40,
        end: 75,
        time_range: '0:40-0:75',
        duration_seconds: 35,
        chars: 104,
        role: '步骤指导',
        title: '分步骤操作指南',
        summary: '逐步讲解操作的每一个细节和要点',
        text: '现在我们来看看具体的步骤。第一步非常重要。接下来是第二步。然后是第三步。',
      },
      {
        index: 3,
        start: 75,
        end: 90,
        time_range: '0:75-0:90',
        duration_seconds: 15,
        chars: 48,
        role: '结尾',
        title: '总结与互动',
        summary: '总结内容，感谢观看，邀请互动',
        text: '感谢大家的观看，如果觉得有帮助，请点赞、评论、关注。',
      },
    ],

    scenes: [
      {
        index: 0,
        start: 2,
        end: 10,
        frame_path: '/mock/frames/scene_001.jpg',
        visual_type: '人物特写',
        visual_hint: '主播面向镜头，室内场景',
        text: '大家好，欢迎来到我的频道',
        speech_index: 0,
        time_range: '0:02-0:10',
        duration_seconds: 8,
        speech_text: '大家好，欢迎来到我的频道。今天我要给大家分享一个非常实用的技巧，相信对你会有很大的帮助。',
      },
      {
        index: 1,
        start: 10,
        end: 18,
        frame_path: '/mock/frames/scene_002.jpg',
        visual_type: '手部特写',
        visual_hint: '展示操作步骤，特写手部动作',
        text: '首先我们需要了解方法的原理',
        speech_index: 1,
        time_range: '0:10-0:18',
        duration_seconds: 8,
        speech_text: '首先我们需要了解这个方法的原理。这个方法基于最新的研究成果。',
      },
      {
        index: 2,
        start: 18,
        end: 25,
        frame_path: '/mock/frames/scene_003.jpg',
        visual_type: '产品展示',
        visual_hint: '产品或工具摆放展示',
        text: '这样做的好处是可以节省时间',
        speech_index: 1,
        time_range: '0:18-0:25',
        duration_seconds: 7,
        speech_text: '你看，这样做的好处是可以节省大量时间。',
      },
      {
        index: 3,
        start: 25,
        end: 35,
        frame_path: '/mock/frames/scene_004.jpg',
        visual_type: '步骤演示',
        visual_hint: '展示第一步的具体操作',
        text: '第一步非常重要',
        speech_index: 3,
        time_range: '0:25-0:35',
        duration_seconds: 10,
        speech_text: '现在我们来看看具体的步骤。第一步非常重要，一定要认真操作。',
      },
      {
        index: 4,
        start: 35,
        end: 45,
        frame_path: '/mock/frames/scene_005.jpg',
        visual_type: '步骤演示',
        visual_hint: '展示第二步的具体操作',
        text: '接下来是第二步',
        speech_index: 4,
        time_range: '0:35-0:45',
        duration_seconds: 10,
        speech_text: '接下来是第二步，这一步决定了最终的效果。所以请务必按照我说的来做。',
      },
      {
        index: 5,
        start: 45,
        end: 55,
        frame_path: '/mock/frames/scene_006.jpg',
        visual_type: '步骤演示',
        visual_hint: '展示第三步的具体操作',
        text: '然后是第三步',
        speech_index: 5,
        time_range: '0:45-0:55',
        duration_seconds: 10,
        speech_text: '然后是第三步，这是整个过程中最关键的环节。很多人就是在这一步失败了。',
      },
      {
        index: 6,
        start: 55,
        end: 70,
        frame_path: '/mock/frames/scene_007.jpg',
        visual_type: '结果展示',
        visual_hint: '展示最终的操作结果',
        text: '这是整个过程完成后的效果',
        speech_index: 6,
        time_range: '0:55-0:70',
        duration_seconds: 15,
        speech_text: '现在我们已经完成了主要部分，最后一步就是验证结果。如果你看到这个效果，说明操作成功了。',
      },
      {
        index: 7,
        start: 70,
        end: 90,
        frame_path: '/mock/frames/scene_008.jpg',
        visual_type: '人物特写',
        visual_hint: '主播再次面向镜头，号召互动',
        text: '感谢观看，请点赞关注',
        speech_index: 7,
        time_range: '0:70-0:90',
        duration_seconds: 20,
        speech_text: '感谢大家的观看，如果觉得有帮助，请点赞、评论、关注，我会继续为大家分享更多实用的内容。',
      },
    ],

    aligned: [
      {
        index: 0,
        start: 0,
        end: 10,
        time_range: '0:00-0:10',
        duration_seconds: 10,
        chars: 52,
        role: '开场',
        title: '问候与引入',
        summary: '主播自我介绍，引出今天的主题',
        text: '大家好，欢迎来到我的频道。',
        scene_count: 1,
        visual_types: ['人物特写'],
        visual_summary: '主播面向镜头讲话',
        keyframes: ['scene_001.jpg'],
      },
      {
        index: 1,
        start: 10,
        end: 40,
        time_range: '0:10-0:40',
        duration_seconds: 30,
        chars: 120,
        role: '正文',
        title: '方法原理与演示',
        summary: '详细讲解该方法的原理和具体步骤演示',
        text: '首先我们需要了解这个方法的原理。',
        scene_count: 3,
        visual_types: ['手部特写', '产品展示', '步骤演示'],
        visual_summary: '展示产品和操作步骤',
        keyframes: ['scene_002.jpg', 'scene_003.jpg', 'scene_004.jpg'],
      },
      {
        index: 2,
        start: 40,
        end: 75,
        time_range: '0:40-0:75',
        duration_seconds: 35,
        chars: 104,
        role: '正文',
        title: '分步骤操作指南',
        summary: '逐步讲解操作的每一个细节和要点',
        text: '现在我们来看看具体的步骤。',
        scene_count: 3,
        visual_types: ['步骤演示', '步骤演示', '结果展示'],
        visual_summary: '展示各步骤的操作过程',
        keyframes: ['scene_005.jpg', 'scene_006.jpg', 'scene_007.jpg'],
      },
      {
        index: 3,
        start: 75,
        end: 90,
        time_range: '0:75-0:90',
        duration_seconds: 15,
        chars: 48,
        role: '结尾',
        title: '总结与互动',
        summary: '总结内容，感谢观看，邀请互动',
        text: '感谢大家的观看。',
        scene_count: 1,
        visual_types: ['人物特写'],
        visual_summary: '主播号召互动',
        keyframes: ['scene_008.jpg'],
      },
    ],

    keyframe_mode: 'transcript',

    // 新增：内容分析维度
    content_analysis: {
      main_topics: ['AI工具', '选择技巧', '生产力提升', '效率工具'],
      keywords: [
        { word: 'AI', frequency: 12, relevance: 0.95 },
        { word: '工具', frequency: 8, relevance: 0.88 },
        { word: '选择', frequency: 6, relevance: 0.82 },
        { word: '新手', frequency: 5, relevance: 0.75 },
        { word: '推荐', frequency: 4, relevance: 0.70 },
      ],
      sentiment: 'positive',
      sentiment_score: 0.85,
      tone: '专业、实用、友善',
      content_type: '教程/讲解',
      target_audience: '新手/初学者/职场人士',
      complexity_level: 'medium',
    },

    // 新增：互动优化建议
    engagement_suggestions: [
      {
        category: '开场优化',
        priority: 'high',
        suggestion: '开场Hook可以更加吸引眼球，尝试提出问题或悬念',
        estimated_impact: '提高完播率15-25%',
      },
      {
        category: '节奏优化',
        priority: 'medium',
        suggestion: '中段可以加入更多视觉变化或转场效果',
        estimated_impact: '提高用户停留时间10%',
      },
      {
        category: '互动号召',
        priority: 'high',
        suggestion: '结尾的互动号召可以更具体（如"评论你的答案"而非泛泛号召）',
        estimated_impact: '提高评论率20%',
      },
      {
        category: '字幕优化',
        priority: 'medium',
        suggestion: '关键词和重点信息需要用字幕突出',
        estimated_impact: '提高理解度和分享意愿',
      },
    ],

    // 新增：内容评分
    content_scores: {
      overall_score: 78,
      originality: 72,
      clarity: 85,
      engagement_potential: 76,
      seo_friendliness: 68,
      production_quality: 80,
      pacing: 74,
      call_to_action: 70,
    },

    // 新增：SEO 和传播数据
    seo_metadata: {
      title: '从80个AI工具中如何选择 - 新手必看教程',
      description: '完整讲解新手选择AI工具的方法论和实用建议，包括评估标准、工具对比和快速上手技巧',
      recommended_hashtags: ['#AI', '#AI工具', '#效率提升', '#新手教程', '#职场技能'],
      recommended_keywords: [
        'AI工具选择',
        '新手AI工具教程',
        'AI工具对比',
        '生产力工具',
        '工作效率',
      ],
    },

    // 新增：类似视频推荐
    similar_videos: [
      {
        title: 'ChatGPT 新手快速上手指南',
        similarity_score: 0.92,
        expected_audience_overlap: 0.85,
      },
      {
        title: '2024年最实用的5个AI工具评测',
        similarity_score: 0.88,
        expected_audience_overlap: 0.78,
      },
      {
        title: '如何用AI提高工作效率50%',
        similarity_score: 0.84,
        expected_audience_overlap: 0.72,
      },
    ],

    // 新增：发布建议
    publication_recommendations: {
      best_posting_time: '工作日下午2-4点',
      recommended_platforms: ['抖音', 'YouTube', 'B站', '小红书'],
      optimal_duration: '2-5分钟',
      suggested_thumbnail_style: '人物特写+数字突出',
      expected_ctr: '6-8%',
      expected_completion_rate: '65-75%',
    },

    // 新增：字幕和文本优化
    subtitle_optimization: {
      current_coverage: '部分（仅关键词）',
      recommended_coverage: '100%（全文字幕）',
      emphasis_points: [
        { time: '0:05-0:10', text: '新手如果从80个AI工具中选择', emphasis: '核心问题' },
        { time: '0:15-0:25', text: '评估标准和选择方法', emphasis: '核心内容' },
        { time: '0:85-0:90', text: '点赞、评论、关注', emphasis: 'CTA' },
      ],
      subtitle_style_recommendation: '白色字体，黑色或半透明背景，字号适中便于阅读',
    },
  };

  // 保存报告到文件
  const reportPath = path.join(analysisDir, 'report.json');
  fs.writeFileSync(reportPath, JSON.stringify(report, null, 2), 'utf-8');

  // 生成模拟关键帧（只创建空文件作为占位符）
  for (let i = 1; i <= 8; i++) {
    const framePath = path.join(scenesDir, `scene_${String(i).padStart(3, '0')}.jpg`);
    // 创建一个简单的1x1像素JPG占位符
    const jpgHeader = Buffer.from([
      0xff, 0xd8, 0xff, 0xe0, 0x00, 0x10, 0x4a, 0x46, 0x49, 0x46, 0x00, 0x01, 0x01, 0x00, 0x00, 0x01,
      0x00, 0x01, 0x00, 0x00, 0xff, 0xdb, 0x00, 0x43, 0x00, 0x08, 0x06, 0x06, 0x07, 0x06, 0x05, 0x08,
      0x07, 0x07, 0x07, 0x09, 0x09, 0x08, 0x0a, 0x0c, 0x14, 0x0d, 0x0c, 0x0b, 0x0b, 0x0c, 0x19, 0x12,
      0x13, 0x0f, 0x14, 0x1d, 0x1a, 0x1f, 0x1e, 0x1d, 0x1a, 0x1c, 0x1c, 0x20, 0x24, 0x2e, 0x27, 0x20,
      0x22, 0x2c, 0x23, 0x1c, 0x1c, 0x28, 0x37, 0x29, 0x2c, 0x30, 0x31, 0x34, 0x34, 0x34, 0x1f, 0x27,
      0x39, 0x3d, 0x38, 0x32, 0x3c, 0x2e, 0x33, 0x34, 0x32, 0xff, 0xc0, 0x00, 0x0b, 0x08, 0x00, 0x01,
      0x00, 0x01, 0x01, 0x01, 0x11, 0x00, 0xff, 0xc4, 0x00, 0x1f, 0x00, 0x00, 0x01, 0x05, 0x01, 0x01,
      0x01, 0x01, 0x01, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x01, 0x02, 0x03, 0x04,
      0x05, 0x06, 0x07, 0x08, 0x09, 0x0a, 0x0b, 0xff, 0xc4, 0x00, 0xb5, 0x10, 0x00, 0x02, 0x01, 0x03,
      0x03, 0x02, 0x04, 0x03, 0x05, 0x05, 0x04, 0x04, 0x00, 0x00, 0x01, 0x7d, 0x01, 0x02, 0x03, 0x00,
      0x04, 0x11, 0x05, 0x12, 0x21, 0x31, 0x41, 0x06, 0x13, 0x51, 0x61, 0x07, 0x22, 0x71, 0x14, 0x32,
      0x81, 0x91, 0xa1, 0x08, 0x23, 0x42, 0xb1, 0xc1, 0x15, 0x52, 0xd1, 0xf0, 0x24, 0x33, 0x62, 0x72,
      0x82, 0x09, 0x0a, 0x16, 0x17, 0x18, 0x19, 0x1a, 0x25, 0x26, 0x27, 0x28, 0x29, 0x2a, 0x34, 0x35,
      0x36, 0x37, 0x38, 0x39, 0x3a, 0x43, 0x44, 0x45, 0x46, 0x47, 0x48, 0x49, 0x4a, 0x53, 0x54, 0x55,
      0x56, 0x57, 0x58, 0x59, 0x5a, 0x63, 0x64, 0x65, 0x66, 0x67, 0x68, 0x69, 0x6a, 0x73, 0x74, 0x75,
      0x76, 0x77, 0x78, 0x79, 0x7a, 0x83, 0x84, 0x85, 0x86, 0x87, 0x88, 0x89, 0x8a, 0x92, 0x93, 0x94,
      0x95, 0x96, 0x97, 0x98, 0x99, 0x9a, 0xa2, 0xa3, 0xa4, 0xa5, 0xa6, 0xa7, 0xa8, 0xa9, 0xaa, 0xb2,
      0xb3, 0xb4, 0xb5, 0xb6, 0xb7, 0xb8, 0xb9, 0xba, 0xc2, 0xc3, 0xc4, 0xc5, 0xc6, 0xc7, 0xc8, 0xc9,
      0xca, 0xd2, 0xd3, 0xd4, 0xd5, 0xd6, 0xd7, 0xd8, 0xd9, 0xda, 0xe1, 0xe2, 0xe3, 0xe4, 0xe5, 0xe6,
      0xe7, 0xe8, 0xe9, 0xea, 0xf1, 0xf2, 0xf3, 0xf4, 0xf5, 0xf6, 0xf7, 0xf8, 0xf9, 0xfa, 0xff, 0xda,
      0x00, 0x08, 0x01, 0x01, 0x00, 0x00, 0x3f, 0x00, 0xfb, 0xd4, 0xff, 0xd9,
    ]);
    fs.writeFileSync(framePath, jpgHeader);
  }

  // 返回分析结果
  return {
    projectPath,
    report,
    keyframes: [
      path.join(scenesDir, 'scene_001.jpg'),
      path.join(scenesDir, 'scene_002.jpg'),
      path.join(scenesDir, 'scene_003.jpg'),
      path.join(scenesDir, 'scene_004.jpg'),
      path.join(scenesDir, 'scene_005.jpg'),
      path.join(scenesDir, 'scene_006.jpg'),
      path.join(scenesDir, 'scene_007.jpg'),
      path.join(scenesDir, 'scene_008.jpg'),
    ],
  };
}
