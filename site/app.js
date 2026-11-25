/* The Connector Store — shared JS: copy buttons, home catalog search/filter.
   The search index below mirrors search-index.json (kept inline so search
   also works when the site is opened straight from disk). */
(function () {
  "use strict";

  /* ---------- Copy buttons (install prompts + front-page Connect) ---------- */
  document.querySelectorAll("[data-copy-target]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var target = document.getElementById(btn.getAttribute("data-copy-target"));
      var status = btn.parentElement.querySelector(".copy-status");
      if (!target) return;
      /* Hidden prompt stores have no innerText in some browsers — fall back
         to textContent so the Connect buttons still copy the full prompt. */
      var text = target.innerText || target.textContent;
      var isConnect = btn.hasAttribute("data-connect");
      var okMsg = isConnect
        ? "Prompt copied — paste it in your Muse"
        : "Copied. Now paste it into your Muse chat.";
      function done(msg) {
        if (status) status.textContent = msg;
        if (isConnect && msg === okMsg) {
          var original = btn.textContent;
          btn.textContent = "✓ Copied";
          setTimeout(function () { btn.textContent = original; }, 2600);
        }
      }
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(
          function () { done(okMsg); },
          function () { fallback(); }
        );
      } else { fallback(); }
      function fallback() {
        var ta = document.createElement("textarea");
        ta.value = text; document.body.appendChild(ta); ta.select();
        try { document.execCommand("copy"); done(okMsg); }
        catch (e) { done(isConnect ? "Copy didn't work — open the connector page and copy the prompt from there." : "Copy didn't work — select the text above and copy it manually."); }
        document.body.removeChild(ta);
      }
    });
  });

  /* ---------- Home catalog: live search + category chips ---------- */
  var SEARCH_INDEX = [
    {
      id: "woocommerce", name: "WooCommerce Connector", category: "Online stores",
      page: "woocommerce.html",
      keywords: "woocommerce wordpress wp store shop orders refunds products inventory stock low stock alerts best sellers customers lapsed customers coupons morning store brief connect my shop connect my store rest api keys sales snapshot revenue"
    },
    {
      id: "etsy", name: "Etsy Connector", category: "Online stores",
      page: "etsy.html",
      keywords: "etsy shop seller receipts orders listings inventory quantities low quantity alerts reviews payment ledger morning shop brief connect my shop connect my etsy sales snapshot oauth"
    },
    {
      id: "mailchimp", name: "Mailchimp Connector", category: "Email marketing",
      page: "mailchimp.html",
      keywords: "mailchimp email marketing audience subscribers growth campaign reports opens clicks bounces top campaigns list health draft campaign api key newsletter connect mailchimp"
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
