document.getElementById("loginForm").addEventListener("submit", async function (event) {
    event.preventDefault();
    const firstName = document.getElementById("firstName").value;
    const lastName = document.getElementById("lastName").value;
    const password = document.getElementById("password").value;
    const errorMessage = document.getElementById("errorMessage");
    const username = `${firstName} ${lastName}`;
    const credentials =  btoa(`${username}:${password}`);
    try {
        const response = await fetch("http://localhost:8000/api/v1/student/login", {
            method: "POST",
            headers: {
                "Authorization": "Basic " + credentials,
                "Content-Type": "application/json"
            }
        });
        if (response.ok) {
            const data = await response.json();
            sessionStorage.setItem("studentId", data[0].student_id);
            sessionStorage.setItem("credentials", credentials);
            window.location.href = "/students_page/students.html";
        } else {
            errorMessage.style.display = "block";
        }
    } catch (error) {
        console.error("Error during login:", error);
        errorMessage.style.display = "block";
    }
});
