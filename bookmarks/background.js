// Background script receives messages from the popup and sends them to the API.

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message.action === 'createDID') {
        handleCreateDID(message.payload, message.apiUrl, message.collection, sendResponse);
        return true; // Keep the message channel open for async response
    }
});

async function handleCreateDID(payload, apiUrl, collection, sendResponse) {
    try {
        const requestBody = { payload: payload };
        if (collection) {
            requestBody.collection = collection;
        }

        const response = await fetch(apiUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(requestBody)
        });

        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`API returned ${response.status}: ${errorText}`);
        }

        const data = await response.json();
        sendResponse({ success: true, data: data });
    } catch (error) {
        console.error('Error creating DID:', error);
        sendResponse({ success: false, error: error.message });
    }
}
