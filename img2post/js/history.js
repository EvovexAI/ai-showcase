/* ==============================
   撤销/重做 — history.js
   布局快照栈，支持 Ctrl+Z 撤销 / Ctrl+Y 重做
   最大保存 50 个快照
   ============================== */

const History = (() => {
  const MAX_SNAPSHOTS = 50;
  let undoStack = [];   // 过去的快照
  let redoStack = [];   // 被撤销的快照（用于重做）
  let debounceTimer = null;
  let ignoreNextPush = false; // 防止 applyLayoutData 触发 snapshot

  /** 获取当前布局序列化快照 */
  function capture() {
    return Layout.serialize();
  }

  /** 推入快照（普通用户操作后调用） */
  function push() {
    if (debounceTimer) clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
      if (ignoreNextPush) { ignoreNextPush = false; return; }
      const snapshot = capture();
      undoStack.push(snapshot);
      if (undoStack.length > MAX_SNAPSHOTS) undoStack.shift();
      redoStack = []; // 新操作清空重做栈
      updateButtonStates();
    }, 80);
  }

  /** 撤销 */
  function undo() {
    if (undoStack.length === 0) return;

    if (debounceTimer) { clearTimeout(debounceTimer); debounceTimer = null; }

    // 当前状态推入 redo
    redoStack.push(capture());
    // 弹出上一个状态
    const prev = undoStack.pop();

    ignoreNextPush = true;
    Layout.applyLayoutData(prev);
    updateButtonStates();
  }

  /** 重做 */
  function redo() {
    if (redoStack.length === 0) return;

    // 当前状态推入 undo
    undoStack.push(capture());
    // 弹出重做状态
    const next = redoStack.pop();

    ignoreNextPush = true;
    Layout.applyLayoutData(next);
    updateButtonStates();
  }

  /** 更新工具栏撤销/重做按钮状态 */
  function updateButtonStates() {
    const btnUndo = document.getElementById('btnUndo');
    const btnRedo = document.getElementById('btnRedo');
    if (btnUndo) btnUndo.disabled = undoStack.length === 0;
    if (btnRedo) btnRedo.disabled = redoStack.length === 0;
  }

  /** 判断是否可以撤销 */
  function canUndo() { return undoStack.length > 0; }

  /** 判断是否可以重做 */
  function canRedo() { return redoStack.length > 0; }

  /** 清空历史 */
  function clear() {
    undoStack = [];
    redoStack = [];
    updateButtonStates();
  }

  return { push, undo, redo, canUndo, canRedo, clear, capture };
})();

// 挂载到 window（覆盖浏览器内置 History 构造函数）
window.History = History;
