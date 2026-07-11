(function () {
  var KEY = "dnd_theme";

  function getStoredTheme() {
    return localStorage.getItem(KEY) || "dark";
  }

  function applyTheme(theme) {
    document.documentElement.setAttribute("data-theme", theme);
  }

  applyTheme(getStoredTheme());

  window.dndTheme = {
    get: getStoredTheme,
    set: function (theme) {
      localStorage.setItem(KEY, theme);
      applyTheme(theme);
    },
    toggle: function () {
      var next = getStoredTheme() === "light" ? "dark" : "light";
      window.dndTheme.set(next);
      return next;
    },
  };
})();