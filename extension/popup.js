const API_BASE = 'https://memoir-ai-backend.fly.dev/api/v1';
const SUPABASE_URL = 'https://otzqnucgfrlbqyyhksgo.supabase.co';
const SUPABASE_ANON_KEY =
  'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im90enFudWNnZnJsYnF5eWhrc2dvIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Njk3NjE5NjQsImV4cCI6MjA4NTMzNzk2NH0.ewsd_uZl7hkjdH9Np-P03J0R4qJT6-H1natMKUIy8zE';

// --- 토큰 관리 ---

async function refreshToken() {
  const { refresh_token } = await chrome.storage.local.get(['refresh_token']);
  if (!refresh_token) return null;

  try {
    const res = await fetch(`${SUPABASE_URL}/auth/v1/token?grant_type=refresh_token`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', apikey: SUPABASE_ANON_KEY },
      body: JSON.stringify({ refresh_token }),
    });
    if (!res.ok) return null;

    const data = await res.json();
    await chrome.storage.local.set({
      access_token: data.access_token,
      refresh_token: data.refresh_token,
    });
    return data.access_token;
  } catch {
    return null;
  }
}

async function apiFetch(path, options = {}) {
  const { access_token } = await chrome.storage.local.get(['access_token']);
  if (!access_token) throw new Error('NO_TOKEN');

  const headers = { 'Content-Type': 'application/json', Authorization: `Bearer ${access_token}`, ...options.headers };
  let res = await fetch(`${API_BASE}${path}`, { ...options, headers });

  // 401 → 토큰 갱신 후 재시도
  if (res.status === 401) {
    const newToken = await refreshToken();
    if (!newToken) throw new Error('AUTH_EXPIRED');
    headers.Authorization = `Bearer ${newToken}`;
    res = await fetch(`${API_BASE}${path}`, { ...options, headers });
  }
  if (!res.ok) throw new Error(`API_ERROR_${res.status}`);
  return res.json();
}

// --- 본문 추출 ---

async function extractPageContent(tabId) {
  try {
    const results = await chrome.scripting.executeScript({
      target: { tabId },
      files: ['content.js'],
    });
    return results?.[0]?.result || '';
  } catch {
    return '';
  }
}

// --- 오늘 저장 카운트 ---

async function getTodayCount() {
  const today = new Date().toDateString();
  const { save_count, save_date } = await chrome.storage.local.get(['save_count', 'save_date']);
  if (save_date === today) return save_count || 0;
  return 0;
}

async function incrementTodayCount() {
  const today = new Date().toDateString();
  const count = (await getTodayCount()) + 1;
  await chrome.storage.local.set({ save_count: count, save_date: today });
  return count;
}

// --- UI 헬퍼 ---

function $(id) { return document.getElementById(id); }

function showLogin() {
  $('loginSection').style.display = 'block';
  $('mainSection').style.display = 'none';
  $('googleLoginBtn').disabled = false;
  $('googleLoginBtn').textContent = 'Google로 로그인';
}

function showMain(email) {
  $('loginSection').style.display = 'none';
  $('mainSection').style.display = 'block';
  $('userEmail').textContent = email || '';
  $('saveArea').style.display = 'block';
  $('successArea').style.display = 'none';
  $('status').textContent = '';
  $('status').className = '';
}

function showSuccess(count) {
  $('saveArea').style.display = 'none';
  $('successArea').style.display = 'block';
  $('todayCount').textContent = `오늘 ${count}개 저장됨`;
  $('status').textContent = '';

  // 3초 후 자동 닫기
  setTimeout(() => window.close(), 3000);
}

function showError(message) {
  $('status').textContent = message;
  $('status').className = 'error';
  $('saveBtn').disabled = false;
  $('saveBtn').textContent = '다시 시도';
}

// --- 메인 ---

document.addEventListener('DOMContentLoaded', async () => {
  const stored = await chrome.storage.local.get(['access_token', 'refresh_token', 'user_email']);

  if (!stored.access_token) {
    showLogin();
  } else {
    await initMain(stored.user_email);
  }

  // Google OAuth
  $('googleLoginBtn').addEventListener('click', async () => {
    $('googleLoginBtn').disabled = true;
    $('googleLoginBtn').textContent = '로그인 중...';

    try {
      const redirectUrl = chrome.identity.getRedirectURL();
      const authUrl = `${SUPABASE_URL}/auth/v1/authorize?provider=google&redirect_to=${encodeURIComponent(redirectUrl)}`;

      const responseUrl = await chrome.identity.launchWebAuthFlow({ url: authUrl, interactive: true });
      const hashParams = new URLSearchParams(responseUrl.split('#')[1]);
      const accessToken = hashParams.get('access_token');
      const refreshTokenVal = hashParams.get('refresh_token');

      if (!accessToken) throw new Error('토큰을 받지 못했습니다');

      const userRes = await fetch(`${SUPABASE_URL}/auth/v1/user`, {
        headers: { Authorization: `Bearer ${accessToken}`, apikey: SUPABASE_ANON_KEY },
      });
      const userData = await userRes.json();
      const email = userData.email || 'User';

      await chrome.storage.local.set({ access_token: accessToken, refresh_token: refreshTokenVal, user_email: email });
      await initMain(email);
    } catch (error) {
      console.error('OAuth error:', error);
      $('loginStatus').textContent = '로그인 실패. 다시 시도해주세요.';
      $('loginStatus').className = 'error';
      $('googleLoginBtn').disabled = false;
      $('googleLoginBtn').textContent = 'Google로 로그인';
    }
  });

  // 로그아웃
  $('logoutBtn').addEventListener('click', async () => {
    await chrome.storage.local.remove(['access_token', 'refresh_token', 'user_email']);
    showLogin();
  });
});

async function initMain(email) {
  showMain(email);

  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (tab) {
    $('title').textContent = tab.title || '제목 없음';
    $('url').textContent = tab.url || '';
  }

  $('saveBtn').onclick = async () => {
    $('saveBtn').disabled = true;
    $('saveBtn').textContent = '저장 중...';
    $('status').textContent = '';
    $('status').className = '';

    try {
      // 본문 추출 (토글 켜진 경우)
      let content = '';
      if ($('includeBody').checked && tab?.id) {
        content = await extractPageContent(tab.id);
      }

      // 사용자 입력
      const userMemo = $('memoInput').value.trim();
      const tagsRaw = $('tagsInput').value.trim();
      const tags = tagsRaw ? tagsRaw.split(',').map(t => t.trim()).filter(Boolean) : [];

      // memo 조합: 사용자 메모 + 페이지 제목
      const memo = userMemo || tab?.title || 'Saved from Memoir Scout';

      const body = { source_type: 'WEB', url: tab?.url, memo };
      if (content) body.content = content;
      if (tags.length) body.tags = tags;

      await apiFetch('/memories', {
        method: 'POST',
        body: JSON.stringify(body),
      });

      const count = await incrementTodayCount();
      showSuccess(count);
    } catch (error) {
      console.error('저장 실패:', error);
      if (error.message === 'AUTH_EXPIRED' || error.message === 'NO_TOKEN') {
        await chrome.storage.local.remove(['access_token', 'refresh_token', 'user_email']);
        showLogin();
        return;
      }
      showError('저장 실패. 다시 시도해주세요.');
    }
  };
}
