document.addEventListener("DOMContentLoaded", function () {

    console.log("Medication Reminder App loaded.");


    // ================================
    // FLASH MESSAGE AUTO HIDE
    // ================================

    const messages =
        document.querySelectorAll(".message");

    messages.forEach(function (message) {

        setTimeout(function () {

            message.style.opacity = "0";

            setTimeout(function () {
                message.remove();
            }, 500);

        }, 4000);

    });


    // ================================
    // DELETE CONFIRMATION
    // ================================

    const deleteButtons =
        document.querySelectorAll(".delete-btn");

    deleteButtons.forEach(function (button) {

        button.addEventListener(
            "click",
            function (event) {

                const answer = confirm(
                    "Are you sure you want to delete this?"
                );

                if (!answer) {
                    event.preventDefault();
                }

            }
        );

    });


    // ================================
    // SEARCH PATIENTS
    // ================================

    const search =
        document.getElementById(
            "patientSearch"
        );

    const rows =
        document.querySelectorAll(
            ".patient-row"
        );

    if (search) {

        search.addEventListener(
            "keyup",
            function () {

                const value =
                    search.value.toLowerCase();

                rows.forEach(function (row) {

                    if (
                        row.textContent
                            .toLowerCase()
                            .includes(value)
                    ) {

                        row.style.display = "";

                    } else {

                        row.style.display = "none";

                    }

                });

            }
        );

    }


    // ================================
    // START DATE / END DATE
    // ================================

    const startDate =
        document.querySelector(
            'input[name="start_date"]'
        );

    const endDate =
        document.querySelector(
            'input[name="end_date"]'
        );

    if (startDate && endDate) {

        endDate.addEventListener(
            "change",
            function () {

                if (
                    startDate.value &&
                    endDate.value &&
                    endDate.value < startDate.value
                ) {

                    alert(
                        "End date cannot be before start date."
                    );

                    endDate.value = "";

                }

            }
        );

    }


    // ================================
    // PASSWORD SHOW / HIDE
    // ================================

    const password =
        document.querySelector(
            'input[type="password"]'
        );

    const toggle =
        document.querySelector(
            ".password-toggle"
        );

    if (password && toggle) {

        toggle.addEventListener(
            "click",
            function () {

                if (
                    password.type === "password"
                ) {

                    password.type = "text";

                    toggle.textContent = "Hide";

                } else {

                    password.type = "password";

                    toggle.textContent = "Show";

                }

            }
        );

    }

});