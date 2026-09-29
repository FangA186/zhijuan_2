    let g_treeData = null;
    let g_currentRelPath = "";
    let g_currentImages = [];
    let g_selectedFiles = new Set();
    let g_lightboxIdx = 0;
    let g_deleteMode = true; // 默认开启删除模式！
    let g_lastClickedIdx = -1; // 支持 Shift 连续多选
    let g_vocabDetectData = null; // 智能单词表识别数据
    let g_trashImages = []; // 当前册次回收站图片
    let g_selectedTrashFiles = new Set(); // 回收站选中的图片

    window.addEventListener("DOMContentLoaded", () => {
      loadTree();
      setupSearch();
      setupKeyboard();
    });

    function showToast(msg, type = "success") {
      const c = document.getElementById("toast-container");
      const t = document.createElement("div");
      t.className = `toast ${type}`;
      t.innerHTML = `<span>${type === "success" ? "✓" : "⚠️"}</span> <span>${msg}</span>`;
      c.appendChild(t);
      setTimeout(() => {
        t.style.opacity = "0";
        t.style.transition = "opacity 0.3s";
        setTimeout(() => t.remove(), 300);
      }, 2500);
    }

    function toggleDeleteMode() {
      g_deleteMode = !g_deleteMode;
      updateDeleteModeUI();
    }

    function updateDeleteModeUI() {
      const btn = document.getElementById("btn-toggle-del-mode");
      if (btn) {
        if (g_deleteMode) {
          btn.className = "btn btn-delete-mode active";
          btn.innerHTML = `<span>🔥 删除模式：已开启</span>`;
        } else {
          btn.className = "btn btn-delete-mode";
          btn.innerHTML = `<span>🗑️ 删除模式：已关闭</span>`;
        }
      }

      const banner = document.getElementById("mode-banner");
      if (banner) {
        if (g_deleteMode) {
          banner.style.background = "rgba(239, 68, 68, 0.16)";
          banner.style.border = "1px solid rgba(239, 68, 68, 0.45)";
          banner.style.color = "#fca5a5";
          banner.innerHTML = `<div>🔥 <b>删除模式已开启</b>：直接点击任意图片即可快速勾选/取消！支持按住 <b>Shift 键连选</b>，选好后点击【批量删除】或按键盘 <b>Delete</b> 键一键删除！</div>
                              <div>当前共 <b>${g_currentImages.length}</b> 张原图</div>`;
        } else {
          banner.style.background = "rgba(59, 130, 246, 0.1)";
          banner.style.border = "1px solid rgba(59, 130, 246, 0.25)";
          banner.style.color = "#93c5fd";
          banner.innerHTML = `<div>💡 普通浏览模式：点击图片可放大查看。点击右上角【删除模式】可恢复直接点击勾选。</div>
                              <div>当前共 <b>${g_currentImages.length}</b> 张原图</div>`;
        }
      }
    }

    let g_currentViewMode = "grade"; // 默认使用“年级视角”（严格对齐官网课程教学）

    function switchViewMode(mode) {
      g_currentViewMode = mode;
      document.getElementById("tab-mode-grade").className = mode === "grade" ? "view-tab-btn active" : "view-tab-btn";
      document.getElementById("tab-mode-edition").className = mode === "edition" ? "view-tab-btn active" : "view-tab-btn";
      const filterText = document.getElementById("search-input").value;
      renderTree(filterText);
    }

    async function loadTree() {
      try {
        const res = await fetch("/api/tree");
        g_treeData = await res.json();
        document.getElementById("stat-books").innerText = g_treeData.total_books;
        document.getElementById("stat-images").innerText = g_treeData.total_images;
        renderTree();
      } catch (err) {
        document.getElementById("tree-root").innerHTML = `<div style="color: #f87171; padding: 20px;">加载层级失败: ${err}</div>`;
      }
    }

    function renderTree(filterText = "") {
      if (!g_treeData) return;
      if (g_currentViewMode === "grade" && g_treeData.by_grade) {
        renderTreeByGrade(g_treeData.by_grade, filterText);
      } else {
        renderTreeByEdition(g_treeData.stages, filterText);
      }
    }

    // 模式 1：按年级分类（与官网课程教学完全一致：学段 -> 年级 -> 版本 -> 册次）
