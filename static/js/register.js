document.addEventListener("DOMContentLoaded", () => {
    const registerForm = document.getElementById("registerForm");
    const password = document.getElementById("password");
    const confirmPassword = document.getElementById("confirm-password");
    const errorText = document.getElementById("errorText");
  
    registerForm.addEventListener("submit", async function (e) {
      e.preventDefault();
  
      // Client-side validations
      if (password.value !== confirmPassword.value) {
        errorText.textContent = "Passwords do not match.";
        errorText.classList.remove("hidden");
        return;
      }
  
      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      const passwordRegex = /^(?=.*[A-Za-z])(?=.*\d)[A-Za-z\d@$!%*#?&]{6,}$/;
  
      if (!emailRegex.test(registerForm.email.value)) {
        errorText.textContent = "Invalid email format.";
        errorText.classList.remove("hidden");
        return;
      }
  
      if (!passwordRegex.test(password.value)) {
        errorText.textContent = "Password must be at least 6 characters and contain letters and numbers.";
        errorText.classList.remove("hidden");
        return;
      }
  
      errorText.classList.add("hidden");
  
      // Prepare data
      const formData = {
        name: document.getElementById("name").value,
        email: document.getElementById("email").value,
        password: password.value,
        confirm_password: confirmPassword.value,
      };
  
      try {
        // AJAX request
        const response = await fetch("/register", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(formData),
        });
  
        const data = await response.json();
  
        if (response.ok) {
            localStorage.setItem("jwt_token", data.token);
            alert("Welcome! You've been signed in.");
            window.location.href = "/"; // redirect to homepage
        } else {
          errorText.textContent = data.error || "Registration failed.";
          errorText.classList.remove("hidden");
        }
      } catch (err) {
        console.error("Registration error:", err);
        errorText.textContent = "Something went wrong. Please try again.";
        errorText.classList.remove("hidden");
      }
    });
  });
  