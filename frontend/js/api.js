(() => {
    const configuredBase = window.HARMONICRAG_API_BASE_URL || "";
    const base = (configuredBase || window.location.origin).replace(/\/+$/, "");

    window.harmonicRagApiUrl = (path) => {
        const normalizedPath = String(path).replace(/^\/+/, "");
        return `${base}/${normalizedPath}`;
    };
})();
