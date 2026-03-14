async function loadRegistry() {
  const meta = document.getElementById("registry-meta");
  const list = document.getElementById("capability-list");

  try {
    const response = await fetch("../../registry/generated/index.json", { cache: "no-store" });
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const payload = await response.json();
    meta.textContent = `Capabilities: ${payload.capability_count} | MCPs: ${payload.mcp_count}`;

    if (!payload.capabilities || payload.capabilities.length === 0) {
      list.innerHTML = `<article class="card"><h3>暂无 capability</h3><p>请先新增 manifest 并运行 build_registry.py。</p></article>`;
      return;
    }

    list.innerHTML = payload.capabilities.map(renderCard).join("");
  } catch (error) {
    meta.textContent = "加载失败";
    list.innerHTML = `<article class="card"><h3>无法读取 registry</h3><p>${escapeHtml(String(error))}</p></article>`;
  }
}

function renderCard(item) {
  const chips = (item.platforms || []).map(platform => `<span class="chip">${escapeHtml(platform)}</span>`).join("");
  const tags = (item.tags || []).slice(0, 4).map(tag => `<span class="chip">${escapeHtml(tag)}</span>`).join("");
  const meta = [
    `类型：${escapeHtml(item.kind || "-")}`,
    `来源：${escapeHtml(item.source_type || "-")}`,
    `状态：${escapeHtml(item.status || "-")}`,
    `版本：${escapeHtml(item.version || "-")}`
  ].join("<br/>");

  return `
    <article class="card">
      <h3>${escapeHtml(item.name || item.id || "Unnamed")}</h3>
      <p>${escapeHtml(item.description || "")}</p>
      <div class="chips">${chips}${tags}</div>
      <div class="meta">${meta}</div>
    </article>
  `;
}

function escapeHtml(value) {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll("\"", "&quot;")
    .replaceAll("'", "&#39;");
}

loadRegistry();
