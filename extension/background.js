const API_BASE = 'https://memoir-ai-backend.fly.dev/api/v1';

chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: 'memoir-save-selection',
    title: 'Memoir에 저장',
    contexts: ['selection'],
  });
  chrome.contextMenus.create({
    id: 'memoir-save-page',
    title: '이 페이지를 Memoir에 저장',
    contexts: ['page'],
  });
});

async function getToken() {
  const { access_token } = await chrome.storage.local.get(['access_token']);
  return access_token;
}

async function saveMemory(payload) {
  const token = await getToken();
  if (!token) {
    console.warn('Memoir: 로그인 필요');
    return;
  }

  try {
    const res = await fetch(`${API_BASE}/memories`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(payload),
    });

    if (res.ok) {
      chrome.action.setBadgeText({ text: '✓' });
      chrome.action.setBadgeBackgroundColor({ color: '#34d399' });
      setTimeout(() => chrome.action.setBadgeText({ text: '' }), 3000);
    }
  } catch (err) {
    console.error('Memoir 저장 실패:', err);
  }
}

chrome.contextMenus.onClicked.addListener(async (info, tab) => {
  if (info.menuItemId === 'memoir-save-selection') {
    await saveMemory({
      source_type: 'WEB',
      url: tab.url,
      memo: info.selectionText.slice(0, 500),
    });
  } else if (info.menuItemId === 'memoir-save-page') {
    await saveMemory({
      source_type: 'WEB',
      url: tab.url,
      memo: tab.title || 'Saved from Memoir Scout',
    });
  }
});

// Ctrl+Shift+M 단축키
chrome.commands.onCommand.addListener(async (command) => {
  if (command === 'save-current-page') {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (tab) {
      await saveMemory({
        source_type: 'WEB',
        url: tab.url,
        memo: tab.title || 'Saved from Memoir Scout',
      });
    }
  }
});
