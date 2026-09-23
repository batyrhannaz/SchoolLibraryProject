// static/js/admin_panel.js
document.addEventListener("DOMContentLoaded", () => {
  requireAuth();

  const user = getCurrentUser();
  const isLibrarian = user && (user.role === "librarian" || user.role === "admin");

  if (!isLibrarian) {
    alert("Доступ только для библиотекаря и администратора.");
    window.location.href = "/";
    return;
  }

  const tabBtns = document.querySelectorAll(".tab-btn");
  const tabs = document.querySelectorAll(".admin-tab");

  tabBtns.forEach((btn) => {
    btn.addEventListener("click", () => {
      tabBtns.forEach((b) => b.classList.remove("active"));
      tabs.forEach((t) => (t.style.display = "none"));

      btn.classList.add("active");
      document.getElementById(btn.dataset.tab).style.display = "block";

      if (btn.dataset.tab === "log-tab") {
        loadAuditLog();
      }
    });
  });

  loadStats();
});

async function loadStats() {
  const grid = document.getElementById("stats-grid");
  const res = await apiFetch("/circulation/dashboard/");

  if (!res.ok) {
    grid.innerHTML = "<p>Не удалось загрузить статистику.</p>";
    return;
  }

  const data = await res.json();

  const topBooksHtml = data.top_books
    .map((b) => `<li>${escapeHtml(b.title)} — ${b.loan_count} выдач</li>`)
    .join("");

  grid.innerHTML = `
    <div class="stat-card">
      <div class="stat-value">${data.total_books}</div>
      <div class="stat-label">Всего книг</div>
    </div>
    <div class="stat-card">
      <div class="stat-value">${data.books_available}</div>
      <div class="stat-label">Доступно сейчас</div>
    </div>
    <div class="stat-card">
      <div class="stat-value">${data.active_loans}</div>
      <div class="stat-label">На руках</div>
    </div>
    <div class="stat-card">
      <div class="stat-value">${data.overdue_loans}</div>
      <div class="stat-label">Просрочено</div>
    </div>
    <div class="stat-card">
      <div class="stat-value">${data.waiting_reservations}</div>
      <div class="stat-label">В очереди</div>
    </div>
    <div class="stat-card stat-card-wide">
      <div class="stat-label">Топ книг по популярности</div>
      <ul>${topBooksHtml || "<li>Нет данных</li>"}</ul>
    </div>
  `;
}

async function loadAuditLog() {
  const tbody = document.getElementById("log-tbody");
  tbody.innerHTML = `<tr><td colspan="4">Загрузка...</td></tr>`;

  const res = await apiFetch("/auth/audit-log/");
  if (!res.ok) {
    tbody.innerHTML = `<tr><td colspan="4">Не удалось загрузить журнал.</td></tr>`;
    return;
  }

  const data = await res.json();
  const items = data.results || data;

  if (items.length === 0) {
    tbody.innerHTML = `<tr><td colspan="4">Записей пока нет.</td></tr>`;
    return;
  }

  tbody.innerHTML = items
    .map(
      (item) => `
        <tr>
          <td>${new Date(item.created_at).toLocaleString("ru-RU")}</td>
          <td>${escapeHtml(item.actor_name || "система")}</td>
          <td>${escapeHtml(item.action_display)}</td>
          <td>${escapeHtml(item.target_repr)}</td>
        </tr>
      `
    )
    .join("");
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str ?? "";
  return div.innerHTML;
}