// 内容分析 - 生成视频内容的深层分析数据
// 包括：内容简介、目标人群、钩子、重点、情绪、获取价值、吸引策略、作品类型

export interface ContentAnalysis {
  contentSummary: string;    // 这篇视频主要讲的是什么？
  targetAudience: string;    // 目标人群
  hooks: string[];           // 钩子（数组）
  keyPoints: string;         // 重点
  emotions: string[];        // 情绪（数组）
  userGain: string;          // 观众能获取到什么东西
  engagementStrategy: string; // 怎么吸引观众停留
  contentType: string;       // 作品类型方向
}

/**
 * 根据视频脚本和其他信息生成内容分析
 */
export function generateContentAnalysis(videoData: {
  title: string;
  script: string;
  duration: number;
  hashtags?: string[];
}): ContentAnalysis {
  // 这是一个模拟分析器，实际生产环境应该使用 LLM 或 AI 分析
  // 我们基于脚本内容和视频标题来推断这些信息

  const script = videoData.script.toLowerCase();
  const title = videoData.title;
  
  // 内容简介
  const contentSummary = extractContentSummary(title, script);
  
  // 目标人群
  const targetAudience = inferTargetAudience(script, title);
  
  // 钩子
  const hooks = extractHooks(script, title);
  
  // 重点
  const keyPoints = extractKeyPoints(script);
  
  // 情绪
  const emotions = detectEmotions(script);
  
  // 观众获取
  const userGain = inferUserGain(script, contentSummary);
  
  // 吸引策略
  const engagementStrategy = inferEngagementStrategy(script);
  
  // 作品类型
  const contentType = classifyContentType(title, script, videoData.hashtags);
  
  return {
    contentSummary,
    targetAudience,
    hooks,
    keyPoints,
    emotions,
    userGain,
    engagementStrategy,
    contentType,
  };
}

function extractContentSummary(title: string, script: string): string {
  // 从标题提取关键信息
  if (title.includes('教程') || title.includes('教') || script.includes('步骤')) {
    return `这是一个教程类视频，主要教授用户如何完成某项任务或学习某个技能。`;
  }
  
  if (title.includes('分享') || title.includes('建议')) {
    return `这是一个知识分享类视频，分享作者的经验、见解或建议。`;
  }
  
  if (title.includes('评测') || title.includes('体验') || title.includes('测试')) {
    return `这是一个产品评测类视频，对产品或服务进行深度体验和评价。`;
  }
  
  if (title.includes('故事') || title.includes('分享')) {
    return `这是一个个人故事分享类视频，分享作者的经历或见闻。`;
  }
  
  // 默认推断
  if (script.includes('第一步') || script.includes('首先')) {
    return `这是一个指导类视频，通过分步骤的讲解，指导观众完成某项任务。`;
  }
  
  return `这是一个内容分享视频，通过口头讲解的方式向观众传递信息和知识。`;
}

function inferTargetAudience(script: string, title: string): string {
  const scriptLower = script.toLowerCase();
  
  if (scriptLower.includes('初学者') || scriptLower.includes('新手')) {
    return '初学者/新手用户';
  }
  
  if (scriptLower.includes('专业') || scriptLower.includes('高级')) {
    return '专业人士/进阶用户';
  }
  
  if (script.includes('学生') || script.includes('年轻人')) {
    return '学生/年轻人';
  }
  
  if (title.includes('家长') || title.includes('父母')) {
    return '家长/父母';
  }
  
  if (title.includes('职场') || title.includes('上班族')) {
    return '上班族/职场人士';
  }
  
  // 根据脚本复杂度判断
  if (scriptLower.includes('复杂') || scriptLower.includes('深入')) {
    return '有相关背景知识的用户';
  }
  
  return '普通观众/所有年龄段';
}

function extractHooks(script: string, title: string): string[] {
  const hooks: string[] = [];
  
  // 寻找常见的钩子表达
  if (script.includes('想知道') || script.includes('有没有想过')) {
    hooks.push('提问激发好奇心');
  }
  
  if (script.includes('惊人') || script.includes('不敢相信') || script.includes('绝了')) {
    hooks.push('制造惊喜感');
  }
  
  if (script.includes('错过') || script.includes('后悔') || script.includes('浪费')) {
    hooks.push('制造紧急感');
  }
  
  if (script.includes('最新') || script.includes('首次') || script.includes('独家')) {
    hooks.push('强调稀缺性');
  }
  
  if (script.includes('免费') || script.includes('不花钱')) {
    hooks.push('经济利益吸引');
  }
  
  if (script.includes('简单') || script.includes('轻松') || script.includes('只需')) {
    hooks.push('强调简便性');
  }
  
  if (script.includes('秘密') || script.includes('技巧') || script.includes('窍门')) {
    hooks.push('暗示秘诀/技巧');
  }
  
  if (script.includes('大家') || script.includes('你们') || script.includes('朋友们')) {
    hooks.push('建立亲切感');
  }
  
  // 如果没有找到明显的钩子，设置默认的
  if (hooks.length === 0) {
    hooks.push('开场吸引', '内容承诺');
  }
  
  return hooks;
}

