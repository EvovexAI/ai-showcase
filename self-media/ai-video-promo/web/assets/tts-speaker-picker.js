/**
 * 火山 TTS 音色选择 — 页面内嵌列表（可搜索、试听）
 */
(function (global) {
  const PREVIEW_PLAY = "▶";
  const PREVIEW_STOP = "■";

  let previewAudio = null;
  let previewBtn = null;

  function escHtml(s) {
    return String(s ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }

  function findPreset(presets, value) {
    return presets.find(p => p.id === value) || null;
  }

  function labelFor(presets, value) {
    const preset = findPreset(presets, value);
    if (preset) return preset.label;
    return value ? "自定义音色" : "未选择";
  }

  function previewTextForSpeaker(voiceType, presets) {
    const preset = presets.find(p => p.id === voiceType);
    if (preset?.label) {
      const name = preset.label.replace(/（.*?）/g, "").replace(/\s*2\.0/g, "").trim();
      if (name) return `你好，我是${name}，欢迎试听豆包语音合成效果。`;
    }
    return "你好，欢迎试听豆包语音合成效果。";
  }

  function stopPreview() {
    if (previewAudio) {
      previewAudio.pause();
      previewAudio = null;
    }
    if (previewBtn) {
      previewBtn.classList.remove("is-playing");
      previewBtn.textContent = PREVIEW_PLAY;
      previewBtn = null;
    }
  }

  async function playPreview(voiceType, btn, presets) {
    const voice = String(voiceType || "").trim();
    if (!voice) return;
    if (previewBtn === btn && previewAudio && !previewAudio.paused) {
      stopPreview();
      return;
    }
    stopPreview();
    previewBtn = btn || null;
    if (btn) {
      btn.classList.add("is-playing");
      btn.textContent = PREVIEW_STOP;
    }
    try {
      const resp = await fetch("/api/settings/tts/preview", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ speaker: voice, text: previewTextForSpeaker(voice, presets) }),
      });
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({}));
        throw new Error(err.error || `试听失败 (${resp.status})`);
      }
      const blob = await resp.blob();
      previewAudio = new Audio(URL.createObjectURL(blob));
      previewAudio.onended = () => stopPreview();
      await previewAudio.play();
    } catch (e) {
      stopPreview();
      alert(e.message || "试听失败");
    }
  }

  /**
   * @param {HTMLElement} container
   * @param {{ presets: {id:string,label:string}[], value?: string, onChange?: (v:string)=>void }} opts
   */
  function mountInline(container, { presets = [], value = "", onChange }) {
    let selected = value || "";
    let useCustom = selected && !findPreset(presets, selected);

    container.innerHTML = `
      <div class="tts-inline-picker">
        <div class="tts-inline-selected">
          <span class="tts-inline-selected-label">${escHtml(labelFor(presets, selected))}</span>
          <code class="tts-inline-selected-id">${escHtml(selected || "—")}</code>
        </div>
        <input type="search" class="tts-inline-search settings-input" placeholder="搜索音色名称或 voice_type…" autocomplete="off">
        <div class="tts-inline-list" role="listbox" aria-label="音色列表"></div>
        <label class="tts-inline-custom-toggle">
          <input type="checkbox" class="tts-inline-custom-check"${useCustom ? " checked" : ""}>
          <span>自定义 voice_type</span>
        </label>
        <input type="text" class="tts-inline-custom-input settings-input"
          placeholder="例如 zh_female_vv_uranus_bigtts"
          value="${useCustom ? escHtml(selected) : ""}"${useCustom ? "" : " hidden"}>
        <input type="hidden" class="tts-inline-value" value="${escHtml(selected)}">
      </div>`;

    const root = container.querySelector(".tts-inline-picker");
    const searchEl = root.querySelector(".tts-inline-search");
    const listEl = root.querySelector(".tts-inline-list");
    const selectedLabelEl = root.querySelector(".tts-inline-selected-label");
    const selectedIdEl = root.querySelector(".tts-inline-selected-id");
    const customCheck = root.querySelector(".tts-inline-custom-check");
    const customInput = root.querySelector(".tts-inline-custom-input");
    const hidden = root.querySelector(".tts-inline-value");

    const syncSelectedDisplay = () => {
      selectedLabelEl.textContent = labelFor(presets, selected);
      selectedIdEl.textContent = selected || "—";
      hidden.value = selected;
      onChange?.(selected);
    };

    const paintList = () => {
      const q = searchEl.value.trim().toLowerCase();
      const items = presets.filter(p => !q || `${p.label} ${p.id}`.toLowerCase().includes(q));
      if (!items.length) {
        listEl.innerHTML = `<p class="tts-inline-empty">无匹配音色</p>`;
        return;
      }
      listEl.innerHTML = items.map(p => `
        <div class="tts-inline-item${p.id === selected ? " active" : ""}" data-id="${escHtml(p.id)}">
          <button type="button" class="tts-inline-item-pick">
            <span class="tts-inline-item-label">${escHtml(p.label)}</span>
            <code class="tts-inline-item-id">${escHtml(p.id)}</code>
          </button>
          <button type="button" class="tts-inline-item-preview" title="试听">${PREVIEW_PLAY}</button>
        </div>`).join("");

      listEl.querySelectorAll(".tts-inline-item").forEach(row => {
        const id = row.dataset.id || "";
        row.querySelector(".tts-inline-item-pick")?.addEventListener("click", () => {
          selected = id;
          useCustom = false;
          customCheck.checked = false;
          customInput.hidden = true;
          customInput.value = "";
          syncSelectedDisplay();
          paintList();
        });
        row.querySelector(".tts-inline-item-preview")?.addEventListener("click", (e) => {
          e.stopPropagation();
          playPreview(id, e.currentTarget, presets);
        });
      });
    };

    customCheck.addEventListener("change", () => {
      useCustom = customCheck.checked;
      customInput.hidden = !useCustom;
      if (useCustom) {
        selected = customInput.value.trim();
      } else if (presets.length) {
        selected = findPreset(presets, selected)?.id || presets[0].id;
      }
      syncSelectedDisplay();
      paintList();
    });

    customInput.addEventListener("input", () => {
      if (customCheck.checked) {
        selected = customInput.value.trim();
        syncSelectedDisplay();
      }
    });

    searchEl.addEventListener("input", paintList);
    paintList();
    syncSelectedDisplay();

    return {
      getValue() {
        return customCheck.checked ? customInput.value.trim() : hidden.value.trim();
      },
      setValue(v) {
        selected = v || "";
        useCustom = !!selected && !findPreset(presets, selected);
        customCheck.checked = useCustom;
        customInput.hidden = !useCustom;
        customInput.value = useCustom ? selected : "";
        syncSelectedDisplay();
        paintList();
      },
    };
  }

  global.TtsSpeakerPicker = { mountInline, stopPreview };
})(window);
