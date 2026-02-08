document.addEventListener('DOMContentLoaded', async () => {
    const titleEl = document.getElementById('title');
    const urlEl = document.getElementById('url');
    const saveBtn = document.getElementById('saveBtn');
    const statusEl = document.getElementById('status');
  
    // Get current tab info
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    
    if (tab) {
      titleEl.textContent = tab.title || 'No Title';
      urlEl.textContent = tab.url || 'No URL';
    }
  
    saveBtn.addEventListener('click', async () => {
      saveBtn.disabled = true;
      saveBtn.textContent = 'Saving...';
      statusEl.textContent = '';
      statusEl.className = '';
  
      try {
        const response = await fetch('http://localhost:8000/api/v1/memories', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            source_type: 'WEB',
            url: tab.url,
            memo: "Saved from Chrome Extension"
          })
        });
  
        if (!response.ok) {
          throw new Error('Server error');
        }
  
        const result = await response.json();
        statusEl.textContent = '✅ Saved!';
        statusEl.className = 'success';
        saveBtn.textContent = 'Saved';
      } catch (error) {
        console.error(error);
        statusEl.textContent = '❌ Failed to save. Is Backend running?';
        statusEl.className = 'error';
        saveBtn.disabled = false;
        saveBtn.textContent = 'Retry Save';
      }
    });
  });
