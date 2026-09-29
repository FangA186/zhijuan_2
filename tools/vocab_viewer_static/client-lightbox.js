    function openLightbox(idx) {
      if (idx < 0 || idx >= g_currentImages.length) return;
      g_lightboxIdx = idx;
      updateLightboxContent();
      document.getElementById("lightbox").classList.add("active");
    }

    function closeLightbox() {
      document.getElementById("lightbox").classList.remove("active");
    }

    function updateLightboxContent() {
      const img = g_currentImages[g_lightboxIdx];
      if (!img) return;
      document.getElementById("lb-title").innerText = `${img.filename}  (#${g_lightboxIdx + 1} / ${g_currentImages.length})`;
      document.getElementById("lb-img").src = `/image/${encodeURI(img.rel_file_path)}`;
      document.getElementById("lb-meta").innerText = `书本真实页码: 第 ${img.page_num || "-"} 页 | 文件大小: ${img.size_kb} KB | 路径: ${img.rel_file_path}`;
    }

    function prevLightboxImage() {
      if (g_lightboxIdx > 0) {
        g_lightboxIdx--;
        updateLightboxContent();
      }
    }

    function nextLightboxImage() {
      if (g_lightboxIdx < g_currentImages.length - 1) {
        g_lightboxIdx++;
        updateLightboxContent();
      }
    }

    async function deleteCurrentLightboxImage() {
      const img = g_currentImages[g_lightboxIdx];
      if (!img) return;
      const useTrash = document.getElementById("use-trash-cb").checked;
      try {
        const res = await fetch("/api/delete", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ files: [img.rel_file_path], trash: useTrash })
        });
        const result = await res.json();
        if (result.success) {
          showToast(`已删除: ${img.filename}`);
          g_currentImages.splice(g_lightboxIdx, 1);
          if (g_currentImages.length === 0) {
            closeLightbox();
          } else {
            if (g_lightboxIdx >= g_currentImages.length) {
              g_lightboxIdx = g_currentImages.length - 1;
            }
            updateLightboxContent();
          }
          renderImages();
          loadTree();
        }
      } catch (err) {
        alert("删除失败: " + err);
      }
    }

