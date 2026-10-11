/* ==============================
   导出功能 — export.js
   html2canvas 渲染导出（CSS 级保真）+ 可调分辨率
   ============================== */

const Export = (() => {
  const modal = document.getElementById('exportModal');
  const btnPng = document.getElementById('exportPng');
  const btnJpg = document.getElementById('exportJpg');
  const btnClose = document.getElementById('exportModalClose');
  const resolutionSelect = document.getElementById('exportResolution');

  function open() { modal.classList.add('open'); }
  function close() { modal.classList.remove('open'); }

  /** 主导出 */
  async function renderAndDownload(format) {
    const scale = parseInt(resolutionSelect?.value || 4);
    const canvasEl = Canvas.getElement();
    const selectedId = Elements.getSelectedId();

    // 取消选中，避免导出图里有高亮框
    if (selectedId) {
      const sel = Elements.getElement(selectedId);
      if (sel) sel.classList.remove('selected');
    }

    const savedZoom = Canvas.getZoom();
    document.documentElement.style.setProperty('--zoom', '1');
    close();

    // Toast
    const toast = document.createElement('div');
    toast.style.cssText = 'position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);background:rgba(255,255,255,0.97);color:#1f2329;padding:20px 30px;border-radius:12px;font-size:13px;z-index:300;text-align:center;min-width:200px;box-shadow:0 12px 40px rgba(15,23,42,0.18);border:1px solid #e4e7ec;';
    toast.innerHTML = `<div style="margin-bottom:8px;">⏳ 正在导出…</div><div style="font-size:11px;color:#6b7280;">${scale}x 分辨率</div>`;
    document.body.appendChild(toast);

    try {
      await new Promise(r => requestAnimationFrame(r));

      const exportCanvas = await html2canvas(canvasEl, {
        scale,
        backgroundColor: format === 'png' ? null : '#ffffff',
        logging: false,
        imageTimeout: 15000,
      });

      const mimeType = format === 'jpg' ? 'image/jpeg' : 'image/png';
      const quality = format === 'jpg' ? 0.95 : undefined;
      const blob = await new Promise(r => exportCanvas.toBlob(r, mimeType, quality));
      const dataUrl = URL.createObjectURL(blob);

      const link = document.createElement('a');
      link.download = `poster_${Date.now()}_${exportCanvas.width}x${exportCanvas.height}.${format}`;
      link.href = dataUrl;
      link.click();
      setTimeout(() => URL.revokeObjectURL(dataUrl), 1000);

      toast.innerHTML = '<div style="color:#16a34a;">✅ 导出成功</div>';
      setTimeout(() => document.body.removeChild(toast), 1200);
    } catch (err) {
      console.error('导出失败:', err);
      toast.innerHTML = `<div style="color:#dc2626;">❌ 导出失败</div><div style="font-size:11px;margin-top:6px;">${err.message}</div>`;
      setTimeout(() => document.body.removeChild(toast), 3000);
    } finally {
      document.documentElement.style.setProperty('--zoom', savedZoom);
      if (selectedId) {
        const sel = Elements.getElement(selectedId);
        if (sel) sel.classList.add('selected');
      }
    }
  }

  btnPng.addEventListener('click', () => renderAndDownload('png'));
  btnJpg.addEventListener('click', () => renderAndDownload('jpg'));
  btnClose.addEventListener('click', close);
  modal.addEventListener('click', (e) => { if (e.target === modal) close(); });

  return { open };
})();
