// Keep track of the active user type
window.userType = 'user'; // default to seeker
window.registrationData = null; // store signup data temporarily before location is resolved

// Configure user dashboard switching
function setUserType(type) {
    window.userType = type;

    // Toggle active classes on styling
    const seekerBtn = document.getElementById('user-type-seeker');
    const providerBtn = document.getElementById('user-type-provider');
    const subtitle = document.getElementById('auth-subtitle-text');

    if (type === 'user') {
        seekerBtn.classList.add('active');
        providerBtn.classList.remove('active');
        subtitle.textContent = "Premium Room Renting & Finding Portal";
    } else {
        seekerBtn.classList.remove('active');
        providerBtn.classList.add('active');
        subtitle.textContent = "List, Manage, and Monitise Your Properties";
    }

    // Reset alert banners
    clearAlerts();
}

function showSignUpPanel() {
    document.getElementById('signin-panel').classList.add('hidden');
    document.getElementById('signup-panel').classList.remove('hidden');
    document.getElementById('location-panel').classList.add('hidden');
    clearAlerts();
}

function showSignInPanel() {
    document.getElementById('signup-panel').classList.add('hidden');
    document.getElementById('signin-panel').classList.remove('hidden');
    document.getElementById('location-panel').classList.add('hidden');
    clearAlerts();
}

// Sign In Action
async function handleSignIn(event) {
    event.preventDefault();
    clearAlerts();

    const email = document.getElementById('signin-email').value.trim();
    const password = document.getElementById('signin-password').value;
    const submitBtn = document.getElementById('signin-btn');

    if (!email || !password) {
        showError('Please provide both your email and password.');
        return;
    }

    showLoader(true);
    submitBtn.disabled = true;

    try {
        const response = await fetch('/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password, user_type: window.userType })
        });
        const result = await response.json();

        showLoader(false);

        if (result.success) {
            showSuccess('Welcome back! Redirecting...');
            document.getElementById('signin-panel').classList.add('hidden');
            document.getElementById('success-panel').classList.remove('hidden');
            setTimeout(() => {
                window.location.href = result.redirect_url;
            }, 1500);
        } else {
            submitBtn.disabled = false;
            showError(result.message || 'Incorrect email or password.');
        }
    } catch (err) {
        showLoader(false);
        submitBtn.disabled = false;
        showError('Network error. Failed to connect to server.');
        console.error('Sign in error:', err);
    }
}

// Check Email & Start Sign Up Flow
async function handlePreSignUp(event) {
    event.preventDefault();
    clearAlerts();

    const firstName = document.getElementById('signup-firstname').value.trim();
    const lastName = document.getElementById('signup-lastname').value.trim();
    const phone = document.getElementById('signup-phone').value.trim();
    const email = document.getElementById('signup-email').value.trim();
    const password = document.getElementById('signup-password').value;
    const submitBtn = document.getElementById('signup-profile-btn');

    if (!firstName || !lastName || !phone || !email || !password) {
        showError('Please fill out all registration fields.');
        return;
    }

    showLoader(true);
    submitBtn.disabled = true;

    // Store temporarily in memory
    window.registrationData = {
        first_name: firstName,
        last_name: lastName,
        phone: phone,
        email: email,
        password: password,
        user_type: window.userType
    };

    try {
        // First check if email is unique
        const checkRes = await fetch('/check-email', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, user_type: window.userType })
        });
        const checkResult = await checkRes.json();

        if (checkResult.exists) {
            showLoader(false);
            submitBtn.disabled = false;
            showError('Email is already registered for this user type.');
            return;
        }

        // Attempt to request geolocation coordinates
        if (navigator.geolocation) {
            navigator.geolocation.getCurrentPosition(
                // Success GPS callback
                (position) => {
                    const gpsLocation = {
                        latitude: position.coords.latitude,
                        longitude: position.coords.longitude
                    };
                    submitFinalRegistration(gpsLocation);
                },
                // Error GPS callback
                (error) => {
                    console.warn("GPS fetching failed:", error);
                    showLoader(false);
                    // Fallback to manual entry
                    document.getElementById('signup-panel').classList.add('hidden');
                    document.getElementById('location-panel').classList.remove('hidden');
                },
                { enableHighAccuracy: true, timeout: 8000, maximumAge: 0 }
            );
        } else {
            showLoader(false);
            // Browser doesn't support geolocation, show manual form
            document.getElementById('signup-panel').classList.add('hidden');
            document.getElementById('location-panel').classList.remove('hidden');
        }

    } catch (err) {
        showLoader(false);
        submitBtn.disabled = false;
        showError('Server lookup failed. Please check connection.');
        console.error(err);
    }
}

// Manual Location Registration submit
async function handleLocationSubmit(event) {
    event.preventDefault();
    clearAlerts();

    const street = document.getElementById('street').value.trim();
    const city = document.getElementById('city').value.trim();
    const submitBtn = document.getElementById('location-btn');

    if (!street || !city) {
        showError('Please supply street address and city.');
        return;
    }

    submitBtn.disabled = true;
    showLoader(true);

    const manualLocation = {
        street: street,
        city: city,
        manual: true
    };

    submitFinalRegistration(manualLocation);
}

// Perform AJAX Registration
async function submitFinalRegistration(locationPayload) {
    const signupData = {
        ...window.registrationData,
        location: locationPayload
    };

    try {
        const response = await fetch('/register', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(signupData)
        });
        const result = await response.json();

        showLoader(false);

        if (result.success) {
            showSuccess('Profile created successfully!');
            document.getElementById('signup-panel').classList.add('hidden');
            document.getElementById('location-panel').classList.add('hidden');
            document.getElementById('success-panel').classList.remove('hidden');

            setTimeout(() => {
                window.location.href = result.redirect_url;
            }, 1800);
        } else {
            resetControllers();
            showError(result.message || 'Registration failed. Try checking details.');
        }
    } catch (err) {
        showLoader(false);
        resetControllers();
        showError('Server communications error. Account creation failed.');
        console.error(err);
    }
}

function resetControllers() {
    const pBtn = document.getElementById('signup-profile-btn');
    const lBtn = document.getElementById('location-btn');
    if (pBtn) pBtn.disabled = false;
    if (lBtn) lBtn.disabled = false;
}

// Helpers
function showError(message) {
    const alert = document.getElementById('error-message');
    alert.innerText = message;
    alert.style.display = 'block';
}

function showSuccess(message) {
    const alert = document.getElementById('success-message');
    alert.innerText = message;
    alert.style.display = 'block';
}

function clearAlerts() {
    document.getElementById('error-message').style.display = 'none';
    document.getElementById('success-message').style.display = 'none';
}

function showLoader(visible) {
    document.getElementById('loading').style.display = visible ? 'flex' : 'none';
}