function extractKeyPoints(script: string): string {
  const scriptLower = script.toLowerCase();
  
  // 寻找强调词
  if (scriptLower.includes('最关键') || scriptLower.includes('最重要')) {
    return '核心要点被明确强调';
  }
  
  if (scriptLower.includes('第一步') || scriptLower.includes('首先')) {
    return '通过分步骤的讲解突出重点';
  }
  
  if (scriptLower.includes('必须') || scriptLower.includes('一定要') || scriptLower.includes('务必')) {
    return '通过强调性语言突出重点';
  }
  
  if (scriptLower.includes('结果') || scriptLower.includes('效果')) {
    return '强调最终的效果和结果';
  }
  
  return '通过重复和强调来突出核心内容';
}

function detectEmotions(script: string): string[] {
  const emotions: string[] = [];
  
  if (script.includes('兴奋') || script.includes('太棒') || script.includes('非常') || script.includes('绝了')) {
    emotions.push('兴奋');
  }
  
  if (script.includes('遗憾') || script.includes('可惜') || script.includes('失败')) {
    emotions.push('遗憾');
  }
  
  if (script.includes('感谢') || script.includes('谢谢') || script.includes('感激')) {
    emotions.push('感谢');
  }
  
  if (script.includes('担心') || script.includes('害怕') || script.includes('紧张')) {
    emotions.push('紧张');
  }
  
  if (script.includes('高兴') || script.includes('开心') || script.includes('满意')) {
    emotions.push('满意');
  }
  
  if (script.includes('惊讶') || script.includes('意外') || script.includes('竟然')) {
    emotions.push('惊讶');
  }
  
  if (emotions.length === 0) {
    emotions.push('信息性', '教育性');
  }
  
  return emotions;
}

function inferUserGain(script: string, contentSummary: string): string {
  const scriptLower = script.toLowerCase();
  
  if (scriptLower.includes('学会') || scriptLower.includes('掌握') || scriptLower.includes('了解')) {
    return '观众学会了新的知识或技能';
  }
  
  if (scriptLower.includes('节省') || scriptLower.includes('省') || scriptLower.includes('效率')) {
    return '观众可以节省时间或金钱';
  }
  
  if (scriptLower.includes('方法') || scriptLower.includes('技巧') || scriptLower.includes('窍门')) {
    return '观众获得了实用的方法和技巧';
  }
  
  if (scriptLower.includes('灵感') || scriptLower.includes('启发')) {
    return '观众获得了灵感和启发';
  }
  
  if (scriptLower.includes('解决') || scriptLower.includes('问题')) {
    return '观众学会了如何解决问题';
  }
  
  if (contentSummary.includes('教程')) {
    return '观众学会了具体的执行步骤';
  }
  
  return '观众获得了有价值的信息和知识';
}

function inferEngagementStrategy(script: string): string {
  const scriptLower = script.toLowerCase();
  
  // 检查多个参与策略
  const strategies: string[] = [];
  
  if (scriptLower.includes('点赞') || scriptLower.includes('关注') || scriptLower.includes('评论')) {
    strategies.push('直接呼吁互动');
  }
  
  if (scriptLower.includes('下期') || scriptLower.includes('持续') || scriptLower.includes('更新')) {
    strategies.push('预告下期内容');
  }
  
  if (scriptLower.includes('问你') || scriptLower.includes('你们说') || scriptLower.includes('怎么看')) {
    strategies.push('提问互动');
  }
  
  if (scriptLower.includes('分享') || scriptLower.includes('传播') || scriptLower.includes('告诉朋友')) {
    strategies.push('鼓励分享转发');
  }
  
  if (scriptLower.includes('悬念') || scriptLower.includes('剧情') || scriptLower.includes('反转')) {
    strategies.push('制造剧情张力');
  }
  
  if (scriptLower.includes('视觉') || scriptLower.includes('画面') || scriptLower.includes('展示')) {
    strategies.push('通过视觉吸引');
  }
  
  if (strategies.length === 0) {
    strategies.push('通过内容质量和信息完整性吸引观众停留');
  }
  
  return strategies.join('、');
}

function classifyContentType(title: string, script: string, hashtags?: string[]): string {
  const titleLower = title.toLowerCase();
  const scriptLower = script.toLowerCase();
  
  if (titleLower.includes('教程') || titleLower.includes('教') || scriptLower.includes('第一步')) {
    return '教程/指南';
  }
  
  if (titleLower.includes('评测') || titleLower.includes('体验') || titleLower.includes('测试')) {
    return '评测/体验';
  }
  
  if (titleLower.includes('分享') && scriptLower.includes('我')) {
    return '经验分享';
  }
  
  if (titleLower.includes('技巧') || titleLower.includes('建议') || titleLower.includes('窍门')) {
    return '技巧/建议';
  }
  
  if (titleLower.includes('故事') || scriptLower.includes('我的经历')) {
    return '故事分享';
  }
  
  if (titleLower.includes('讲解') || titleLower.includes('科普')) {
    return '讲解/科普';
  }
  
  if (hashtags?.some(tag => tag.includes('vlog') || tag.includes('日常'))) {
    return 'VLOG/日常';
  }
  
  if (scriptLower.includes('对比') || scriptLower.includes('优缺点')) {
    return '对比分析';
  }
  
  return '内容分享';
}
