// static/js/api.js
const API_BASE = "/api";

function getAccessToken() {
  return localStorage.getItem("access_token");
}

function getRefreshToken() {
  return localStorage.getItem("refresh_token");
}

function setTokens(access, refresh) {
  if (access) localStorage.setItem("access_token", access);
  if (refresh) localStorage.setItem("refresh_token", refresh);
}

function clearTokens() {
  localStorage.removeItem("access_token");
  localStorage.removeItem("refresh_token");
  localStorage.removeItem("user");
}

function getCurrentUser() {
  const raw = localStorage.getItem("user");
  return raw ? JSON.parse(raw) : null;
}

function setCurrentUser(user) {
  localStorage.setItem("user", JSON.stringify(user));
}

function isLoggedIn() {
  return !!getAccessToken();
}

async function refreshAccessToken() {
  const refresh = getRefreshToken();
  if (!refresh) return false;

  const res = await fetch(`${API_BASE}/auth/refresh/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh }),
  });

  if (!res.ok) {
    clearTokens();
    return false;
  }
  const data = await res.json();
  setTokens(data.access, null);
  return true;
}

async function apiFetch(path, options = {}) {
  const headers = options.headers ? { ...options.headers } : {};
  if (!(options.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }

  const token = getAccessToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;

  let res = await fetch(`${API_BASE}${path}`, { ...options, headers });

  if (res.status === 401 && getRefreshToken()) {
    const refreshed = await refreshAccessToken();
    if (refreshed) {
      headers["Authorization"] = `Bearer ${getAccessToken()}`;
      res = await fetch(`${API_BASE}${path}`, { ...options, headers });
    }
  }

  return res;
}

function requireAuth() {
  if (!isLoggedIn()) {
    window.location.href = "/login/";
  }
}

function logout() {
  const refresh = getRefreshToken();
  if (refresh) {
    apiFetch("/auth/logout/", {
      method: "POST",
      body: JSON.stringify({ refresh }),
    }).catch(() => {});
  }
  clearTokens();
  window.location.href = "/login/";
}