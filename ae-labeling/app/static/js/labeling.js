// Function that renders Markdown then highlights context strings
function highlightContextsWithMarkdown(text, contexts) {
    const container = document.getElementById('text-container');
    
    // Parse Markdown to HTML using marked.js
    let htmlContent = marked.parse(text);
    
    if (contexts && contexts.length > 0) {
        // For each context string, find and wrap it with <mark> tags
        contexts.forEach(context => {
            const searchText = context.trim();
            
            if (searchText) {
                // Escape special regex characters in the search text
                const escapedText = escapeRegExp(searchText);
                
                // Create a case-insensitive global regex to find all occurrences
                const regex = new RegExp(escapedText, 'gi');
                
                // Replace with highlighted version
                htmlContent = htmlContent.replace(regex, function(match) {
                    return `<mark class="context-highlight">${match}</mark>`;
                });
            }
        });
    }
    
    container.innerHTML = htmlContent;
}

// Helper to escape special regex characters
function escapeRegExp(string) {
    return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

// Keep the old function for backward compatibility if needed
function highlightContexts(text, contexts) {
    console.warn('highlightContexts is deprecated. Use highlightContextsWithMarkdown instead.');
    highlightContextsWithMarkdown(text, contexts);
}

function submitForm() {
    const form = document.getElementById('label-form');
    form.submit();
}


