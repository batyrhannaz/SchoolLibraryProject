// static/js/nav.js
document.addEventListener("DOMContentLoaded", () => {
  const loginLink = document.getElementById("nav-login");
  const logoutLink = document.getElementById("nav-logout");
  const adminLink = document.getElementById("nav-admin");
  const profileLink = document.getElementById("nav-profile");

  if (isLoggedIn()) {
    if (loginLink) loginLink.style.display = "none";
    if (profileLink) profileLink.style.display = "inline";

    if (logoutLink) {
      logoutLink.style.display = "inline";
      logoutLink.addEventListener("click", (e) => {
        e.preventDefault();
        logout();
      });
    }
    const user = getCurrentUser();
    if (adminLink && user && (user.role === "librarian" || user.role === "admin")) {
      adminLink.style.display = "inline";
    }
  } else {
    if (loginLink) loginLink.setAttribute("href", "/login/");
  }
});