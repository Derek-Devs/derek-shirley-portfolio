(function () {
  var root = document.documentElement;
  var theme = "light";
  try {
    var stored = localStorage.getItem("derekdevs-theme");
    if (stored === "dark") theme = "dark";
  } catch (e) {}
  root.setAttribute("data-theme", theme);
  var meta = document.querySelector('meta[name="theme-color"]');
  if (meta) {
    meta.setAttribute("content", root.getAttribute("data-theme-color-" + theme));
  }
})();
