// static/js/loans.js
let currentStatusFilter = "";

document.addEventListener("DOMContentLoaded", () => {
  requireAuth();

  const user = getCurrentUser();
  const isLibrarian = user && (user.role === "librarian" || user.role === "admin");

  if (isLibrarian) {
    document.getElementById("loans-title").textContent = "Все выдачи";
    document.getElementById("librarian-filters").style.display = "flex";
    document.getElementById("col-user").style.display = "table-cell";
  }

  loadLoans();

  if (isLibrarian) {
    document.getElementById("status-filter").addEventListener("change", (e) => {
      currentStatusFilter = e.target.value;
      loadLoans();
    });

    const modal = document.getElementById("issue-modal");
    document.getElementById("issue-book-btn").addEventListener("click", () => {
      document.getElementById("issue-form").reset();
      document.getElementById("issue-form-error").textContent = "";
      modal.style.display = "flex";
    });
    document.getElementById("issue-modal-cancel").addEventListener("click", () => {
      modal.style.display = "none";
    });
    document.getElementById("issue-form").addEventListener("submit", handleIssueSubmit);
  }
});

async function loadLoans() {
  const params = new URLSearchParams();
  if (currentStatusFilter) params.set("status", currentStatusFilter);

  const res = await apiFetch(`/circulation/loans/?${params.toString()}`);
  const tbody = document.getElementById("loans-tbody");

  if (!res.ok) {
    tbody.innerHTML = `<tr><td colspan="6">Не удалось загрузить выдачи.</td></tr>`;
    return;
  }

  const data = await res.json();
  const loans = data.results || data;

  if (loans.length === 0) {
    tbody.innerHTML = `<tr><td colspan="6">Пока ничего нет.</td></tr>`;
    return;
  }

  const user = getCurrentUser();
  const isLibrarian = user && (user.role === "librarian" || user.role === "admin");

  tbody.innerHTML = loans.map((loan) => renderLoanRow(loan, isLibrarian)).join("");

  if (isLibrarian) {
    document.querySelectorAll("[data-return-id]").forEach((btn) => {
      btn.addEventListener("click", () => returnLoan(btn.dataset.returnId));
    });
    document.querySelectorAll("[data-payfine-id]").forEach((btn) => {
      btn.addEventListener("click", () => payFine(btn.dataset.payfineId));
    });
  }

  document.querySelectorAll("[data-extend-id]").forEach((btn) => {
    btn.addEventListener("click", () => extendLoan(btn.dataset.extendId));
  });
}

function renderLoanRow(loan, isLibrarian) {
  const statusMap = {
    active: { text: "На руках", cls: "status-active" },
    returned: { text: "Возвращена", cls: "status-returned" },
    overdue: { text: "Просрочена", cls: "status-overdue" },
  };
  const status = statusMap[loan.is_overdue && loan.status === "active" ? "overdue" : loan.status]
    || statusMap.active;

  const fineHtml = loan.current_fine > 0
    ? `<span class="fine-pill">Штраф: ${loan.current_fine}${loan.fine_paid ? " (оплачен)" : ""}</span>`
    : "";

  const actions = [];
  if (isLibrarian && loan.status !== "returned") {
    actions.push(`<button class="btn btn-outline btn-small" data-return-id="${loan.id}">Принять возврат</button>`);
  }
  if (isLibrarian && loan.fine_amount > 0 && !loan.fine_paid) {
    actions.push(`<button class="btn btn-outline btn-small" data-payfine-id="${loan.id}">Штраф оплачен</button>`);
  }
  if (loan.status === "active" && !loan.is_overdue && loan.extensions_used < 1) {
    actions.push(`<button class="btn btn-outline btn-small" data-extend-id="${loan.id}">Продлить</button>`);
  }

  return `
    <tr>
      <td>${escapeHtml(loan.book_title)}</td>
      ${isLibrarian ? `<td>${escapeHtml(loan.user_name)}</td>` : ""}
      <td>${loan.issue_date}</td>
      <td>${loan.due_date}</td>
      <td><span class="status-pill ${status.cls}">${status.text}</span> ${fineHtml}</td>
      <td>${actions.join(" ") || "—"}</td>
    </tr>
  `;
}

async function returnLoan(loanId) {
  const res = await apiFetch(`/circulation/loans/${loanId}/return/`, { method: "POST" });
  if (res.ok) {
    loadLoans();
  } else {
    alert("Не удалось оформить возврат");
  }
}

async function extendLoan(loanId) {
  const res = await apiFetch(`/circulation/loans/${loanId}/extend/`, { method: "POST" });
  if (res.ok) {
    loadLoans();
  } else {
    const data = await res.json().catch(() => ({}));
    alert(data.detail || "Не удалось продлить срок");
  }
}

async function payFine(loanId) {
  const res = await apiFetch(`/circulation/loans/${loanId}/pay-fine/`, { method: "POST" });
  if (res.ok) {
    loadLoans();
  } else {
    alert("Не удалось отметить штраф оплаченным");
  }
}

async function handleIssueSubmit(e) {
  e.preventDefault();
  const errorEl = document.getElementById("issue-form-error");
  errorEl.textContent = "";

  const formData = new FormData(e.target);
  const bookId = formData.get("book");
  const username = formData.get("user_username").trim();

  if (!username) {
    errorEl.textContent = "Введите username читателя";
    return;
  }

  try {
    const searchRes = await apiFetch(`/auth/users/?search=${encodeURIComponent(username)}`);
    if (!searchRes.ok) {
      errorEl.textContent = "Не удалось найти пользователя";
      return;
    }
    const searchData = await searchRes.json();
    const users = searchData.results || searchData;
    const exactMatch = users.find((u) => u.username === username);

    if (!exactMatch) {
      errorEl.textContent = `Пользователь с username "${username}" не найден`;
      return;
    }

    const payload = {
      book: parseInt(bookId, 10),
      user: exactMatch.id,
    };

    const res = await apiFetch("/circulation/loans/", {
      method: "POST",
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      const firstError = Object.values(data)[0];
      errorEl.textContent = Array.isArray(firstError) ? firstError[0] : "Ошибка выдачи книги";
      return;
    }

    document.getElementById("issue-modal").style.display = "none";
    loadLoans();
  } catch (err) {
    errorEl.textContent = "Не удалось выдать книгу";
  }
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str ?? "";
  return div.innerHTML;
}