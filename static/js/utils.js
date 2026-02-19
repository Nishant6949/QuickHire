(function () {
    window.escapeHtml = function (str) {
        var div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    };

    window.scoreColorClass = function (score) {
        if (score >= 90) return 'green';
        if (score >= 70) return 'amber';
        return 'red';
    };
})();
