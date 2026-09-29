    function renderImages() {
      const container = document.getElementById("images-container");
      if (g_currentImages.length === 0) {
        container.innerHTML = `
          <div class="empty-state">
            <div class="empty-icon">🎉</div>
            <h2>该册次图片已全部清洗完毕或暂无图片</h2>
          </div>`;
        return;
      }

      let html = `
        <div class="smart-vocab-banner" id="smart-vocab-banner" style="display: none;"></div>
        <div class="mode-banner" id="mode-banner"></div>
        <div class="image-grid">`;

      g_currentImages.forEach((img, idx) => {
        const isSelected = g_selectedFiles.has(img.rel_file_path);
        let smartBadgeHtml = "";
        let cardClassExtra = "";

        if (g_vocabDetectData && g_vocabDetectData.pages) {
          const p = g_vocabDetectData.pages.find(item => item.rel_file_path === img.rel_file_path);
          if (p) {
            if (p.is_start) {
              smartBadgeHtml = `<div class="smart-badge badge-start">⭐ 单词表首页</div>`;
              cardClassExtra = "card-vocab-start";
            } else if (p.is_vocab) {
              smartBadgeHtml = `<div class="smart-badge badge-vocab">📖 单词表</div>`;
              cardClassExtra = "card-vocab-page";
            } else {
              smartBadgeHtml = `<div class="smart-badge badge-non-vocab">${p.label || "📄 非词汇"}</div>`;
              cardClassExtra = "card-non-vocab-page";
            }
          }
        }

        html += `
          <div class="image-card ${isSelected ? "selected" : ""} ${g_deleteMode ? "delete-mode-hover" : ""} ${cardClassExtra}" id="card-${idx}" onclick="handleCardClick(${idx}, event)" ondblclick="openLightbox(${idx})">
            <div class="selected-overlay">
              <div class="selected-check-badge">✓</div>
            </div>
            <input type="checkbox" class="card-checkbox" ${isSelected ? "checked" : ""} onclick="event.stopPropagation(); toggleSelectImage('${img.rel_file_path}', ${idx}, this.checked)" />
            ${smartBadgeHtml}
            <div class="page-badge">第 ${img.page_num || "-"} 页</div>
            <div class="thumb-wrapper">
              <img src="/image/${encodeURI(img.rel_file_path)}" loading="lazy" alt="${img.filename}" />
            </div>
            <div class="card-footer">
              <div class="card-info" title="${img.filename}">#${img.idx_num || idx + 1} (${img.size_kb} KB)</div>
              <div class="card-actions">
                <button class="btn-icon-zoom" onclick="event.stopPropagation(); openLightbox(${idx})" title="双击或点击放大预览">🔍</button>
                <button class="btn-icon-del" onclick="event.stopPropagation(); deleteOneImage('${img.rel_file_path}', ${idx})" title="删除此张图片">🗑️</button>
              </div>
            </div>
          </div>`;
      });
      html += `</div>`;
      container.innerHTML = html;
      updateDeleteModeUI();
      if (g_vocabDetectData) {
        renderSmartVocabBanner();
      }
    }

    async function loadVocabDetection(relPath, force = false) {
      const banner = document.getElementById("smart-vocab-banner");
      if (banner && !g_vocabDetectData) {
        banner.style.display = "flex";
        banner.className = "smart-vocab-banner loading";
        banner.innerHTML = `
          <div class="banner-info">
            <span class="banner-icon">🤖</span>
            <div>
              <div class="banner-title">正在智能定位单词表分布...</div>
              <div class="banner-desc">macOS Vision OCR 正在极速分析页面标题、词性与音标特征</div>
            </div>
          </div>
        `;
      }

      try {
        const res = await fetch(`/api/detect_vocab?path=${encodeURIComponent(relPath)}&force=${force ? "1" : "0"}`);
        const data = await res.json();
        if (g_currentRelPath === relPath) {
          g_vocabDetectData = data;
          renderSmartVocabBanner();
          applyVocabBadgesToCards();
        }
      } catch (err) {
        console.error("Vocab detection failed:", err);
        if (banner) banner.style.display = "none";
      }
    }

    function renderSmartVocabBanner() {
      const banner = document.getElementById("smart-vocab-banner");
      if (!banner) return;

      if (!g_vocabDetectData || !g_vocabDetectData.success) {
        banner.style.display = "none";
        return;
      }

      banner.style.display = "flex";
      if (g_vocabDetectData.detected) {
        banner.className = "smart-vocab-banner detected";
        banner.innerHTML = `
          <div class="banner-info">
            <span class="banner-icon">🎯</span>
            <div>
              <div class="banner-title">${g_vocabDetectData.summary}</div>
              <div class="banner-desc">核心单词表共 <b style="color:#10b981; font-size: 13px;">${g_vocabDetectData.vocab_count}</b> 页 · 待清理非单词页 <b style="color:#f87171; font-size: 13px;">${g_vocabDetectData.non_vocab_count}</b> 页</div>
            </div>
          </div>
          <div class="banner-actions">
            ${g_vocabDetectData.non_vocab_count > 0 ? `
              <button class="btn btn-smart-filter" onclick="smartSelectNonVocab()" title="根据智能定位，一键自动勾选所有前置课文与末尾版权封底页">
                ⚡ 一键勾选非单词页 (${g_vocabDetectData.non_vocab_count})
              </button>
            ` : `<span style="color: #10b981; font-size: 13px; font-weight:700;">✨ 当前册次已纯净，无非单词页！</span>`}
            ${g_vocabDetectData.start_idx !== null ? `
              <button class="btn btn-jump-start" onclick="jumpToVocabStart()" title="直接滚动到单词表第一页">
                🎯 跳至单词表首页 (第 ${g_vocabDetectData.start_page} 页)
              </button>
            ` : ""}
            <button class="btn btn-default" onclick="loadVocabDetection(g_currentRelPath, true)" title="清除缓存并重新扫描">
              🔄 重新识别
            </button>
          </div>
        `;
      } else {
        banner.className = "smart-vocab-banner undetected";
        banner.innerHTML = `
          <div class="banner-info">
            <span class="banner-icon">ℹ️</span>
            <div>
              <div class="banner-title">${g_vocabDetectData.summary}</div>
              <div class="banner-desc">请通过右上方快捷按钮或点击图片手动勾选非单词页</div>
            </div>
          </div>
          <div class="banner-actions">
            <button class="btn btn-default" onclick="loadVocabDetection(g_currentRelPath, true)" title="重新尝试识别">
              🔄 重新识别
            </button>
          </div>
        `;
      }
    }

