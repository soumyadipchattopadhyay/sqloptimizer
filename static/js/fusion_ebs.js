document.addEventListener('DOMContentLoaded', () => {
    // Configure Marked to convert line breaks automatically
    marked.setOptions({
        gfm: true,
        breaks: true
    });

    // 1. Initialize CodeMirror Editor
    const editorTextarea = document.getElementById('sqlCodeEditor');
    const editor = CodeMirror.fromTextArea(editorTextarea, {
        mode: 'text/x-sql',
        lineNumbers: false,
        indentUnit: 4,
        matchBrackets: true
    });

    editor.setValue("select sysdate from dual");
    setTimeout(() => editor.refresh(), 100);
    window.addEventListener('resize', () => editor.refresh());

    // 2. Load Model & System Toggle
    const activeModel = localStorage.getItem('selected_ai_model') || 'gemini-2.5-flash';
    document.getElementById('activeModelDisplay').textContent = activeModel;

    const systemToggle = document.getElementById('systemToggle');
    const dialectBadge = document.getElementById('dialectBadge');

    function getSelectedSystem() { return systemToggle.checked ? 'Fusion' : 'EBS'; }
    function updateLabels() {
        document.getElementById('label-fusion').classList.toggle('active', systemToggle.checked);
        document.getElementById('label-ebs').classList.toggle('active', !systemToggle.checked);
        dialectBadge.textContent = systemToggle.checked ? 'ORACLE SQL (FUSION)' : 'ORACLE SQL (EBS R12)';
    }
    systemToggle.addEventListener('change', updateLabels);
    updateLabels();

    // 3. Status Bar Updates
    function updateStatusBar() {
        const cursor = editor.getCursor();
        document.getElementById('cursorPos').textContent = `Ln ${cursor.line + 1}, Col ${cursor.ch + 1}`;
        document.getElementById('lineCount').textContent = `${editor.lineCount()} line(s)`;
        const sel = editor.getSelection();
        document.getElementById('selectionStatus').textContent = `${sel.length > 0 ? sel.length : 0} selected`;
    }
    editor.on('cursorActivity', updateStatusBar);
    editor.on('change', updateStatusBar);
    updateStatusBar();

    // 4. Action API handler with Markdown Parsing
    async function executeApiAction(action, promptText = '') {
        const output = document.getElementById('explanationOutput');
        
        // Auto-expand panel if it was collapsed so user can see output
        document.getElementById('explanationContainer').classList.remove('collapsed');
        document.getElementById('toggleExplanationBtn').textContent = '▼';
        document.getElementById('bottomResizer').classList.remove('hidden');
        editor.refresh();

        output.innerHTML = '<p style="color:#EB8C00;">Processing request...</p>';

        try {
            const res = await fetch('/api/fusion-ebs/process', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    action: action,
                    prompt: promptText,
                    code: editor.getValue(),
                    system_type: getSelectedSystem(),
                    model: activeModel
                })
            });
            const data = await res.json();
            
            if (data.code) editor.setValue(data.code);

            // Parse Markdown returned by model into formatted HTML
            if (data.explanation) {
                output.innerHTML = marked.parse(data.explanation);
            }
        } catch (err) {
            output.innerHTML = `<p style="color:#A30000;">Connection Error: ${err.message}</p>`;
        }
    }

    // 5. Button Listeners
    document.getElementById('optimizeSqlBtn').addEventListener('click', () => executeApiAction('optimize'));
    document.getElementById('formatSqlBtn').addEventListener('click', () => executeApiAction('format'));
    document.getElementById('debugSqlBtn').addEventListener('click', () => executeApiAction('debug'));
    
    document.getElementById('copyCodeBtn').addEventListener('click', () => {
        navigator.clipboard.writeText(editor.getValue());
        document.getElementById('explanationOutput').innerHTML = '<p style="color:#2E7D32;">Code copied to clipboard.</p>';
    });
    
    document.getElementById('clearEditorBtn').addEventListener('click', () => {
        editor.setValue('');
        document.getElementById('explanationOutput').innerHTML = '<p class="placeholder-text">Editor cleared.</p>';
    });

    // 6. AI Generator Modal
    const modal = document.getElementById('aiGenModal');
    document.getElementById('openAiGenModalBtn').addEventListener('click', () => modal.style.display = 'flex');
    document.getElementById('closeAiGenModalBtn').addEventListener('click', () => modal.style.display = 'none');
    document.getElementById('cancelAiGenBtn').addEventListener('click', () => modal.style.display = 'none');
    
    document.getElementById('submitAiGenBtn').addEventListener('click', () => {
        const text = document.getElementById('aiPromptInput').value.trim();
        if (text) {
            modal.style.display = 'none';
            executeApiAction('generate', text);
        }
    });

    // 7. Chatbot Integration with Typing Animation
    document.getElementById('sendChatBtn').addEventListener('click', async () => {
        const input = document.getElementById('chatInput');
        const text = input.value.trim();
        if (!text) return;
        
        const chatBox = document.getElementById('chatMessages');
        const typingIndicator = document.getElementById('typingIndicator');
        
        // 7a. Display user message safely
        const safeUserText = text.replace(/</g, "&lt;").replace(/>/g, "&gt;");
        chatBox.insertAdjacentHTML('beforeend', `<div class="chat-bubble user">${safeUserText}</div>`);
        input.value = '';
        
        // 7b. Show typing indicator and move it to the bottom of the chat list
        typingIndicator.classList.add('active');
        chatBox.appendChild(typingIndicator);
        chatBox.scrollTop = chatBox.scrollHeight;

        try {
            const res = await fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    message: text, 
                    system_type: getSelectedSystem(),
                    current_code: editor.getValue(), 
                    model: activeModel
                })
            });
            const data = await res.json();
            const parsedBotReply = marked.parse(data.reply);
            
            // 7c. Hide indicator and show bot response
            typingIndicator.classList.remove('active');
            chatBox.insertAdjacentHTML('beforeend', `<div class="chat-bubble bot">${parsedBotReply}</div>`);
            chatBox.scrollTop = chatBox.scrollHeight;
        } catch (e) {
            // 7d. Handle errors and hide indicator
            typingIndicator.classList.remove('active');
            chatBox.insertAdjacentHTML('beforeend', `<div class="chat-bubble bot" style="color:#A30000;">Error reaching AI.</div>`);
            chatBox.scrollTop = chatBox.scrollHeight;
        }
    });

    // 8. Resizer (Sidebar Left/Right Drag)
    const sidebarResizer = document.getElementById('sidebarResizer');
    const sidebar = document.getElementById('chatbotSidebar');
    let isResizingSidebar = false;
    let startX, startWidth;

    sidebarResizer.addEventListener('mousedown', function(e) {
        isResizingSidebar = true;
        startX = e.clientX;
        startWidth = parseInt(document.defaultView.getComputedStyle(sidebar).width, 10);
        document.documentElement.style.cursor = 'ew-resize';
        sidebarResizer.classList.add('active');
        e.preventDefault();
    });

    document.addEventListener('mousemove', function(e) {
        if (isResizingSidebar) {
            const dx = e.clientX - startX;
            const newWidth = startWidth - dx;
            if (newWidth > 200 && newWidth < 800) {
                sidebar.style.width = `${newWidth}px`;
            }
        }
    });

    document.addEventListener('mouseup', function(e) {
        if (isResizingSidebar) {
            isResizingSidebar = false;
            document.documentElement.style.cursor = '';
            sidebarResizer.classList.remove('active');
            editor.refresh(); 
        }
    });

    // 9. Resizer (Explanation Panel Up/Down Drag)
    const bottomResizer = document.getElementById('bottomResizer');
    const expContainer = document.getElementById('explanationContainer');
    let isResizingBottom = false;
    let startY, startHeight;

    bottomResizer.addEventListener('mousedown', function(e) {
        isResizingBottom = true;
        startY = e.clientY;
        startHeight = parseInt(document.defaultView.getComputedStyle(expContainer).height, 10);
        document.documentElement.style.cursor = 'ns-resize';
        bottomResizer.classList.add('active');
        e.preventDefault();
    });

    document.addEventListener('mousemove', function(e) {
        if (isResizingBottom) {
            // Dragging UP makes Y smaller, so dy is negative. Height should increase.
            const dy = startY - e.clientY; 
            const newHeight = startHeight + dy;
            
            // Constrain heights
            if (newHeight > 50 && newHeight < 600) {
                expContainer.style.height = `${newHeight}px`;
            }
        }
    });

    document.addEventListener('mouseup', function(e) {
        if (isResizingBottom) {
            isResizingBottom = false;
            document.documentElement.style.cursor = '';
            bottomResizer.classList.remove('active');
            editor.refresh(); 
        }
    });

    // 10. Toggle Buttons (Chat & Explanation Panel)
    document.getElementById('toggleChatBtn').addEventListener('click', () => {
        sidebar.classList.toggle('hidden');
        sidebarResizer.classList.toggle('hidden');
        setTimeout(() => editor.refresh(), 50); 
    });

    document.getElementById('toggleExplanationBtn').addEventListener('click', (e) => {
        const btn = e.target;
        expContainer.classList.toggle('collapsed');
        
        if (expContainer.classList.contains('collapsed')) {
            btn.textContent = '▲';
            bottomResizer.classList.add('hidden');
        } else {
            btn.textContent = '▼';
            bottomResizer.classList.remove('hidden');
        }
        setTimeout(() => editor.refresh(), 50); 
    });
});