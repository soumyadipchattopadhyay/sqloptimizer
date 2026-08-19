document.addEventListener('DOMContentLoaded', () => {
    
    // --- 1. Global State ---
    let dbSessionId = null;

    // --- 2. CodeMirror Setup ---
    const editorTextarea = document.getElementById('sqlCodeEditor');
    const editor = CodeMirror.fromTextArea(editorTextarea, {
        mode: 'text/x-sql',
        lineNumbers: true,
        indentUnit: 4,
        matchBrackets: true
    });

    // --- 3. Database Connection Logic ---
    document.getElementById('connectBtn').addEventListener('click', async () => {
        const btn = document.getElementById('connectBtn');
        const errorDiv = document.getElementById('loginError');
        
        const payload = {
            username: document.getElementById('dbUser').value.trim(),
            password: document.getElementById('dbPassword').value.trim(),
            host: document.getElementById('dbHost').value.trim(),
            port: parseInt(document.getElementById('dbPort').value) || 1521,
            service_name: document.getElementById('dbService').value.trim()
        };

        if (!payload.username || !payload.password || !payload.host || !payload.service_name) {
            errorDiv.textContent = "Please fill in all fields.";
            return;
        }

        btn.textContent = "Connecting...";
        btn.disabled = true;
        errorDiv.textContent = "";

        try {
            const response = await fetch('/api/db/connect', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const data = await response.json();

            if (data.success) {
                dbSessionId = data.session_id;
                
                // Switch UI
                document.getElementById('loginOverlay').classList.add('hidden');
                document.getElementById('workspaceContainer').classList.remove('hidden');
                
                // Update Badge
                const badge = document.getElementById('connectionStatus');
                badge.textContent = `Connected: ${payload.username}@${payload.service_name}`;
                badge.className = "status-badge connected";
                
                // Refresh editor so it renders correctly after being unhidden
                setTimeout(() => {
                    editor.refresh();
                    editor.setValue("-- Connected successfully.\nSELECT * FROM DUAL;");
                }, 100);
            } else {
                errorDiv.textContent = "Error: " + data.error;
            }
        } catch (err) {
            errorDiv.textContent = "Connection failed. Is the server running?";
        } finally {
            btn.textContent = "Connect Database";
            btn.disabled = false;
        }
    });

    // --- 4. Workspace Resizer Logic ---
    const resizer = document.getElementById('horizontalResizer');
    const topPane = document.getElementById('editorPane');
    const bottomPane = document.getElementById('resultsPane');
    let isResizing = false;

    resizer.addEventListener('mousedown', (e) => {
        isResizing = true;
        resizer.classList.add('active');
        document.body.style.cursor = 'ns-resize';
    });

    document.addEventListener('mousemove', (e) => {
        if (!isResizing) return;
        const container = document.getElementById('workspaceContainer');
        const containerHeight = container.clientHeight;
        const offsetTop = container.getBoundingClientRect().top;
        
        let newTopHeight = ((e.clientY - offsetTop) / containerHeight) * 100;
        
        // Boundaries
        if (newTopHeight > 15 && newTopHeight < 85) {
            topPane.style.height = `${newTopHeight}%`;
            bottomPane.style.height = `${100 - newTopHeight}%`;
        }
    });

    document.addEventListener('mouseup', () => {
        if (isResizing) {
            isResizing = false;
            resizer.classList.remove('active');
            document.body.style.cursor = '';
            editor.refresh();
        }
    });

    // --- 5. Tab Switching Logic ---
    const tabs = document.querySelectorAll('.tab');
    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            // Remove active classes
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
            
            // Add active to clicked
            tab.classList.add('active');
            document.getElementById(tab.getAttribute('data-target')).classList.add('active');
        });
    });

    // --- 6. Execute Query ---
    document.getElementById('runQueryBtn').addEventListener('click', async () => {
        const query = editor.getSelection() || editor.getValue();
        if (!query.trim()) return;

        // Ensure Results tab is active
        tabs[0].click(); 
        document.getElementById('resultsMessage').textContent = "Executing query...";
        document.getElementById('tableHeaders').innerHTML = "";
        document.getElementById('tableBody').innerHTML = "";
        document.getElementById('queryTime').textContent = "";

        const startTime = performance.now();

        try {
            const res = await fetch('/api/db/execute', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ session_id: dbSessionId, query: query })
            });
            const data = await res.json();
            const timeTaken = ((performance.now() - startTime) / 1000).toFixed(2);

            if (data.success) {
                document.getElementById('resultsMessage').style.display = 'none';
                document.getElementById('queryTime').textContent = `${data.rows.length} rows in ${timeTaken}s`;
                
                // Build Headers
                let headHtml = data.columns.map(col => `<th>${col}</th>`).join("");
                document.getElementById('tableHeaders').innerHTML = headHtml;
                
                // Build Rows
                let bodyHtml = data.rows.map(row => {
                    return `<tr>${row.map(cell => `<td>${cell !== null ? cell : '<em>null</em>'}</td>`).join("")}</tr>`;
                }).join("");
                document.getElementById('tableBody').innerHTML = bodyHtml;
            } else {
                document.getElementById('resultsMessage').style.display = 'block';
                document.getElementById('resultsMessage').innerHTML = `<span style="color:#A30000;">Error: ${data.error}</span>`;
            }
        } catch (err) {
            document.getElementById('resultsMessage').textContent = "Server connection failed.";
        }
    });

    // --- 7. Generate Explain Plan ---
    document.getElementById('explainPlanBtn').addEventListener('click', async () => {
        const query = editor.getSelection() || editor.getValue();
        if (!query.trim()) return;

        // Switch to Explain tab
        tabs[1].click();
        const explainOutput = document.getElementById('explainPlanOutput');
        explainOutput.textContent = "Generating plan...";

        try {
            const res = await fetch('/api/db/explain', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ session_id: dbSessionId, query: query })
            });
            const data = await res.json();

            if (data.success) {
                explainOutput.textContent = data.plan;
            } else {
                explainOutput.textContent = "Error: " + data.error;
            }
        } catch (err) {
            explainOutput.textContent = "Failed to fetch explain plan.";
        }
    });

    // --- 8. Clear Button ---
    document.getElementById('clearBtn').addEventListener('click', () => {
        editor.setValue('');
    });
});