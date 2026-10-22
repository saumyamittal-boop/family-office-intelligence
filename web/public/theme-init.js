/* Apply the saved or system theme before first paint, so a dark-mode user never sees a white flash.
   This is a file of its own, not an inline script in index.html, so the production Content-Security-Policy can forbid inline scripts. */
(function () {
  try {
    var saved = window.localStorage.getItem("foi.theme");
    var dark = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
    var theme = saved === "light" || saved === "dark" ? saved : dark ? "dark" : "light";
    document.documentElement.setAttribute("data-theme", theme);
  } catch (e) {
    /* storage blocked: keep the default */
  }
})();
