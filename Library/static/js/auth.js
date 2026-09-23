// static/js/auth.js
document.addEventListener("DOMContentLoaded", () => {
  // Если уже авторизован — сразу в каталог
  if (isLoggedIn()) {
    window.location.href = "/catalog/";
    return;
  }

  // ===== Переключение вкладок Вход / Регистрация =====
  const tabBtns = document.querySelectorAll(".tab-btn");
  const loginForm = document.getElementById("login-form");
  const registerForm = document.getElementById("register-form");

  tabBtns.forEach((btn) => {
    btn.addEventListener("click", () => {
      tabBtns.forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");

      if (btn.dataset.tab === "login-form") {
        loginForm.style.display = "block";
        registerForm.style.display = "none";
      } else {
        loginForm.style.display = "none";
        registerForm.style.display = "block";
      }
    });
  });

  // ===== Вход =====
  loginForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const errorEl = document.getElementById("login-error");
    errorEl.textContent = "";

    const formData = new FormData(loginForm);
    const payload = {
      username: formData.get("username"),
      password: formData.get("password"),
    };

    try {
      const res = await fetch(`${API_BASE}/auth/login/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        errorEl.textContent = data.non_field_errors?.[0] || "Неверный логин или пароль";
        return;
      }

      const data = await res.json();
      setTokens(data.access, data.refresh);
      setCurrentUser(data.user);
      window.location.href = "/catalog/";
    } catch (err) {
      errorEl.textContent = "Не удалось подключиться к серверу";
    }
  });

  // ===== Регистрация =====
  registerForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const errorEl = document.getElementById("register-error");
    const successEl = document.getElementById("register-success");
    errorEl.textContent = "";
    successEl.textContent = "";

    const formData = new FormData(registerForm);
    const payload = {
      username: formData.get("username"),
      first_name: formData.get("first_name"),
      last_name: formData.get("last_name"),
      email: formData.get("email"),
      phone: formData.get("phone"),
      password: formData.get("password"),
    };

    try {
      const res = await fetch(`${API_BASE}/auth/register/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        const firstError = Object.values(data)[0];
        errorEl.textContent = Array.isArray(firstError) ? firstError[0] : "Ошибка регистрации";
        return;
      }

      successEl.textContent = "Готово! Теперь войдите под своим логином.";
      registerForm.reset();

      document.querySelector('[data-tab="login-form"]').click();
    } catch (err) {
      errorEl.textContent = "Не удалось подключиться к серверу";
    }
  });
});