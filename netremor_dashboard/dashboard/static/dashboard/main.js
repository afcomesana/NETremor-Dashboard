const normalizeText = text => text.toLowerCase()
    .trim()                                            // remove blank spaces in edges
    .normalize("NFKD").replace(/[\u0300-\u036f]/g, "") // replace accents and weird stuff like ñ or ç
    .replace(/[^a-z0-9\ ]/g, "")                       // remove strange characters