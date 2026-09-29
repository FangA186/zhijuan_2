    function applyVocabBadgesToCards() {
      if (!g_vocabDetectData || !g_vocabDetectData.pages) return;

      const pageMap = {};
      g_vocabDetectData.pages.forEach(p => {
        pageMap[p.rel_file_path] = p;
      });

      g_currentImages.forEach((img, idx) => {
        const card = document.getElementById(`card-${idx}`);
        if (!card) return;

        const p = pageMap[img.rel_file_path];
        if (!p) return;

        const oldBadge = card.querySelector(".smart-badge");
        if (oldBadge) oldBadge.remove();

        card.classList.remove("card-vocab-start", "card-vocab-page", "card-non-vocab-page");

        const badge = document.createElement("div");
        badge.className = "smart-badge";

        if (p.is_start) {
          badge.classList.add("badge-start");
          badge.innerHTML = `⭐ 单词表首页`;
          card.classList.add("card-vocab-start");
        } else if (p.is_vocab) {
          badge.classList.add("badge-vocab");
          badge.innerHTML = `📖 单词表`;
          card.classList.add("card-vocab-page");
        } else {
          badge.classList.add("badge-non-vocab");
          badge.innerHTML = p.label || `📄 非词汇`;
          card.classList.add("card-non-vocab-page");
        }

        const pageBadge = card.querySelector(".page-badge");
        if (pageBadge) {
          card.insertBefore(badge, pageBadge);
        } else {
          card.appendChild(badge);
        }
      });
    }

    function smartSelectNonVocab() {
      if (!g_vocabDetectData || !g_vocabDetectData.detected) {
        showToast("当前册次未检测到单词表范围，请手动勾选", "warning");
        return;
      }
      const nonVocab = g_vocabDetectData.non_vocab_files || [];
      if (nonVocab.length === 0) {
        showToast("当前册次已全为单词表页面，无需清理！", "success");
        return;
      }

      g_selectedFiles.clear();
      nonVocab.forEach(f => g_selectedFiles.add(f));
      updateAllCardsDOM();
      updateSelectedCount();
      showToast(`已智能勾选 ${nonVocab.length} 张非单词页，可按 Delete 键直接删除！`, "success");
    }

    function jumpToVocabStart() {
      if (!g_vocabDetectData || g_vocabDetectData.start_idx === null) return;
      const targetCard = document.getElementById(`card-${g_vocabDetectData.start_idx}`);
      if (targetCard) {
        targetCard.scrollIntoView({ behavior: "smooth", block: "center" });
        targetCard.classList.add("flash-highlight");
        setTimeout(() => targetCard.classList.remove("flash-highlight"), 1800);
        showToast(`已平滑定位至单词表首页 (第 ${g_vocabDetectData.start_page} 页)`);
      }
    }

    function handleCardClick(idx, event) {
      // 避免点击放大或单张删除时重复触发
      if (event.target.closest(".card-actions")) {
        return;
      }

      // 如果未开启删除模式，且用户点击的是图片主体，则放大
      if (!g_deleteMode) {
        openLightbox(idx);
        return;
      }

      const img = g_currentImages[idx];
      if (!img) return;

      // 支持 Shift 键连续范围多选！
      if (event.shiftKey && g_lastClickedIdx !== -1 && g_lastClickedIdx !== idx) {
        const start = Math.min(g_lastClickedIdx, idx);
        const end = Math.max(g_lastClickedIdx, idx);
        const shouldSelect = !g_selectedFiles.has(img.rel_file_path);
        for (let i = start; i <= end; i++) {
          const targetItem = g_currentImages[i];
          if (targetItem) {
            if (shouldSelect) {
              g_selectedFiles.add(targetItem.rel_file_path);
            } else {
              g_selectedFiles.delete(targetItem.rel_file_path);
            }
          }
        }
      } else {
        // 单击切换当前项
        if (g_selectedFiles.has(img.rel_file_path)) {
          g_selectedFiles.delete(img.rel_file_path);
        } else {
          g_selectedFiles.add(img.rel_file_path);
        }
        g_lastClickedIdx = idx;
      }

      updateAllCardsDOM();
      updateSelectedCount();
    }

    function toggleSelectImage(relFilePath, idx, isChecked) {
      if (isChecked) {
        g_selectedFiles.add(relFilePath);
      } else {
        g_selectedFiles.delete(relFilePath);
      }
      g_lastClickedIdx = idx;
      updateAllCardsDOM();
      updateSelectedCount();
    }

    function updateAllCardsDOM() {
      g_currentImages.forEach((img, idx) => {
        const card = document.getElementById(`card-${idx}`);
        if (!card) return;
        const isSel = g_selectedFiles.has(img.rel_file_path);
        if (isSel) {
          card.classList.add("selected");
        } else {
          card.classList.remove("selected");
        }
        const cb = card.querySelector(".card-checkbox");
        if (cb) cb.checked = isSel;
      });
    }

    function selectFirstN(n) {
      g_selectedFiles.clear();
      g_currentImages.slice(0, n).forEach((img) => {
        g_selectedFiles.add(img.rel_file_path);
      });
      updateAllCardsDOM();
      updateSelectedCount();
      showToast(`已直接勾选前 ${Math.min(n, g_currentImages.length)} 张非单词正文页`);
    }

    function toggleSelectAll() {
      if (g_selectedFiles.size === g_currentImages.length) {
        g_selectedFiles.clear();
      } else {
        g_selectedFiles.clear();
        g_currentImages.forEach(img => g_selectedFiles.add(img.rel_file_path));
      }
      updateAllCardsDOM();
      updateSelectedCount();
    }

    function clearSelection() {
      g_selectedFiles.clear();
      updateAllCardsDOM();
      updateSelectedCount();
    }

    function updateSelectedCount() {
      const count = g_selectedFiles.size;
      document.getElementById("selected-count").innerText = count;
      document.getElementById("btn-batch-del").disabled = (count === 0);

      const floatBar = document.getElementById("bottom-floating-bar");
      const floatCount = document.getElementById("float-selected-count");
      if (count > 0) {
        floatBar.classList.add("active");
        floatCount.innerText = count;
      } else {
        floatBar.classList.remove("active");
      }
    }

