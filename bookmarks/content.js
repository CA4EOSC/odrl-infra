// Content script that extracts page details for JSON-LD.
// We also want to extract any existing JSON-LD if present.
function extractPageData() {
    const url = window.location.href;
    const title = document.title || 'Unknown Title';
    const descriptionMeta = document.querySelector('meta[name="description"]');
    const description = descriptionMeta ? descriptionMeta.getAttribute('content') : '';

    // Look for existing JSON-LD
    let existingJsonLd = null;
    const scriptTags = document.querySelectorAll('script[type="application/ld+json"]');
    if (scriptTags.length > 0) {
        try {
            existingJsonLd = JSON.parse(scriptTags[0].textContent);
        } catch (e) {
            console.warn("Found JSON-LD but failed to parse it.", e);
        }
    }

    const payload = {
        "@context": "https://schema.org",
        "@type": "WebPage",
        "url": url,
        "name": title,
        "description": description,
        "dateCreated": new Date().toISOString()
    };

    if (existingJsonLd) {
        payload["schema"] = existingJsonLd;
    }

    return payload;
}

// When injected, run extraction and return
extractPageData();
