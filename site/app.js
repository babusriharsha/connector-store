/* Plugvana — shared JS: front-page Connect buttons and the
   home catalog search/filter. There is deliberately NO copying
   behaviour on this site: connecting happens inside the user's own Muse,
   so a Connect button simply tells the visitor the one sentence to say.
   The search index below mirrors search-index.json (kept inline so search
   also works when the site is opened straight from disk). */
(function () {
  "use strict";

  /* ---------- Front-page Connect buttons: show the sentence to say ---------- */
  document.querySelectorAll("[data-say]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var say = btn.getAttribute("data-say");
      var status = btn.parentElement.querySelector(".connect-status");
      if (status) status.textContent = "Open your Muse and say: '" + say + "'";
      var original = "Connect";
      btn.textContent = "✓ Got it";
      setTimeout(function () { btn.textContent = original; }, 2600);
    });
  });

  /* ---------- Home catalog: live search + category chips ---------- */
  var SEARCH_INDEX = [
    {
      id: "woocommerce", name: "ShopSignal for WooCommerce", category: "Online stores",
      page: "woocommerce.html",
      keywords: "woocommerce wordpress wp store shop orders refunds products inventory stock low stock alerts best sellers customers lapsed customers coupons morning store brief connect my shop connect my store connect my woocommerce store with plugvana sales snapshot revenue"
    },
    {
      id: "etsy", name: "SellSignal for Etsy", category: "Online stores",
      page: "etsy.html",
      keywords: "etsy shop seller receipts orders listings inventory quantities low quantity alerts reviews payment ledger morning shop brief connect my shop connect my etsy connect my etsy shop with plugvana sales snapshot"
    },
    {
      id: "mailchimp", name: "ListSignal for Mailchimp", category: "Email marketing",
      page: "mailchimp.html",
      keywords: "mailchimp email marketing audience subscribers growth campaign reports opens clicks bounces top campaigns list health draft campaign newsletter connect mailchimp connect my mailchimp account with plugvana"
    }
  ];

  var grid = document.getElementById("catalog-grid");
  if (!grid) return;
  var input = document.getElementById("catalog-search-input");
  var chips = document.querySelectorAll(".chip[data-filter]");
  var noResults = document.getElementById("no-results");
  var activeFilter = "All";

  function matches(entry, q) {
    var hay = (entry.name + " " + entry.category + " " + entry.keywords).toLowerCase();
    return q.split(/\s+/).filter(Boolean).every(function (word) { return hay.indexOf(word) !== -1; });
  }
  function apply() {
    var q = (input ? input.value : "").trim().toLowerCase();
    var visible = 0;
    SEARCH_INDEX.forEach(function (entry) {
      var card = grid.querySelector('[data-card="' + entry.id + '"]');
      if (!card) return;
      var show = (activeFilter === "All" || entry.category === activeFilter) && (q === "" || matches(entry, q));
      card.style.display = show ? "" : "none";
      if (show) visible++;
    });
    if (noResults) noResults.style.display = visible === 0 ? "" : "none";
  }
  if (input) {
    input.addEventListener("input", apply);
    var params = new URLSearchParams(window.location.search);
    var q0 = params.get("q");
    if (q0) input.value = q0;
  }
  chips.forEach(function (chip) {
    chip.addEventListener("click", function () {
      chips.forEach(function (c) { c.setAttribute("aria-pressed", "false"); });
      chip.setAttribute("aria-pressed", "true");
      activeFilter = chip.getAttribute("data-filter");
      apply();
    });
  });
  apply();
})();
