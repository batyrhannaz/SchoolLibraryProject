// static/js/profile.js
let originalProfileValues = {};
let cameraStream = null;

document.addEventListener("DOMContentLoaded", () => {
  requireAuth();
  loadProfile();
  loadStats();

  document.getElementById("profile-form").addEventListener("submit", handleProfileSubmit);
  document.getElementById("profile-edit-btn").addEventListener("click", enterEditMode);
  document.getElementById("profile-cancel-btn").addEventListener("click", cancelEditMode);

  document.getElementById("avatar-choose-btn").addEventListener("click", () => {
    document.getElementById("avatar-input").click();
  });
  document.getElementById("avatar-input").addEventListener("change", handleAvatarFileChange);
  document.getElementById("avatar-camera-btn").addEventListener("click", openCameraModal);
  document.getElementById("camera-cancel-btn").addEventListener("click", closeCameraModal);
  document.getElementById("camera-shot-btn").addEventListener("click", takeCameraShot);
});

function setFormDisabled(disabled) {
  const form = document.getElementById("profile-form");
  ["first_name", "last_name", "phone", "email", "avatar"].forEach((name) => {
    form[name].disabled = disabled;
  });
  document.getElementById("avatar-choose-btn").disabled = disabled;
  document.getElementById("avatar-camera-btn").disabled = disabled || !cameraIsSupported();
  document.getElementById("profile-form-actions").style.display = disabled ? "none" : "flex";
  document.getElementById("profile-edit-btn").style.display = disabled ? "inline-block" : "none";
}

function cameraIsSupported() {
  return !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia);
}

function enterEditMode() {
  setFormDisabled(false);
}

function cancelEditMode() {
  const form = document.getElementById("profile-form");
  form.first_name.value = originalProfileValues.first_name || "";
  form.last_name.value = originalProfileValues.last_name || "";
  form.phone.value = originalProfileValues.phone || "";
  form.email.value = originalProfileValues.email || "";
  clearAvatarSelection();
  document.getElementById("profile-form-error").textContent = "";
  document.getElementById("profile-form-success").textContent = "";
  setFormDisabled(true);
}

function clearAvatarSelection() {
  const input = document.getElementById("avatar-input");
  input.value = "";
  document.getElementById("avatar-filename").textContent = "Файл не выбран";
  document.getElementById("avatar-file-preview").style.display = "none";
}

function setAvatarFile(file) {
  const input = document.getElementById("avatar-input");
  const dataTransfer = new DataTransfer();
  dataTransfer.items.add(file);
  input.files = dataTransfer.files;

  document.getElementById("avatar-filename").textContent = file.name;
  const preview = document.getElementById("avatar-file-preview");
  preview.src = URL.createObjectURL(file);
  preview.style.display = "block";
}

function handleAvatarFileChange(e) {
  const file = e.target.files && e.target.files[0];
  if (!file) return;
  document.getElementById("avatar-filename").textContent = file.name;
  const preview = document.getElementById("avatar-file-preview");
  preview.src = URL.createObjectURL(file);
  preview.style.display = "block";
}

async function openCameraModal() {
  const modal = document.getElementById("camera-modal");
  const errorEl = document.getElementById("camera-error");
  errorEl.textContent = "";
  modal.style.display = "flex";

  try {
    cameraStream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "user" } });
    document.getElementById("camera-video").srcObject = cameraStream;
  } catch (err) {
    errorEl.textContent = "Не удалось получить доступ к камере. Проверьте разрешения браузера.";
  }
}

function closeCameraModal() {
  if (cameraStream) {
    cameraStream.getTracks().forEach((track) => track.stop());
    cameraStream = null;
  }
  document.getElementById("camera-video").srcObject = null;
  document.getElementById("camera-modal").style.display = "none";
}

function takeCameraShot() {
  const video = document.getElementById("camera-video");
  if (!video.videoWidth) return;

  const canvas = document.getElementById("camera-canvas");
  canvas.width = video.videoWidth;
  canvas.height = video.videoHeight;
  canvas.getContext("2d").drawImage(video, 0, 0, canvas.width, canvas.height);

  canvas.toBlob((blob) => {
    if (!blob) return;
    const file = new File([blob], `avatar-${Date.now()}.jpg`, { type: "image/jpeg" });
    setAvatarFile(file);
    closeCameraModal();
  }, "image/jpeg", 0.9);
}

async function loadProfile() {
  const res = await apiFetch("/auth/me/");
  if (!res.ok) return;
  const user = await res.json();

  document.getElementById("profile-name").textContent =
    `${user.first_name || ""} ${user.last_name || ""}`.trim() || user.username;
  document.getElementById("profile-email").textContent = user.email || user.username;

  const avatarEl = document.getElementById("profile-avatar");
  if (user.avatar) {
    avatarEl.src = user.avatar;
    avatarEl.style.display = "block";
  }

  const form = document.getElementById("profile-form");
  form.first_name.value = user.first_name || "";
  form.last_name.value = user.last_name || "";
  form.phone.value = user.phone || "";
  form.email.value = user.email || "";

  originalProfileValues = {
    first_name: user.first_name || "",
    last_name: user.last_name || "",
    phone: user.phone || "",
    email: user.email || "",
  };

  setCurrentUser(user);
}

