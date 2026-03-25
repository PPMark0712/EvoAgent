(() => {
    const html = document.documentElement ? document.documentElement.outerHTML : "";
    return String(html || "");
})();
