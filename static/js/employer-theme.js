/* Small usability helpers for the employer workspace.
   No business logic lives here; this file only connects existing controls. */
(function () {
    "use strict";

    function queryValue(name) {
        return new URLSearchParams(window.location.search).get(name) || "";
    }

    function applyIncomingSearch() {
        var query = queryValue("q").trim();
        if (!query) return;

        var candidateSearch = document.getElementById("cand-search");
        var jobsSearch = document.getElementById("jobs-search");
        var target = candidateSearch || jobsSearch;
        if (target) {
            target.value = query;
            target.dispatchEvent(new Event("input", { bubbles: true }));
        }
    }

    function applyIncomingStatus() {
        var status = queryValue("status").trim();
        if (!status) return;

        var statusFilter = document.getElementById("cand-status-filter");
        if (!statusFilter) return;

        var option = Array.from(statusFilter.options).find(function (item) {
            return item.value === status;
        });
        if (option) {
            statusFilter.value = status;
            statusFilter.dispatchEvent(new Event("change", { bubbles: true }));
        }
    }

    function openCreateJobFromUrl() {
        if (queryValue("create") !== "1") return;
        var button = document.getElementById("new-job-btn");
        if (button) window.setTimeout(function () { button.click(); }, 120);
    }

    function addSearchShortcut() {
        document.addEventListener("keydown", function (event) {
            if (event.key !== "/" || event.ctrlKey || event.metaKey || event.altKey) return;
            var active = document.activeElement;
            if (active && /INPUT|TEXTAREA|SELECT/.test(active.tagName)) return;
            var input = document.querySelector(".qh-global-search input");
            if (input) {
                event.preventDefault();
                input.focus();
            }
        });
    }

    document.addEventListener("DOMContentLoaded", function () {
        applyIncomingSearch();
        applyIncomingStatus();
        openCreateJobFromUrl();
        addSearchShortcut();
        if (window.feather) window.feather.replace();
    });
})();
