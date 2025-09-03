document.addEventListener("DOMContentLoaded", () => {
    const logoutLink = document.querySelector('[data-logout-link]');
    if (logoutLink) {
      logoutLink.addEventListener("click", function (e) {
        e.preventDefault();
        localStorage.removeItem("jwt_token"); 
        window.location.href = logoutLink.href; // Redirect to logout
      });
    }
  });
  