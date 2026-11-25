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
      id: "mailchimp", name: "ListSignal for Mailchimp", category: "Email & Audience",
      page: "mailchimp.html",
      keywords: "mailchimp email marketing audience subscribers growth campaign reports opens clicks bounces top campaigns list health draft campaign newsletter connect mailchimp connect my mailchimp account with plugvana"
    },
    {
      id: "pdfsignal", name: "PDFSignal", category: "Documents & Files",
      page: "pdfsignal.html",
      keywords: "pdf merge split compress convert extract text pages documents files pdfsignal batch automatically schedule folder convert all files in this folder to PDF batch convert to PDF convert every invoice automatically always save my reports as PDF extract text from every PDF in this folder"
    },
    {
      id: "sheetsignal", name: "SheetSignal", category: "Documents & Files",
      page: "sheetsignal.html",
      keywords: "spreadsheet excel csv xlsx clean dedupe merge convert summary sheet data sheetsignal batch automatically schedule folder clean every CSV I download batch clean CSVs dedupe every spreadsheet in this folder automatically clean new CSVs merge all CSVs in this folder"
    },
    {
      id: "imagesignal", name: "ImageSignal", category: "Documents & Files",
      page: "imagesignal.html",
      keywords: "image resize convert png bmp ppm jpeg dimensions compress photos pictures imagesignal batch automatically schedule folder resize all photos in this folder batch resize images resize every new photo automatically convert all images in this folder always shrink my screenshots"
    },
    {
      id: "convertsignal", name: "ConvertSignal", category: "Documents & Files",
      page: "convertsignal.html",
      keywords: "convert documents markdown html text docx word convertisseur conversion convertsignal batch automatically schedule folder convert all files in this folder batch convert documents convert every docx automatically always turn my Markdown into HTML convert new files as they arrive"
    },
    {
      id: "ledgersignal-sage", name: "LedgerSignal for Sage", category: "Money & Accounting",
      page: "ledgersignal-sage.html",
      keywords: "sage accounting invoices overdue bank accounts ledger bookkeeping ledgersignal"
    },
    {
      id: "booksignal-xero", name: "BookSignal for Xero", category: "Money & Accounting",
      page: "booksignal-xero.html",
      keywords: "xero invoices contacts profit loss bank bookkeeping accounting booksignal"
    },
    {
      id: "billsignal-freshbooks", name: "BillSignal for FreshBooks", category: "Money & Accounting",
      page: "billsignal-freshbooks.html",
      keywords: "freshbooks invoices expenses payments time tracking freelancers billsignal"
    },
    {
      id: "cashsignal-wave", name: "CashSignal for Wave", category: "Money & Accounting",
      page: "cashsignal-wave.html",
      keywords: "wave accounting invoices customers free bookkeeping cashsignal"
    },
    {
      id: "dealsignal-hubspot", name: "DealSignal for HubSpot", category: "Customers & Sales",
      page: "dealsignal-hubspot.html",
      keywords: "hubspot crm contacts companies deals pipeline sales dealsignal"
    },
    {
      id: "pipesignal-pipedrive", name: "PipeSignal for Pipedrive", category: "Customers & Sales",
      page: "pipesignal-pipedrive.html",
      keywords: "pipedrive deals persons organizations activities pipeline sales pipesignal"
    },
    {
      id: "clientsignal-zoho", name: "ClientSignal for Zoho CRM", category: "Customers & Sales",
      page: "clientsignal-zoho.html",
      keywords: "zoho crm accounts contacts deals leads search clientsignal"
    },
    {
      id: "basesignal-airtable", name: "BaseSignal for Airtable", category: "Customers & Sales",
      page: "basesignal-airtable.html",
      keywords: "airtable bases tables records database spreadsheet basesignal"
    },
    {
      id: "sendsignal-mailerlite", name: "SendSignal for MailerLite", category: "Email & Audience",
      page: "sendsignal-mailerlite.html",
      keywords: "mailerlite email subscribers groups campaigns automations newsletter sendsignal"
    },
    {
      id: "postsignal-kit", name: "PostSignal for Kit", category: "Email & Audience",
      page: "postsignal-kit.html",
      keywords: "kit convertkit email subscribers tags forms sequences broadcasts creators postsignal"
    },
    {
      id: "reachsignal-constantcontact", name: "ReachSignal for Constant Contact", category: "Email & Audience",
      page: "reachsignal-constantcontact.html",
      keywords: "constant contact email contacts lists campaigns small business reachsignal"
    },
    {
      id: "newssignal-aweber", name: "NewsSignal for AWeber", category: "Email & Audience",
      page: "newssignal-aweber.html",
      keywords: "aweber email lists subscribers broadcasts campaigns newsletter newssignal"
    },
    {
      id: "boardsignal-trello", name: "BoardSignal for Trello", category: "Work & Scheduling",
      page: "boardsignal-trello.html",
      keywords: "trello boards lists cards kanban tasks projects boardsignal"
    },
    {
      id: "tasksignal-monday", name: "TaskSignal for monday.com", category: "Work & Scheduling",
      page: "tasksignal-monday.html",
      keywords: "monday.com monday boards items groups updates work management tasksignal"
    },
    {
      id: "worksignal-clickup", name: "WorkSignal for ClickUp", category: "Work & Scheduling",
      page: "worksignal-clickup.html",
      keywords: "clickup spaces lists tasks overdue projects work management worksignal"
    },
    {
      id: "donesignal-ticktick", name: "DoneSignal for TickTick", category: "Work & Scheduling",
      page: "donesignal-ticktick.html",
      keywords: "ticktick tasks projects todo list overdue personal productivity donesignal"
    },
    {
      id: "meetsignal-calcom", name: "MeetSignal for Cal.com", category: "Work & Scheduling",
      page: "meetsignal-calcom.html",
      keywords: "cal.com calendly bookings scheduling event types calendar meetsignal"
    },
    {
      id: "formsignal-typeform", name: "FormSignal for Typeform", category: "Work & Scheduling",
      page: "formsignal-typeform.html",
      keywords: "typeform forms responses surveys leads feedback formsignal"
    },
    {
      id: "legacysignal-cobol", name: "LegacySignal for COBOL", category: "Code & Legacy",
      page: "legacysignal-cobol.html",
      keywords: "cobol mainframe legacy estate inventory documentation impact analysis copybook db2 cics jcl call map modernization modernisation dead code legacysignal connect my cobol codebase with plugvana"
    },
    {
      id: "codesignal-python", name: "CodeSignal for Python", category: "Code & Legacy",
      page: "codesignal-python.html",
      keywords: "python code repo map documentation docstring coverage dependencies dead code complexity todo syntax tests codesignal connect my python codebase with plugvana"
    },
    {
      id: "statsignal-sas", name: "StatSignal for SAS", category: "Code & Legacy",
      page: "statsignal-sas.html",
      keywords: "sas programs macros log scan errors warnings dataset lineage impact analysis estate inventory statsignal connect my sas codebase with plugvana"
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
