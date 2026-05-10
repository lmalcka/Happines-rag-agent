// --- API Interaction Logic ---
async function uploadFile() {
    const statusText = document.getElementById('uploadStatus');
    const fileInput = document.getElementById('fileInput');

    if (fileInput.files.length === 0) {
        statusText.innerText = "Please select a file first.";
        return;
    }

    // Capture the file object so we can pass its name to the tracker
    const file = fileInput.files[0];

    statusText.innerText = "Uploading and learning...";
    const formData = new FormData();
    formData.append("file", file);

    try {
        const response = await fetch('/upload', { method: 'POST', body: formData });
        const result = await response.json();
        statusText.innerText = result.message || result.error;

        // 🚀 WAKE UP THE TRACKER UI HERE!
        // If the upload to S3 was successful, start tracking the file's progress
        if (response.ok) {
            trackFileProgress(result.filename);
        }

    } catch (e) {
        statusText.innerText = "Connection error.";
    }
}

async function askQuestion() {
    const question = document.getElementById('questionInput').value;
    const answerBox = document.getElementById('answerOutput');

    if (!question) return;

    answerBox.innerHTML = "<em>Thinking...</em>";

    try {
        const response = await fetch('/ask', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ question: question })
        });
        const result = await response.json();
        answerBox.innerText = result.answer || result.error;
    } catch (e) {
        answerBox.innerText = "Connection error.";
    }
}

// --- status bar that appears after an upload and updates automatically every 2 seconds until the "Success" message is received. ---
function trackFileProgress(filename) {
    const container = document.getElementById('status-container');
    const msgBox = document.getElementById('status-message');
    const nameBox = document.getElementById('tracking-filename');

    container.style.display = 'block';
    nameBox.innerText = filename;

    // Poll the API every 2 seconds
    const interval = setInterval(async () => {
        try {
            const response = await fetch(`/api/status/${encodeURIComponent(filename)}`);
            const data = await response.json();

            msgBox.innerText = data.status;

            // Stop polling if we see "Success" or "Error"
            if (data.status.includes("Success") || data.status.includes("ERROR")) {
                clearInterval(interval);

                // Optional: Hide tracker after 10 seconds of success
                if(data.status.includes("Success")) {
                    setTimeout(() => { container.style.display = 'none'; }, 10000);
                }
            }
        } catch (err) {
            console.error("Tracking error:", err);
        }
    }, 2000);
}


// --- Pastorale Leaf Animation Logic ---
function createLeaf() {
    const leaf = document.createElement('div');
    // Using different leaf emojis for variety
    const leaves = ['🍃', '🍂', '🌿'];
    leaf.innerText = leaves[Math.floor(Math.random() * leaves.length)];
    leaf.classList.add('leaf');

    // Randomize starting position across the screen width
    leaf.style.left = Math.random() * 100 + 'vw';

    // Randomize fall duration between 5s and 15s for the "dangling" effect
    const fallDuration = Math.random() * 10 + 5;
    leaf.style.animationDuration = fallDuration + 's';

    // Randomize size slightly for depth
    leaf.style.fontSize = (Math.random() * 15 + 15) + 'px';

    document.body.appendChild(leaf);

    // Clean up the leaf after it falls off screen to save memory
    setTimeout(() => {
        leaf.remove();
    }, fallDuration * 1000);
}

// Drop a new leaf every 800 milliseconds
setInterval(createLeaf, 800);