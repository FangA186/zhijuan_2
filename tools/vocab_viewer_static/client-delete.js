    async function deleteOneImage(relFilePath, idx) {
      if (!confirm(`确定要从本地删除此张图片吗？
${relFilePath}`)) return;
      await performDelete([relFilePath]);
    }

    async function deleteSelected() {
      if (g_selectedFiles.size === 0) return;
      const count = g_selectedFiles.size;
      if (!confirm(`确定要从本地删除已勾选的 ${count} 张图片吗？`)) return;
      await performDelete(Array.from(g_selectedFiles));
    }

    async function performDelete(files) {
      const useTrash = document.getElementById("use-trash-cb").checked;
      try {
        const res = await fetch("/api/delete", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ files, trash: useTrash })
        });
        const result = await res.json();
        if (result.success) {
          showToast(`成功删除 ${result.deleted.length} 张本地图片！`);
          // 重新拉取当前目录
          const imgRes = await fetch(`/api/images?path=${encodeURIComponent(g_currentRelPath)}`);
          g_currentImages = await imgRes.json();
          g_selectedFiles.clear();
          g_lastClickedIdx = -1;
          g_vocabDetectData = null;
          updateSelectedCount();
          renderImages();
          loadVocabDetection(g_currentRelPath, true);
          loadTree();
          updateTrashCount();
        } else {
          alert(`部分文件删除失败: ` + JSON.stringify(result.failed));
        }
      } catch (err) {
        alert("删除请求出错: " + err);
      }
    }

    // 全屏画廊 Lightbox
