// static/js/catalog.js
let currentPage = 1;
let currentSearch = "";
let currentCategory = "";
let currentAvailability = "";

document.addEventListener("DOMContentLoaded", () => {
  requireAuth();

  const user = getCurrentUser();
  const isLibrarian = user && (user.role === "librarian" || user.role === "admin");

  if (isLibrarian) {
    document.getElementById("add-book-btn").style.display = "inline-block";
  }

  loadCategories();
  loadBooks();

  let searchTimeout;
  document.getElementById("search-input").addEventListener("input", (e) => {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => {
      currentSearch = e.target.value.trim();
      currentPage = 1;
      loadBooks();
    }, 400);
  });

  document.getElementById("category-filter").addEventListener("change", (e) => {
    currentCategory = e.target.value;
    currentPage = 1;
    loadBooks();
  });

  document.getElementById("availability-filter").addEventListener("change", (e) => {
    currentAvailability = e.target.value;
    currentPage = 1;
    loadBooks();
  });

  const modal = document.getElementById("book-modal");
  const form = document.getElementById("book-form");

  document.getElementById("add-book-btn").addEventListener("click", () => {
    form.reset();
    form.id.value = "";
    document.getElementById("book-modal-title").textContent = "Добавить книгу";
    document.getElementById("book-form-error").textContent = "";
    modal.style.display = "flex";
  });

  document.getElementById("book-modal-cancel").addEventListener("click", () => {
    modal.style.display = "none";
  });

  form.addEventListener("submit", handleBookFormSubmit);
});

async function loadCategories() {
  const res = await apiFetch("/catalog/categories/");
  if (!res.ok) return;
  const data = await res.json();
  const select = document.getElementById("category-filter");
  const items = data.results || data;
  items.forEach((cat) => {
    const opt = document.createElement("option");
    opt.value = cat.id;
    opt.textContent = cat.name;
    select.appendChild(opt);
  });
}

async function loadBooks() {
  const params = new URLSearchParams();
  if (currentSearch) params.set("search", currentSearch);
  if (currentCategory) params.set("category", currentCategory);
  if (currentAvailability) params.set("available", currentAvailability);
  params.set("page", currentPage);

  const res = await apiFetch(`/catalog/books/?${params.toString()}`);
  const listEl = document.getElementById("book-list");

  if (!res.ok) {
    listEl.innerHTML = "<p>Не удалось загрузить книги.</p>";
    return;
  }

  const data = await res.json();
  const books = data.results || data;

  if (books.length === 0) {
    listEl.innerHTML = "<p>Ничего не найдено.</p>";
    document.getElementById("pagination").innerHTML = "";
    return;
  }

  const user = getCurrentUser();
  const isLibrarian = user && (user.role === "librarian" || user.role === "admin");

  listEl.innerHTML = books.map((book) => renderBookCard(book, isLibrarian)).join("");

  if (isLibrarian) {
    document.querySelectorAll("[data-edit-id]").forEach((btn) => {
      btn.addEventListener("click", () => openEditModal(btn.dataset.editId, books));
    });
    document.querySelectorAll("[data-delete-id]").forEach((btn) => {
      btn.addEventListener("click", () => deleteBook(btn.dataset.deleteId));
    });
  }

  document.querySelectorAll("[data-reserve-id]").forEach((btn) => {
    btn.addEventListener("click", () => reserveBook(btn.dataset.reserveId));
  });

  renderPagination(data.count || books.length);
}

function renderBookCard(book, isLibrarian) {
  const badgeClass = book.is_available ? "available" : "unavailable";
  const badgeText = book.is_available
    ? `Доступно: ${book.available_copies}`
    : "Нет в наличии";

  const reserveBtn = !book.is_available
    ? `<button class="btn btn-outline btn-small" data-reserve-id="${book.id}">Забронировать</button>`
    : "";

  return `
    <div class="book-card">
      <h3>${escapeHtml(book.title)}</h3>
      <div class="meta">Автор: ${escapeHtml(book.author_name || "—")}</div>
      <div class="meta">Категория: ${escapeHtml(book.category_name || "—")}</div>
      <div class="meta">Год: ${book.year}</div>
      <span class="badge ${badgeClass}">${badgeText}</span>
      ${reserveBtn}
      ${isLibrarian ? `
        <div class="card-actions">
          <button class="btn btn-outline btn-small" data-edit-id="${book.id}">Редактировать</button>
          <button class="btn btn-danger btn-small" data-delete-id="${book.id}">Удалить</button>
        </div>
      ` : ""}
    </div>
  `;
}

