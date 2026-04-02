let schematicCount = 1;

function addSchematic() {
    const container = document.getElementById('schematics-container');
    const row = document.createElement('div');
    row.className = 'schematic-row';
    row.id = `schematic-${schematicCount}`;

    row.innerHTML = `
    <input type="text" placeholder="Enter schematic URL (e.g., chemistry_medpack_enhance_poison_c)" class="schematic-url">
    <input type="number" placeholder="Qty" min="1" value="1" class="schematic-qty" style="width: 80px;">
    <button class="remove-btn" onclick="removeSchematic(${schematicCount})">Remove</button>
  `;

    container.appendChild(row);
    schematicCount++;
}

function removeSchematic(id) {
    const row = document.getElementById(`schematic-${id}`);
    if (row) {
        row.remove();
    }
}

function getSchematicUrls() {
    const urls = [];
    document.querySelectorAll('.schematic-row').forEach(row => {
        const urlInput = row.querySelector('.schematic-url');
        const qtyInput = row.querySelector('.schematic-qty');

        const url = urlInput.value.trim();
        const quantity = parseInt(qtyInput.value) || 1;

        if (url) {
            // Ensure it's a full URL
            let fullUrl = url;
            if (!fullUrl.startsWith('http')) {
                fullUrl = `https://www.galaxyharvester.net/schematics.py/${url}`;
            }
            urls.push({ url: fullUrl, quantity });
        }
    });

    return urls;
}

async function scrapeAll() {
    const urls = getSchematicUrls();

    if (urls.length === 0) {
        showMessage('Please enter at least one schematic URL', 'error');
        return;
    }

    const loading = document.getElementById('loading');
    const resultArea = document.getElementById('result');
    const messageContainer = document.getElementById('message-container');

    loading.classList.add('active');
    resultArea.value = 'Scraping...';
    messageContainer.innerHTML = '';

    try {
        // Check if API is available
        if (!window.api || !window.api.scrapeSchematics) {
            throw new Error('Electron API not available. Please restart the application.');
        }

        const results = await window.api.scrapeSchematics(urls);

        let fullOutput = '';
        let grandTotalResources = {};
        let resourceNames = new Set();

        results.forEach((result, index) => {
            if (result.error) {
                fullOutput += `❌ Error scraping ${result.url}: ${result.error}\n\n`;
            } else {
                fullOutput += result.notecard + '\n\n';

                // Accumulate grand total
                Object.entries(result.ingredients).forEach(([resource, qty]) => {
                    grandTotalResources[resource] = (grandTotalResources[resource] || 0) + qty;
                    resourceNames.add(resource);
                });
            }
        });

        // Add grand total
        if (Object.keys(grandTotalResources).length > 0) {
            fullOutput += '\n' + '='.repeat(50) + '\n';
            fullOutput += 'GRAND TOTAL - ALL RESOURCES NEEDED\n';
            fullOutput += '='.repeat(50) + '\n';

            const sorted = Object.entries(grandTotalResources).sort((a, b) => a[0].localeCompare(b[0]));
            sorted.forEach(([resource, qty]) => {
                fullOutput += `${resource}: ${qty}\n`;
            });

            // Add resources needed list
            fullOutput += '\n' + '-'.repeat(50) + '\n';
            fullOutput += 'RESOURCES NEEDED:\n';
            fullOutput += '-'.repeat(50) + '\n';

            const resourceList = Array.from(resourceNames).sort();
            resourceList.forEach(resource => {
                fullOutput += `${resource}\n`;
            });
        }

        resultArea.value = fullOutput;
        showMessage('✅ Scraping completed successfully!', 'success');

        // Update Discord format
        updateDiscordFormat();

    } catch (error) {
        resultArea.value = `Error: ${error.message}`;
        showMessage(`❌ Error: ${error.message}`, 'error');
    } finally {
        loading.classList.remove('active');
    }
}

function showMessage(message, type) {
    const container = document.getElementById('message-container');
    const div = document.createElement('div');
    div.className = type;
    div.textContent = message;
    container.innerHTML = '';
    container.appendChild(div);

    if (type === 'success') {
        setTimeout(() => {
            div.remove();
        }, 5000);
    }
}

function downloadResults() {
    const resultArea = document.getElementById('result');
    const text = resultArea.value;

    if (!text) {
        showMessage('No results to download', 'error');
        return;
    }

    const blob = new Blob([text], { type: 'text/plain' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'galaxy_harvester_resources.txt';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
}

function copyToClipboard() {
    const resultArea = document.getElementById('result');
    const text = resultArea.value;

    if (!text) {
        showMessage('No results to copy', 'error');
        return;
    }

    navigator.clipboard.writeText(text).then(() => {
        showMessage('✅ Copied to clipboard!', 'success');
    }).catch(err => {
        showMessage('Failed to copy to clipboard', 'error');
    });
}

function formatForDiscord(text, charLimit) {
    const lines = text.split('\n');
    const messages = [];
    let currentMessage = '```\n';

    for (const line of lines) {
        const potentialMessage = currentMessage + line + '\n';

        if (potentialMessage.length >= charLimit) {
            if (currentMessage === '```\n') {
                // Single line is too long, split it
                currentMessage += line.substring(0, charLimit - 7) + '\n```';
            } else {
                currentMessage += '```';
            }
            messages.push(currentMessage);
            currentMessage = '```\n' + line + '\n';
        } else {
            currentMessage += line + '\n';
        }
    }

    if (currentMessage !== '```\n') {
        currentMessage += '```';
        messages.push(currentMessage);
    }

    return messages;
}

function getDiscordFormat() {
    const selectedFormat = document.querySelector('input[name="discord-format"]:checked').value;
    const resultArea = document.getElementById('result');
    const text = resultArea.value;

    if (!text) {
        return 'No results to format';
    }

    const charLimit = selectedFormat === 'with-nitro' ? 4000 : 2000;
    const messages = formatForDiscord(text, charLimit - 10); // -10 to account for code block markers

    return messages.join('\n\n--- Message Split ---\n\n');
}

function updateDiscordFormat() {
    const discordResult = document.getElementById('discord-result');
    discordResult.value = getDiscordFormat();
}

function copyDiscordFormat() {
    const discordResult = document.getElementById('discord-result');
    const text = discordResult.value;

    if (!text || text === 'No results to format') {
        showMessage('No Discord format to copy. Scrape first!', 'error');
        return;
    }

    navigator.clipboard.writeText(text).then(() => {
        showMessage('✅ Discord format copied to clipboard!', 'success');
    }).catch(err => {
        showMessage('Failed to copy to clipboard', 'error');
    });
}

// Initialize with one schematic row on load
window.addEventListener('DOMContentLoaded', () => {
    addSchematic();
});
