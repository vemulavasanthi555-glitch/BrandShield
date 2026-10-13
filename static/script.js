document.addEventListener("DOMContentLoaded", function () {
    // Mobile navigation toggle
    const menuToggle = document.getElementById("menuToggle");
    const navLinks = document.querySelector(".nav-links");

    if (menuToggle && navLinks) {
        menuToggle.addEventListener("click", function () {
            navLinks.classList.toggle("active");

            const isExpanded = navLinks.classList.contains("active");
            menuToggle.setAttribute("aria-expanded", String(isExpanded));
        });
    }

    // Close mobile navigation after selecting a link
    if (navLinks) {
        const links = navLinks.querySelectorAll("a");

        links.forEach(function (link) {
            link.addEventListener("click", function () {
                navLinks.classList.remove("active");

                if (menuToggle) {
                    menuToggle.setAttribute("aria-expanded", "false");
                }
            });
        });
    }

    // Confirm before resolving or changing a report status
    const statusForms = document.querySelectorAll(
        'form[data-confirm="status"]'
    );

    statusForms.forEach(function (form) {
        form.addEventListener("submit", function (event) {
            const confirmed = window.confirm(
                "Are you sure you want to update this report status?"
            );

            if (!confirmed) {
                event.preventDefault();
            }
        });
    });

    // Display selected logo filename on the brand registration page
    const logoInput = document.querySelector('input[type="file"][name="logo"]');
    const logoFilename = document.getElementById("logoFilename");

    if (logoInput && logoFilename) {
        logoInput.addEventListener("change", function () {
            if (logoInput.files && logoInput.files.length > 0) {
                logoFilename.textContent = logoInput.files[0].name;
            } else {
                logoFilename.textContent = "No file selected";
            }
        });
    }

    // Show a confirmation before deleting or resetting, if such buttons exist
    const confirmButtons = document.querySelectorAll("[data-confirm-message]");

    confirmButtons.forEach(function (button) {
        button.addEventListener("click", function (event) {
            const message =
                button.getAttribute("data-confirm-message") ||
                "Are you sure you want to continue?";

            if (!window.confirm(message)) {
                event.preventDefault();
            }
        });
    });

    // Disable a scan submit button while its form is being submitted
    const scanForms = document.querySelectorAll("form[data-scan-form]");

    scanForms.forEach(function (form) {
        form.addEventListener("submit", function () {
            const submitButton = form.querySelector(
                'button[type="submit"], input[type="submit"]'
            );

            if (submitButton) {
                submitButton.disabled = true;

                if (submitButton.tagName.toLowerCase() === "button") {
                    submitButton.textContent = "Scanning...";
                } else {
                    submitButton.value = "Scanning...";
                }
            }
        });
    });

    // Automatically hide flash messages after a few seconds
    const flashMessages = document.querySelectorAll(
        ".flash-message, .alert"
    );

    flashMessages.forEach(function (message) {
        window.setTimeout(function () {
            message.classList.add("fade-out");

            window.setTimeout(function () {
                if (message.parentNode) {
                    message.parentNode.removeChild(message);
                }
            }, 400);
        }, 5000);
    });

    // Update character counters for text fields that specify a maximum
    const countedFields = document.querySelectorAll("[data-character-counter]");

    countedFields.forEach(function (field) {
        const counterId = field.getAttribute("data-character-counter");
        const counter = document.getElementById(counterId);

        if (!counter) {
            return;
        }

        function updateCounter() {
            const maxLength = field.maxLength;
            const currentLength = field.value.length;

            counter.textContent =
                maxLength > 0
                    ? `${currentLength} / ${maxLength}`
                    : `${currentLength} characters`;
        }

        field.addEventListener("input", updateCounter);
        updateCounter();
    });

    // Add a small loading indicator to buttons marked for loading
    const loadingButtons = document.querySelectorAll("[data-loading-text]");

    loadingButtons.forEach(function (button) {
        const form = button.closest("form");

        if (!form) {
            return;
        }

        form.addEventListener("submit", function () {
            const loadingText = button.getAttribute("data-loading-text");

            if (loadingText) {
                button.disabled = true;
                button.textContent = loadingText;
            }
        });
    });
});
