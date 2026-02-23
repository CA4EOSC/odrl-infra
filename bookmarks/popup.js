document.addEventListener('DOMContentLoaded', () => {
    const bookmarkBtn = document.getElementById('bookmarkBtn');
    const apiUrlInput = document.getElementById('apiUrl');
    const statusDiv = document.getElementById('status');

    // Load saved API URL if any
    chrome.storage.local.get(['apiUrl'], (result) => {
        if (result.apiUrl) {
            apiUrlInput.value = result.apiUrl;
        }
    });

    bookmarkBtn.addEventListener('click', async () => {
        let apiUrl = apiUrlInput.value.trim();
        if (!apiUrl) {
            apiUrl = 'https://odrl.dev.codata.org/did/create';
            apiUrlInput.value = apiUrl;
        }

        // Save API URL for future use
        chrome.storage.local.set({ apiUrl: apiUrl });

        bookmarkBtn.disabled = true;
        bookmarkBtn.textContent = 'Processing...';
        hideStatus();

        try {
            const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

            // Execute content script to get page details
            const injectionResults = await chrome.scripting.executeScript({
                target: { tabId: tab.id },
                files: ['content.js']
            });

            const payload = injectionResults[0].result;

            // Send payload to background script to create DID
            chrome.runtime.sendMessage(
                { action: 'createDID', payload: payload, apiUrl: apiUrl },
                (response) => {
                    bookmarkBtn.disabled = false;
                    bookmarkBtn.textContent = 'Bookmark Page';

                    if (response && response.success) {
                        showStatus(`Success! DID created:<br><small>${response.data.did}</small>`, 'success');
                    } else {
                        const errorMsg = response ? response.error : chrome.runtime.lastError?.message || 'Unknown error';
                        showStatus(`Error: ${errorMsg}`, 'error');
                    }
                }
            );
        } catch (err) {
            bookmarkBtn.disabled = false;
            bookmarkBtn.textContent = 'Bookmark Page';
            showStatus(`Error: ${err.message}`, 'error');
        }
    });

    function showStatus(message, type) {
        statusDiv.innerHTML = message;
        statusDiv.className = `status-${type}`;
    }

    function hideStatus() {
        statusDiv.className = 'status-hidden';
        statusDiv.innerHTML = '';
    }
});
