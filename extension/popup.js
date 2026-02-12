const API_BASE = 'https://memoir-ai-backend.fly.dev/api/v1';

document.addEventListener('DOMContentLoaded', async () => {
  const titleEl = document.getElementById('title');
  const urlEl = document.getElementById('url');
  const saveBtn = document.getElementById('saveBtn');
  const statusEl = document.getElementById('status');
  const loginSection = document.getElementById('loginSection');
  const mainSection = document.getElementById('mainSection');
  const logoutBtn = document.getElementById('logoutBtn');

  // 저장된 토큰 확인
  const stored = await chrome.storage.local.get(['auth_token', 'user_email']);

  if (!stored.auth_token) {
    showLogin();
    return;
  }

  showMain(stored.user_email);

  // 현재 탭 정보 가져오기
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

  if (tab) {
    titleEl.textContent = tab.title || 'No Title';
    urlEl.textContent = tab.url || 'No URL';
  }

  saveBtn.addEventListener('click', async () => {
    saveBtn.disabled = true;
    saveBtn.textContent = '저장 중...';
    statusEl.textContent = '';
    statusEl.className = '';

    try {
      const response = await fetch(`${API_BASE}/memories`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${stored.auth_token}`
        },
        body: JSON.stringify({
          source_type: 'WEB',
          url: tab.url,
          memo: tab.title || 'Saved from Chrome Extension'
        })
      });

      if (response.status === 401) {
        await chrome.storage.local.remove(['auth_token', 'user_email']);
        showLogin();
        return;
      }

      if (!response.ok) {
        throw new Error(`Server error: ${response.status}`);
      }

      statusEl.textContent = '저장 완료!';
      statusEl.className = 'success';
      saveBtn.textContent = '저장됨';
    } catch (error) {
      console.error(error);
      statusEl.textContent = '저장 실패. 다시 시도해주세요.';
      statusEl.className = 'error';
      saveBtn.disabled = false;
      saveBtn.textContent = '다시 시도';
    }
  });

  logoutBtn.addEventListener('click', async () => {
    await chrome.storage.local.remove(['auth_token', 'user_email']);
    showLogin();
  });

  // 로그인 폼 처리
  document.getElementById('loginForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;
    const loginStatus = document.getElementById('loginStatus');

    loginStatus.textContent = '로그인 중...';
    loginStatus.className = '';

    try {
      const res = await fetch(`${API_BASE}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
      });

      if (!res.ok) {
        throw new Error('로그인 실패');
      }

      const data = await res.json();
      await chrome.storage.local.set({
        auth_token: data.access_token,
        user_email: email
      });

      showMain(email);
    } catch (error) {
      loginStatus.textContent = '로그인 실패. 이메일/비밀번호를 확인해주세요.';
      loginStatus.className = 'error';
    }
  });

  function showLogin() {
    if (loginSection) loginSection.style.display = 'block';
    if (mainSection) mainSection.style.display = 'none';
  }

  function showMain(email) {
    if (loginSection) loginSection.style.display = 'none';
    if (mainSection) mainSection.style.display = 'block';
    const userEl = document.getElementById('userEmail');
    if (userEl && email) userEl.textContent = email;
  }
});
