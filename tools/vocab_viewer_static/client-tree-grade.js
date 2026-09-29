    function renderTreeByGrade(stages, filterText = "") {
      const root = document.getElementById("tree-root");
      root.innerHTML = "";
      filterText = filterText.trim().toLowerCase();

      stages.forEach((st) => {
        let hasMatchedStage = false;
        const stageDiv = document.createElement("div");
        stageDiv.className = "tree-group";

        const stHeader = document.createElement("div");
        stHeader.className = "stage-header";
        stHeader.innerHTML = `<span class="arrow">▼</span><span class="node-title">${st.name}</span><span class="node-badge">${st.img_count}张</span>`;

        const stBody = document.createElement("div");
        stBody.className = "stage-body";

        if (st.is_high_school) {
          st.editions.forEach((ed) => {
            let hasMatchedTerm = false;
            const edDiv = document.createElement("div");
            edDiv.className = "edition-group";

            const edHeader = document.createElement("div");
            edHeader.className = "edition-header";
            edHeader.innerHTML = `<span class="arrow">▼</span><span class="node-title">${ed.name}</span><span class="node-badge">${ed.img_count}张</span>`;

            const edBody = document.createElement("div");
            edBody.className = "edition-body";

            ed.terms.forEach(tm => {
              const fullTitle = `${st.name} ${ed.name} ${tm.name}`.toLowerCase();
              if (filterText && !fullTitle.includes(filterText)) return;
              hasMatchedTerm = true;
              hasMatchedStage = true;

              const termItem = document.createElement("div");
              termItem.className = `term-item ${g_currentRelPath === tm.rel_path ? "active" : ""}`;
              termItem.innerHTML = `<span class="node-title">${tm.name}</span><span class="node-badge">${tm.count}</span>`;
              termItem.onclick = () => selectBook(tm.rel_path, `${st.name} > ${ed.name} > ${tm.name}`, termItem);
              edBody.appendChild(termItem);
            });

            if (hasMatchedTerm || !filterText) {
              edHeader.onclick = () => toggleCollapse(edHeader, edBody);
              edDiv.appendChild(edHeader);
              edDiv.appendChild(edBody);
              stBody.appendChild(edDiv);
            }
          });
        } else {
          st.grades.forEach((gr) => {
            let hasMatchedGrade = false;
            const grDiv = document.createElement("div");
            grDiv.className = "grade-group";

            const grHeader = document.createElement("div");
            grHeader.className = "stage-header";
            grHeader.style.background = "rgba(56, 189, 248, 0.08)";
            grHeader.style.color = "#38bdf8";
            grHeader.style.paddingLeft = "20px";
            grHeader.innerHTML = `<span class="arrow">▼</span><span class="node-title">${gr.name}</span><span class="node-badge">${gr.editions.length}个版本 · ${gr.count}张</span>`;

            const grBody = document.createElement("div");
            grBody.className = "grade-body";

            gr.editions.forEach((ed) => {
              let hasMatchedEdition = false;
              const edDiv = document.createElement("div");
              edDiv.className = "edition-group";

              const edHeader = document.createElement("div");
              edHeader.className = "edition-header";
              edHeader.style.paddingLeft = "32px";
              edHeader.innerHTML = `<span class="arrow">▼</span><span class="node-title">${ed.name}</span><span class="node-badge">${ed.count}张</span>`;

              const edBody = document.createElement("div");
              edBody.className = "edition-body";

              ed.terms.forEach(tm => {
                const fullTitle = `${st.name} ${gr.name} ${ed.name} ${tm.name}`.toLowerCase();
                if (filterText && !fullTitle.includes(filterText)) return;
                hasMatchedEdition = true;
                hasMatchedGrade = true;
                hasMatchedStage = true;

                const termItem = document.createElement("div");
                termItem.className = `term-item ${g_currentRelPath === tm.rel_path ? "active" : ""}`;
                termItem.style.paddingLeft = "44px";
                termItem.innerHTML = `<span class="node-title">${tm.name}</span><span class="node-badge">${tm.count}</span>`;
                termItem.onclick = () => selectBook(tm.rel_path, `${st.name} > ${gr.name} > ${ed.name} > ${tm.name}`, termItem);
                edBody.appendChild(termItem);
              });

              if (hasMatchedEdition || !filterText) {
                edHeader.onclick = () => toggleCollapse(edHeader, edBody);
                edDiv.appendChild(edHeader);
                edDiv.appendChild(edBody);
                grBody.appendChild(edDiv);
              }
            });

            if (hasMatchedGrade || !filterText) {
              grHeader.onclick = () => toggleCollapse(grHeader, grBody);
              grDiv.appendChild(grHeader);
              grDiv.appendChild(grBody);
              stBody.appendChild(grDiv);
            }
          });
        }

        if (hasMatchedStage || !filterText) {
          stHeader.onclick = () => toggleCollapse(stHeader, stBody);
          stageDiv.appendChild(stHeader);
          stageDiv.appendChild(stBody);
          root.appendChild(stageDiv);
        }
      });
    }

    // 模式 2：按版本分类（学段 -> 版本 -> 年级 -> 册次）
