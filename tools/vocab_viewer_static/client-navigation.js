    async function selectBook(relPath, breadcrumbText, elem) {
      document.querySelectorAll(".term-item").forEach(el => el.classList.remove("active"));
      if (elem) elem.classList.add("active");

      g_currentRelPath = relPath;
      g_selectedFiles.clear();
      g_lastClickedIdx = -1;
      g_vocabDetectData = null;
      updateSelectedCount();

      const parts = breadcrumbText.split(" > ");
      document.getElementById("breadcrumb-bar").innerHTML = parts.map((p, i) => `<span>${p}</span>`).join('<span class="breadcrumb-sep">/</span>');
      document.getElementById("toolbar-actions").style.display = "flex";

      const container = document.getElementById("images-container");
      container.innerHTML = '<div style="padding: 40px; text-align: center; color: var(--text-muted);">正在加载高清图...</div>';

      try {
        const res = await fetch(`/api/images?path=${encodeURIComponent(relPath)}`);
        g_currentImages = await res.json();
        renderImages();
        loadVocabDetection(relPath);
        updateTrashCount();
      } catch (err) {
        container.innerHTML = `<div style="color: #f87171; padding: 40px;">加载图片失败: ${err}</div>`;
      }
    }

