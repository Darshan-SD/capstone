    document.addEventListener("DOMContentLoaded", () => {
        const loginForm = document.getElementById("loginForm");
    
        loginForm.addEventListener("submit", async function (e) {
        e.preventDefault();
    
        const email = document.getElementById("email").value;
        const password = document.getElementById("password").value;
    
        const response = await fetch("/login", {
            method: "POST",
            headers: {
            "Content-Type": "application/json",
            },
            body: JSON.stringify({ email, password }),
        });
    
        const data = await response.json();
    
        if (response.ok) {
            localStorage.setItem("jwt_token", data.token);
            alert("Login successful!");
            window.location.href = "/";
        } else {
            alert(data.error || "Login failed");
        }
        });
    });
    