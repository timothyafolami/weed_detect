document.addEventListener('DOMContentLoaded', () => {
    const registrationForm = document.getElementById('registrationForm');
    if (registrationForm) {
        registrationForm.addEventListener('submit', async (e) => {
            e.preventDefault();

            const name = document.getElementById('name').value;
            const email = document.getElementById('email').value;
            const phone = document.getElementById('phone').value;
            const address = document.getElementById('address').value;

            const userInfo = {
                "Name": name,
                "Email": email,
                "Address": address,
                "Phone Number": phone
            };

            const response = await fetch('/register', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(userInfo),
            });

            const messageDiv = document.getElementById('message');
            if (response.ok) {
                messageDiv.textContent = 'Registration successful! Redirecting to the application page...';
                setTimeout(() => {
                    window.location.href = '/app';
                }, 2000); // Redirects after 2 seconds
            } else {
                const error = await response.json();
                messageDiv.textContent = `Registration failed: ${error.detail}`;
            }
        });
    }
});
