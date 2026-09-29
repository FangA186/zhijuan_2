    function renderTreeByEdition(stages, filterText = "") {
      const root = document.getElementById("tree-root");
      root.innerHTML = "";
      filterText = filterText.trim().toLowerCase();

      stages.forEach((st) => {
        let hasMatchedEdition = false;
        const stageDiv = document.createElement("div");
        stageDiv.className = "tree-group";

        const stHeader = document.createElement("div");
        stHeader.className = "stage-header";
        stHeader.innerHTML = `<span class="arrow">▼</span><span class="node-title">${st.name}</span><span class="node-badge">${st.img_count}张</span>`;

        const stBody = document.createElement("div");
        stBody.className = "stage-body";

        st.editions.forEach((ed) => {
          let hasMatchedTerm = false;
          const edDiv = document.createElement("div");
          edDiv.className = "edition-group";

          const edHeader = document.createElement("div");
          edHeader.className = "edition-header";
          edHeader.innerHTML = `<span class="arrow">▼</span><span class="node-title">${ed.name}</span><span class="node-badge">${ed.img_count}张</span>`;

          const edBody = document.createElement("div");
          edBody.className = "edition-body";

          if (ed.is_high_school) {
            ed.terms.forEach(tm => {
              const fullTitle = `${st.name} ${ed.name} ${tm.name}`.toLowerCase();
              if (filterText && !fullTitle.includes(filterText)) return;
              hasMatchedTerm = true;
              hasMatchedEdition = true;

              const termItem = document.createElement("div");
              termItem.className = `term-item ${g_currentRelPath === tm.rel_path ? "active" : ""}`;
              termItem.innerHTML = `<span class="node-title">${tm.name}</span><span class="node-badge">${tm.count}</span>`;
              termItem.onclick = () => selectBook(tm.rel_path, `${st.name} > ${ed.name} > ${tm.name}`, termItem);
              edBody.appendChild(termItem);
            });
          } else {
            ed.grades.forEach(gr => {
              let hasMatchedGrade = false;
              const grDiv = document.createElement("div");
              grDiv.className = "grade-group";

              const grHeader = document.createElement("div");
              grHeader.className = "grade-header";
              grHeader.innerHTML = `<span class="arrow">▼</span><span class="node-title">${gr.name}</span><span class="node-badge">${gr.count}</span>`;

              const grBody = document.createElement("div");
              grBody.className = "grade-body";

              gr.terms.forEach(tm => {
                const fullTitle = `${st.name} ${ed.name} ${gr.name} ${tm.name}`.toLowerCase();
                if (filterText && !fullTitle.includes(filterText)) return;
                hasMatchedGrade = true;
                hasMatchedTerm = true;
                hasMatchedEdition = true;

                const termItem = document.createElement("div");
                termItem.className = `term-item ${g_currentRelPath === tm.rel_path ? "active" : ""}`;
                termItem.innerHTML = `<span class="node-title">${tm.name}</span><span class="node-badge">${tm.count}</span>`;
                termItem.onclick = () => selectBook(tm.rel_path, `${st.name} > ${ed.name} > ${gr.name} > ${tm.name}`, termItem);
                grBody.appendChild(termItem);
              });

              if (hasMatchedGrade || !filterText) {
                grHeader.onclick = () => toggleCollapse(grHeader, grBody);
                grDiv.appendChild(grHeader);
                grDiv.appendChild(grBody);
                edBody.appendChild(grDiv);
              }
            });
          }

          if (hasMatchedTerm || !filterText) {
            edHeader.onclick = () => toggleCollapse(edHeader, edBody);
            edDiv.appendChild(edHeader);
            edDiv.appendChild(edBody);
            stBody.appendChild(edDiv);
          }
        });

        if (hasMatchedEdition || !filterText) {
          stHeader.onclick = () => toggleCollapse(stHeader, stBody);
          stageDiv.appendChild(stHeader);
          stageDiv.appendChild(stBody);
          root.appendChild(stageDiv);
        }
      });
    }

    function toggleCollapse(header, body) {
      const arrow = header.querySelector(".arrow");
      if (body.style.display === "none") {
        body.style.display = "block";
        arrow.classList.remove("collapsed");
      } else {
        body.style.display = "none";
        arrow.classList.add("collapsed");
      }
    }

    function setupSearch() {
      const input = document.getElementById("search-input");
      input.addEventListener("input", (e) => {
        if (g_treeData) {
          renderTree(e.target.value);
        }
      });
    }

