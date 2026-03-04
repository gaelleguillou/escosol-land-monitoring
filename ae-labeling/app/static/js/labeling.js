function highlightContexts(text, contexts) {
    const container = document.getElementById('text-container');
    if (!container || !contexts || contexts.length === 0) {
        container.textContent = text;
        return;
    }

    // Sort contexts by length (longest first) to avoid partial replacements
    const sortedContexts = contexts.sort((a, b) => b.length - a.length);
    
    let highlightedText = text;
    
    sortedContexts.forEach(context => {
        // Escape special regex characters
        const escapedContext = context.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        // Create Regex with global flag but case sensitive
        // We use a lookahead to avoid overlapping replacements issues in simple JS
        const regex = new RegExp(escapedContext, 'g');
        
        highlightedText = highlightedText.replace(regex, match => {
            console.log("Match found")
            return `<span class="highlight">${match}</span>`;
        });
    });

     // Convert newlines to <br> tags after highlighting
    highlightedText = highlightedText.replace(/\n/g, '<br>');

    container.innerHTML = highlightedText;
}

function submitForm() {
    const form = document.getElementById('label-form');
    form.submit();
}
