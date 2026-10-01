(function () {
  var key = "derekdevs-theme";
  var root = document.documentElement;

  function current() {
    return root.getAttribute("data-theme") === "dark" ? "dark" : "light";
  }

  function nextLabel(theme) {
    return theme === "dark" ? "Light" : "Dark";
  }

  document.querySelectorAll("[data-theme-toggle]").forEach(function (btn) {
    btn.hidden = false;
    var theme = current();
    btn.textContent = nextLabel(theme);
    btn.setAttribute(
      "aria-label",
      "Switch to " + nextLabel(theme).toLowerCase() + " theme",
    );
    btn.addEventListener("click", function () {
      var next = current() === "dark" ? "light" : "dark";
      root.setAttribute("data-theme", next);
      var meta = document.querySelector('meta[name="theme-color"]');
      if (meta) {
        meta.setAttribute("content", root.getAttribute("data-theme-color-" + next));
      }
      try {
        localStorage.setItem(key, next);
      } catch (e) {}
      btn.textContent = nextLabel(next);
      btn.setAttribute(
        "aria-label",
        "Switch to " + nextLabel(next).toLowerCase() + " theme",
      );
    });
  });
})();
