(function () {
  // Mark Gutenberg column rows that contain Altmetric badges so CSS can keep them inline.
  document
    .querySelectorAll(".post-content .altmetric-embed, .wp-mirror .altmetric-embed")
    .forEach(function (badge) {
    var cols = badge.closest(".wp-block-columns");
    if (cols) cols.classList.add("wp-altmetric-row");
  });

  document
    .querySelectorAll(
      ".post-content .wp-block-ub-content-toggle-accordion, .wp-mirror .wp-block-ub-content-toggle-accordion"
    )
    .forEach(function (acc) {
    var title = acc.querySelector(".wp-block-ub-content-toggle-accordion-title-wrap");
    var content = acc.querySelector(".wp-block-ub-content-toggle-accordion-content-wrap");
    if (!title || !content) return;
    title.setAttribute("role", "button");
    title.setAttribute("tabindex", "0");
    var expanded = !content.classList.contains("ub-hide");
    title.setAttribute("aria-expanded", expanded ? "true" : "false");
    function toggle() {
      content.classList.toggle("ub-hide");
      var open = !content.classList.contains("ub-hide");
      title.setAttribute("aria-expanded", open ? "true" : "false");
    }
    title.addEventListener("click", function (e) {
      e.preventDefault();
      toggle();
    });
    title.addEventListener("keydown", function (e) {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        toggle();
      }
    });
  });
})();
