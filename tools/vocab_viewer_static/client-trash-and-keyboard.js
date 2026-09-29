    async function updateTrashCount() {
      if (!g_currentRelPath) return;
      try {
        const res = await fetch(`/api/trash?path=${encodeURIComponent(g_currentRelPath)}`);
        const items = await res.json();
        const badge = document.getElementById("trash-badge-count");
        if (badge) badge.innerText = items.length;
      } catch (e) {
        console.error("Failed to fetch trash count", e);
      }
    }

    async function openTrashModal() {
      if (!g_currentRelPath) {
        showToast("请先选择一本教材", "warning");
        return;
      }
      const modal = document.getElementById("trash-modal");
      const subtitle = document.getElementById("trash-modal-subtitle");
      subtitle.innerText = `[${g_currentRelPath}]`;
      modal.classList.add("active");

      const body = document.getElementById("trash-modal-body");
      body.innerHTML = '<div style="text-align: center; padding: 40px; color: #94a3b8;">正在加载回收站图片...</div>';

      g_selectedTrashFiles.clear();
      updateTrashSelectedCount();

      try {
        const res = await fetch(`/api/trash?path=${encodeURIComponent(g_currentRelPath)}`);
        g_trashImages = await res.json();
        renderTrashModal();
      } catch (err) {
        body.innerHTML = `<div style="color: #f87171; padding: 30px;">加载回收站失败: ${err}</div>`;
      }
    }

    function closeTrashModal() {
      const modal = document.getElementById("trash-modal");
      modal.classList.remove("active");
    }

    function handleTrashModalOverlayClick(e) {
      if (e.target.id === "trash-modal") {
        closeTrashModal();
      }
    }

    function renderTrashModal() {
      const body = document.getElementById("trash-modal-body");
      if (g_trashImages.length === 0) {
        body.innerHTML = `
          <div style="text-align: center; padding: 60px 20px; color: #64748b;">
            <div style="font-size: 40px; margin-bottom: 10px;">🍃</div>
            <div style="font-size: 15px; color: #94a3b8;">当前册次回收站为空，没有被删除的图片</div>
          </div>`;
        return;
      }

      let html = `<div class="trash-grid">`;
      g_trashImages.forEach((img, idx) => {
        const isSel = g_selectedTrashFiles.has(img.rel_file_path);
        html += `
          <div class="trash-card ${isSel ? "selected" : ""}" id="trash-card-${idx}" onclick="toggleSelectTrashImage('${img.rel_file_path}', ${idx})">
            <input type="checkbox" class="trash-card-checkbox" ${isSel ? "checked" : ""} onclick="event.stopPropagation(); toggleSelectTrashImage('${img.rel_file_path}', ${idx}, this.checked)" />
            <div class="page-badge">第 ${img.page_num || "-"} 页</div>
            <div class="thumb-wrapper">
              <img src="/trash_image/${encodeURI(img.rel_file_path)}" loading="lazy" alt="${img.filename}" />
            </div>
            <div class="trash-card-footer">
              <span title="${img.filename}">#${img.idx_num || idx + 1} (${img.size_kb} KB)</span>
              <button class="btn-restore-single" onclick="event.stopPropagation(); restoreOneImage('${img.rel_file_path}')">↩️ 恢复此张</button>
            </div>
          </div>`;
      });
      html += `</div>`;
      body.innerHTML = html;
    }

    function toggleSelectTrashImage(relPath, idx, isChecked) {
      if (isChecked === undefined) {
        if (g_selectedTrashFiles.has(relPath)) {
          g_selectedTrashFiles.delete(relPath);
        } else {
          g_selectedTrashFiles.add(relPath);
        }
      } else {
        if (isChecked) {
          g_selectedTrashFiles.add(relPath);
        } else {
          g_selectedTrashFiles.delete(relPath);
        }
      }
      updateTrashCardsDOM();
      updateTrashSelectedCount();
    }

    function updateTrashCardsDOM() {
      g_trashImages.forEach((img, idx) => {
        const card = document.getElementById(`trash-card-${idx}`);
        if (!card) return;
        const isSel = g_selectedTrashFiles.has(img.rel_file_path);
        if (isSel) card.classList.add("selected");
        else card.classList.remove("selected");
        const cb = card.querySelector(".trash-card-checkbox");
        if (cb) cb.checked = isSel;
      });
    }

    function updateTrashSelectedCount() {
      const c = g_selectedTrashFiles.size;
      const badge = document.getElementById("trash-selected-count");
      if (badge) badge.innerText = c;
      const btn = document.getElementById("btn-batch-restore");
      if (btn) btn.disabled = (c === 0);
    }

    function toggleSelectAllTrash() {
      if (g_selectedTrashFiles.size === g_trashImages.length) {
        g_selectedTrashFiles.clear();
      } else {
        g_selectedTrashFiles.clear();
        g_trashImages.forEach(img => g_selectedTrashFiles.add(img.rel_file_path));
      }
      updateTrashCardsDOM();
      updateTrashSelectedCount();
    }

    async function restoreOneImage(relFilePath) {
      await performRestore([relFilePath]);
    }

    async function restoreSelectedTrash() {
      if (g_selectedTrashFiles.size === 0) return;
      await performRestore(Array.from(g_selectedTrashFiles));
    }

    async function performRestore(files) {
      try {
        const res = await fetch("/api/restore", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ files: files })
        });
        const result = await res.json();
        showToast(`成功恢复 ${result.restored} 张图片至原册次！`, "success");

        // 重新加载主图片列表与回收站列表
        const imgRes = await fetch(`/api/images?path=${encodeURIComponent(g_currentRelPath)}`);
        g_currentImages = await imgRes.json();
        renderImages();
        loadVocabDetection(g_currentRelPath, true);
        loadTree();

        // 刷新回收站弹窗
        const trashRes = await fetch(`/api/trash?path=${encodeURIComponent(g_currentRelPath)}`);
        g_trashImages = await trashRes.json();
        g_selectedTrashFiles.clear();
        updateTrashSelectedCount();
        renderTrashModal();
        updateTrashCount();
      } catch (err) {
        alert("恢复失败: " + err);
      }
    }

    function setupKeyboard() {
      window.addEventListener("keydown", (e) => {
        const tm = document.getElementById("trash-modal");
        if (tm && tm.classList.contains("active")) {
          if (e.key === "Escape") {
            closeTrashModal();
            return;
          }
        }
        const lb = document.getElementById("lightbox");
        if (lb.classList.contains("active")) {
          if (e.key === "Escape") {
            closeLightbox();
          } else if (e.key === "ArrowLeft") {
            prevLightboxImage();
          } else if (e.key === "ArrowRight") {
            nextLightboxImage();
          } else if (e.key === "Delete" || e.key === "Backspace") {
            e.preventDefault();
            deleteCurrentLightboxImage();
          }
        } else {
          // 主网格下：按 Delete 键一键删除当前勾选的所有图片
          if ((e.key === "Delete" || e.key === "Backspace") && g_selectedFiles.size > 0) {
            // 避免在搜索框内打字时误删
            if (document.activeElement && document.activeElement.tagName === "INPUT") {
              return;
            }
            e.preventDefault();
            deleteSelected();
          }
        }
      });
    }
