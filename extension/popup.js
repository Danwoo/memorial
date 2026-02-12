const API_BASE = 'https://memoir-ai-backend.fly.dev/api/v1';
const SUPABASE_URL = 'https://otzqnucgfrlbqyyhksgo.supabase.co';
const SUPABASE_ANON_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im90enFudWNnZnJsYnF5eWhrc2dvIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Njk3NjE5NjQsImV4cCI6MjA4NTMzNzk2NH0.ewsd_uZl7hkjdH9Np-P03J0R4qJT6-H1natMKUIy8zE';

document.addEventListener('DOMContentLoaded', async () => {
  const titleEl = document.getElementById('title');
  const urlEl = document.getElementById('url');
  const saveBtn = document.getElementById('saveBtn');
  const statusEl = document.getElementById('status');
  const loginSection = document.getElementById('loginSection');
  const mainSection = document.getElementById('mainSection');
  const logoutBtn = document.getElementById('logoutBtn');
  const googleLoginBtn = document.getElementById('googleLoginBtn');

  const stored = await chrome.storage.local.get(['access_token', 'refresh_token', 'user_email']);

  if (!stored.access_token) {
    showLogin();
  } else {
    await initMain(stored.access_token, stored.user_email);
  }

  // Google OAuth 로그인
  googleLoginBtn.addEventListener('click', async () => {
    googleLoginBtn.disabled = true;
    googleLoginBtn.textContent = '로그인 중...';

    try {
      const redirectUrl = chrome.identity.getRedirectURL();
      const authUrl = `${SUPABASE_URL}/auth/v1/authorize?provider=google&redirect_to=${encodeURIComponent(redirectUrl)}`;

      const responseUrl = await chrome.identity.launchWebAuthFlow({
        url: authUrl,
        interactive: true
      });

      // URL fragment에서 토큰 추출 (#access_token=...&refresh_token=...)
      const hashParams = new URLSearchParams(responseUrl.split('#')[1]);
      const accessToken = hashParams.get('access_token');
      const refreshToken = hashParams.get('refresh_token');

      if (!accessToken) {
        throw new Error('토큰을 받지 못했습니다');
      }

      // 사용자 정보 가져오기
      const userRes = await fetch(`${SUPABASE_URL}/auth/v1/user`, {
        headers: {
          'Authorization': `Bearer ${accessToken}`,
          'apikey': SUPABASE_ANON_KEY
        }
      });
      const userData = await userRes.json();
      const email = userData.email || 'User';

      await chrome.storage.local.set({
        access_token: accessToken,
        refresh_token: refreshToken,
        user_email: email
      });

      await initMain(accessToken, email);
    } catch (error) {
      console.error('OAuth error:', error);
      document.getElementById('loginStatus').textContent = '로그인 실패. 다시 시도해주세요.';
      document.getElementById('loginStatus').className = 'error';
      googleLoginBtn.disabled = false;
      googleLoginBtn.textContent = 'Google로 로그인';
    }
  });

  // 로그아웃
  logoutBtn.addEventListener('click', async () => {
    await chrome.storage.local.remove(['access_token', 'refresh_token', 'user_email']);
    showLogin();
  });

  async function initMain(token, email) {
    showMain(email);

    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (tab) {
      titleEl.textContent = tab.title || 'No Title';
      urlEl.textContent = tab.url || 'No URL';
    }

    saveBtn.onclick = async () => {
      saveBtn.disabled = true;
      saveBtn.textContent = '저장 중...';
      statusEl.textContent = '';
      statusEl.className = '';

      try {
        const response = await fetch(`${API_BASE}/memories`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
          },
          body: JSON.stringify({
            source_type: 'WEB',
            url: tab.url,
            memo: tab.title || 'Saved from Memoir Scout'
          })
        });

        if (response.status === 401) {
          await chrome.storage.local.remove(['access_token', 'refresh_token', 'user_email']);
          showLogin();
          return;
        }

        if (!response.ok) throw new Error(`Error: ${response.status}`);

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
    };
  }

  function showLogin() {
    loginSection.style.display = 'block';
    mainSection.style.display = 'none';
    googleLoginBtn.disabled = false;
    googleLoginBtn.textContent = 'Google로 로그인';
  }

  function showMain(email) {
    loginSection.style.display = 'none';
    mainSection.style.display = 'block';
    document.getElementById('userEmail').textContent = email || '';
  }
});
