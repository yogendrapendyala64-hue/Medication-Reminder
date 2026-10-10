/* MediPulse front-end helpers: modals, live search, confirmations, flash messages. */
(function () {
  function openModal(id) {
    var m = document.getElementById(id);
    if (!m) return;
    m.hidden = false;
    var first = m.querySelector("input, select, textarea");
    if (first) first.focus();
  }
  function closeModals() {
    document.querySelectorAll(".scrim").forEach(function (m) { m.hidden = true; });
  }

  document.addEventListener("click", function (e) {
    var opener = e.target.closest("[data-open-modal]");
    if (opener) { e.preventDefault(); openModal(opener.getAttribute("data-open-modal")); return; }
    if (e.target.closest("[data-close-modal]")) { closeModals(); return; }
    if (e.target.classList && e.target.classList.contains("scrim")) { closeModals(); return; }
    var dismiss = e.target.closest("[data-dismiss]");
    if (dismiss) dismiss.parentElement.remove();
  });
  document.addEventListener("keydown", function (e) { if (e.key === "Escape") closeModals(); });

  // Live filter: <input data-filter="#list"> hides rows of #list whose data-search text does not match.
  document.querySelectorAll("[data-filter]").forEach(function (input) {
    var target = document.querySelector(input.getAttribute("data-filter"));
    if (!target) return;
    var empty = target.parentElement.querySelector("[data-empty]");
    function apply() {
      var q = input.value.trim().toLowerCase(), shown = 0;
      target.querySelectorAll("[data-search]").forEach(function (row) {
        var hit = !q || row.getAttribute("data-search").indexOf(q) > -1;
        row.hidden = !hit;
        if (hit) shown++;
      });
      if (empty) empty.hidden = shown > 0;
    }
    input.addEventListener("input", apply);
    apply();
  });

  // Confirm before destructive actions: <form data-confirm="Remove this?">
  document.addEventListener("submit", function (e) {
    var msg = e.target.getAttribute && e.target.getAttribute("data-confirm");
    if (msg && !window.confirm(msg)) e.preventDefault();
  });

  // Flash messages fade out after a few seconds.
  setTimeout(function () {
    document.querySelectorAll(".flash").forEach(function (f) { f.remove(); });
  }, 5000);

  if (location.hash === "#add-patient") openModal("addPatient");
})();