async function handleProfileSubmit(e) {
  e.preventDefault();
  const errorEl = document.getElementById("profile-form-error");
  const successEl = document.getElementById("profile-form-success");
  errorEl.textContent = "";
  successEl.textContent = "";

  const formData = new FormData(e.target);
  const avatarFile = formData.get("avatar");
  if (!avatarFile || avatarFile.size === 0) {
    formData.delete("avatar");
  }

  try {
    const res = await apiFetch("/auth/me/", {
      method: "PATCH",
      body: formData,
    });

    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      const firstError = Object.values(data)[0];
      errorEl.textContent = Array.isArray(firstError) ? firstError[0] : "Не удалось сохранить профиль";
      return;
    }

    successEl.textContent = "Профиль обновлён";
    clearAvatarSelection();
    setFormDisabled(true);
    loadProfile();
  } catch (err) {
    errorEl.textContent = "Не удалось сохранить профиль";
  }
}

async function loadStats() {
  const res = await apiFetch("/auth/me/stats/");
  const grid = document.getElementById("profile-stats-grid");

  if (!res.ok) {
    grid.innerHTML = "<p>Не удалось загрузить статистику.</p>";
    return;
  }

  const data = await res.json();

  grid.innerHTML = `
    <div class="stat-card">
      <div class="stat-value">${data.active_loans_count} / ${data.max_loans}</div>
      <div class="stat-label">Книг на руках</div>
    </div>
    <div class="stat-card">
      <div class="stat-value">${data.loan_days}</div>
      <div class="stat-label">Дней на прочтение</div>
    </div>
    <div class="stat-card">
      <div class="stat-value">${data.total_fines_owed}</div>
      <div class="stat-label">Штраф к оплате</div>
    </div>
    <div class="stat-card">
      <div class="stat-value">${data.loan_history_count}</div>
      <div class="stat-label">Книг прочитано всего</div>
    </div>
  `;

  renderProfileLoans(data.active_loans);
  renderProfileReservations(data.reservations);
}

function renderProfileLoans(loans) {
  const tbody = document.getElementById("profile-loans-tbody");
  if (!loans || loans.length === 0) {
    tbody.innerHTML = `<tr><td colspan="4">Сейчас нет книг на руках.</td></tr>`;
    return;
  }

  tbody.innerHTML = loans
    .map((loan) => {
      const canExtend = loan.status === "active" && !loan.is_overdue && loan.extensions_used < 1;
      return `
        <tr>
          <td>${escapeHtml(loan.book_title)}</td>
          <td>${loan.due_date}</td>
          <td>${loan.is_overdue ? "Просрочена" : "На руках"}</td>
          <td>
            ${canExtend
              ? `<button class="btn btn-outline btn-small" data-extend-id="${loan.id}">Продлить</button>`
              : "—"}
          </td>
        </tr>
      `;
    })
    .join("");

  tbody.querySelectorAll("[data-extend-id]").forEach((btn) => {
    btn.addEventListener("click", () => extendLoan(btn.dataset.extendId));
  });
}

function renderProfileReservations(reservations) {
  const tbody = document.getElementById("profile-reservations-tbody");
  if (!reservations || reservations.length === 0) {
    tbody.innerHTML = `<tr><td colspan="3">Нет активных броней.</td></tr>`;
    return;
  }

  const statusLabels = { waiting: "В очереди", ready: "Готова к выдаче" };

  tbody.innerHTML = reservations
    .map(
      (r) => `
        <tr>
          <td>${escapeHtml(r.book_title)}</td>
          <td>${statusLabels[r.status] || r.status}${r.status === "waiting" ? ` (место ${r.queue_position + 1})` : ""}</td>
          <td><button class="btn btn-outline btn-small" data-cancel-id="${r.id}">Отменить</button></td>
        </tr>
      `
    )
    .join("");

  tbody.querySelectorAll("[data-cancel-id]").forEach((btn) => {
    btn.addEventListener("click", () => cancelReservation(btn.dataset.cancelId));
  });
}

async function extendLoan(loanId) {
  const res = await apiFetch(`/circulation/loans/${loanId}/extend/`, { method: "POST" });
  if (res.ok) {
    loadStats();
  } else {
    const data = await res.json().catch(() => ({}));
    alert(data.detail || "Не удалось продлить срок");
  }
}

async function cancelReservation(reservationId) {
  const res = await apiFetch(`/circulation/reservations/${reservationId}/cancel/`, { method: "POST" });
  if (res.ok) {
    loadStats();
  } else {
    alert("Не удалось отменить бронь");
  }
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str ?? "";
  return div.innerHTML;
}