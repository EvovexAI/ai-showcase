/* ==============================
   AI 配置管理 — config.js
   每个 AI 模块独立存储完整 API 配置，互不影响
   ============================== */

const Config = (() => {
  const STORAGE_KEY = 'img2post_ai_config_v3';

  /* Provider 模板（仅用于初始化默认值和切换类型时继承字段） */
  const TPL = {
    ark: {
      type: 'ark',
      name: '豆包 Agent Plan',
      apiBase: 'https://ark.cn-beijing.volces.com/api/plan/v3',
      apiKey: '',
      model: 'doubao-seedream-5-0-pro',
    },
    newapi: {
      type: 'openai',
      name: 'NewAPI',
      apiBase: '',
      apiKey: '',
      model: '',
    },
  };

  /* 默认模块配置 */
  const DEFAULTS = {
    aiBg:      { ...TPL.ark },
    aiImage:   { ...TPL.ark },
    aiOptimize: { ...TPL.newapi },
    aiPoster:  { ...TPL.newapi },
  };

  let data = null;

  function load() {
    if (data) return data;
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) {
        const saved = JSON.parse(raw);
        data = {};
        for (const key of Object.keys(DEFAULTS)) {
          data[key] = { ...DEFAULTS[key], ...(saved[key] || {}) };
        }
      } else {
        data = JSON.parse(JSON.stringify(DEFAULTS));
      }
    } catch (e) {
      console.warn('Config load failed:', e);
      data = JSON.parse(JSON.stringify(DEFAULTS));
    }
    return data;
  }

  function save() {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(load()));
    } catch (e) {
      console.warn('Config save failed:', e);
    }
  }

  /** 获取模块完整配置 */
  function getAiBg()      { return load().aiBg; }
  function getAiImage()   { return load().aiImage; }
  function getAiOptimize(){ return load().aiOptimize; }
  function getAiPoster()  { return load().aiPoster; }

  /** 获取模块的 Provider 名称 */
  function getAiBgName()      { return load().aiBg.name || ''; }
  function getAiImageName()   { return load().aiImage.name || ''; }
  function getAiOptimizeName(){ return load().aiOptimize.name || ''; }
  function getAiPosterName()  { return load().aiPoster.name || ''; }

  /** 切换模块的 Provider 类型（继承模板默认值） */
  function setAiBgType(type)      { load().aiBg      = { ...TPL[type], ...(type === load().aiBg.type ? load().aiBg : {}) }; save(); }
  function setAiImageType(type)   { load().aiImage   = { ...TPL[type], ...(type === load().aiImage.type ? load().aiImage : {}) }; save(); }
  function setAiOptimizeType(type){ load().aiOptimize= { ...TPL[type], ...(type === load().aiOptimize.type ? load().aiOptimize : {}) }; save(); }
  function setAiPosterType(type) { load().aiPoster  = { ...TPL[type], ...(type === load().aiPoster.type ? load().aiPoster : {}) }; save(); }

  /** 更新模块的单个字段 */
  function updateAiBg(fields)      { Object.assign(load().aiBg, fields); save(); }
  function updateAiImage(fields)   { Object.assign(load().aiImage, fields); save(); }
  function updateAiOptimize(fields){ Object.assign(load().aiOptimize, fields); save(); }
  function updateAiPoster(fields) { Object.assign(load().aiPoster, fields); save(); }

  /** 获取模板列表 */
  function getTypeOptions() {
    return [
      { value: 'ark', label: '豆包 Agent Plan', type: 'ark' },
      { value: 'newapi', label: 'NewAPI', type: 'openai' },
    ];
  }

  /** 获取某个类型的模板默认值 */
  function getTemplate(type) {
    return TPL[type] ? { ...TPL[type] } : null;
  }

  /** 重置 */
  function resetAll() {
    localStorage.removeItem(STORAGE_KEY);
    data = null;
  }

  return {
    getAiBg, getAiImage, getAiOptimize, getAiPoster,
    getAiBgName, getAiImageName, getAiOptimizeName, getAiPosterName,
    setAiBgType, setAiImageType, setAiOptimizeType, setAiPosterType,
    updateAiBg, updateAiImage, updateAiOptimize, updateAiPoster,
    getTypeOptions, getTemplate, resetAll, load,
  };
})();