function renderPagination(count) {
  const pageSize = 20;
  const totalPages = Math.max(1, Math.ceil(count / pageSize));
  const pagEl = document.getElementById("pagination");

  if (totalPages <= 1) {
    pagEl.innerHTML = "";
    return;
  }

  let html = "";
  for (let i = 1; i <= totalPages; i++) {
    html += `<button class="${i === currentPage ? "active" : ""}" data-page="${i}">${i}</button>`;
  }
  pagEl.innerHTML = html;

  pagEl.querySelectorAll("button").forEach((btn) => {
    btn.addEventListener("click", () => {
      currentPage = parseInt(btn.dataset.page, 10);
      loadBooks();
    });
  });
}

function openEditModal(bookId, books) {
  const book = books.find((b) => String(b.id) === String(bookId));
  if (!book) return;

  const form = document.getElementById("book-form");
  form.id.value = book.id;
  form.title.value = book.title;
  form.author_name.value = book.author_name || "";
  form.category_name.value = book.category_name || "";
  form.year.value = book.year;
  form.isbn.value = book.isbn || "";
  form.description.value = book.description || "";
  form.total_copies.value = book.total_copies;

  document.getElementById("book-modal-title").textContent = "Редактировать книгу";
  document.getElementById("book-form-error").textContent = "";
  document.getElementById("book-modal").style.display = "flex";
}

async function handleBookFormSubmit(e) {
  e.preventDefault();
  const form = e.target;
  const errorEl = document.getElementById("book-form-error");
  errorEl.textContent = "";

  const formData = new FormData(form);
  const bookId = formData.get("id");

  try {
    const authorId = await resolveAuthorId(formData.get("author_name").trim());
    let categoryId = null;
    const categoryName = formData.get("category_name").trim();
    if (categoryName) {
      categoryId = await resolveCategoryId(categoryName);
    }

    const payload = {
      title: formData.get("title"),
      author: authorId,
      category: categoryId,
      year: parseInt(formData.get("year"), 10),
      isbn: formData.get("isbn"),
      description: formData.get("description"),
      total_copies: parseInt(formData.get("total_copies"), 10),
    };

    const url = bookId ? `/catalog/books/${bookId}/` : "/catalog/books/";
    const method = bookId ? "PATCH" : "POST";

    const res = await apiFetch(url, {
      method,
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      const firstError = Object.values(data)[0];
      errorEl.textContent = Array.isArray(firstError) ? firstError[0] : "Ошибка сохранения книги";
      return;
    }

    document.getElementById("book-modal").style.display = "none";
    loadBooks();
    loadCategories();
  } catch (err) {
    errorEl.textContent = "Не удалось сохранить книгу";
  }
}

async function deleteBook(bookId) {
  if (!confirm("Удалить эту книгу?")) return;
  const res = await apiFetch(`/catalog/books/${bookId}/`, { method: "DELETE" });
  if (res.ok) {
    loadBooks();
  } else {
    alert("Не удалось удалить книгу");
  }
}

async function reserveBook(bookId) {
  const user = getCurrentUser();
  const res = await apiFetch("/circulation/reservations/", {
    method: "POST",
    body: JSON.stringify({ book: parseInt(bookId, 10), user: user.id }),
  });

  if (res.ok) {
    alert("Вы встали в очередь на книгу! Следите за статусом в профиле.");
  } else {
    const data = await res.json().catch(() => ({}));
    const firstError = Object.values(data)[0];
    alert(Array.isArray(firstError) ? firstError[0] : "Не удалось забронировать книгу");
  }
}

async function resolveAuthorId(name) {
  let res = await apiFetch(`/catalog/authors/?search=${encodeURIComponent(name)}`);
  let data = await res.json();
  const found = (data.results || data).find((a) => a.full_name === name);
  if (found) return found.id;

  res = await apiFetch("/catalog/authors/", {
    method: "POST",
    body: JSON.stringify({ full_name: name }),
  });
  data = await res.json();
  return data.id;
}

async function resolveCategoryId(name) {
  let res = await apiFetch(`/catalog/categories/?search=${encodeURIComponent(name)}`);
  let data = await res.json();
  const found = (data.results || data).find((c) => c.name === name);
  if (found) return found.id;

  res = await apiFetch("/catalog/categories/", {
    method: "POST",
    body: JSON.stringify({ name }),
  });
  data = await res.json();
  return data.id;
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str ?? "";
  return div.innerHTML;
}