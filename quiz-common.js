// ═══════════════════════════════
// 共用測驗邏輯（quiz-common.js）
// hiragana-quiz.html、katakana-quiz.html、grammar-quiz.html 共用；
// 本檔必須在頁面內嵌 script 之後載入（INIT 在檔尾執行）。
// 頁面若要覆寫本檔的函式（如 grammar-quiz 覆寫 renderWrongList），要放在
// <script src=quiz-common.js> 之後再定義——boot 之前的定義會被本檔蓋掉。
// 頁面需先定義：
//   設定：FIREBASE_DB_URL、QUIZ_TYPE、STORAGE_KANA、STORAGE_VOCAB
//   頁面邏輯：getSessionLimit()、rebuildQueues()、nextCard()、restartCurrent()
//   狀態變數：kanaProgress、vocabProgress、totalAnswered、totalCorrect、
//             streak、sessionCount、wrongAnswers
// ═══════════════════════════════
const intervals = [0, 3, 8, 20, 40];
const USER_ID_KEY = 'nihongo_user_id';
let currentUserId = localStorage.getItem(USER_ID_KEY) || '';
let syncTimer = null;

// ── UTILS ──
function shuffle(arr) {
  const a = [...arr];
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

function normalizeRomaji(s) {
  return s.trim().toLowerCase().replace(/\s+/g, '').replace(/oo/g, 'o').replace(/uu/g, 'u').replace(/nn/g, 'n');
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}

let _speakGen = 0;
function speakJa(text) {
  if (!window.speechSynthesis) return;
  speechSynthesis.cancel();
  const gen = ++_speakGen;
  const parts = text.split('/').map(p => p.trim()).filter(Boolean);
  function next(i) {
    if (gen !== _speakGen || i >= parts.length) return;
    const u = new SpeechSynthesisUtterance(parts[i]);
    u.lang = 'ja-JP';
    u.rate = 0.9;
    if (i < parts.length - 1) u.onend = () => setTimeout(() => next(i + 1), 500);
    speechSynthesis.speak(u);
  }
  next(0);
}

// ── SCORE / PROGRESS ──
function resetScore() {
  totalAnswered = 0; totalCorrect = 0; streak = 0; sessionCount = 0;
  wrongAnswers = new Map();
  document.getElementById('scoreCorrect').textContent = 0;
  document.getElementById('scoreTotal').textContent = 0;
  document.getElementById('scoreStreak').textContent = 0;
  document.getElementById('progressFill').style.width = '0%';
}

function updateScore() {
  document.getElementById('scoreCorrect').textContent = totalCorrect;
  document.getElementById('scoreTotal').textContent = totalAnswered;
  document.getElementById('scoreStreak').textContent = streak;
}

function updateProgress() {
  const lim = getSessionLimit();
  document.getElementById('progressFill').style.width = (Math.min(sessionCount / lim, 1) * 100) + '%';
}

// ── SRS ──
function pickFromQueue(queue) {
  const due = queue.filter(c => c.nextReview <= sessionCount);
  if (!due.length) return null;
  const sorted = [...due].sort((a, b) => a.level !== b.level ? a.level - b.level : a.nextReview - b.nextReview);
  const pool = sorted.slice(0, Math.min(3, sorted.length));
  return pool[Math.floor(Math.random() * pool.length)];
}

function advanceSRS(item, correct) {
  if (correct) {
    item.level = Math.min((item.level || 0) + 1, intervals.length - 1);
    streak++;
    totalCorrect++;
  } else {
    item.level = 0;
    streak = 0;
    const key = item.char || item.display || item.word;
    if (key) wrongAnswers.set(key, item);
  }
  item.nextReview = sessionCount + intervals[item.level];
  if (item.char) kanaProgress[item.char] = item.level;
  const vocabKey = item.display || item.word;
  if (vocabKey) vocabProgress[vocabKey] = item.level;
  saveProgress();
  totalAnswered++;
  sessionCount++;
  updateScore();
}

// ── RESULT ──
function renderWrongList() {
  if (wrongAnswers.size === 0) return '';
  const items = [...wrongAnswers.values()].map(c => {
    let front, back;
    if (c.char) {
      front = escapeHtml(c.char);
      if (c.hiragana) {
        back = `${escapeHtml(c.reading)}　來源：${escapeHtml(c.kanji)}<br>${escapeHtml(c.hint || '')}`;
      } else {
        const kata = c.katakana ? `片假名：${escapeHtml(c.katakana)}　` : '';
        back = `${escapeHtml(c.reading)}　${kata}${escapeHtml(c.hint || '')}`;
      }
    } else {
      const kp = c.kanji ? `${escapeHtml(c.kanji)} ` : '';
      front = `${kp}${escapeHtml(c.display || c.word)}`;
      back = `${escapeHtml(c.reading)}　${escapeHtml(c.meaning)}` +
        (c.word && c.hint ? `<br>${escapeHtml(c.hint)}` : '');
    }
    return `<div class="wrong-item"><span class="wrong-front">${front}</span><span class="wrong-back">${back}</span></div>`;
  }).join('');
  return `<div class="wrong-list"><div class="wrong-title">答錯回顧（${wrongAnswers.size}）</div>${items}</div>`;
}

function showResult() {
  updateProgress();
  const pct = totalAnswered ? Math.round((totalCorrect / totalAnswered) * 100) : 0;
  let emoji, msg, sub;
  if (pct >= 90) { emoji = '🎌'; msg = '完美！'; sub = `正確率 ${pct}%，繼續保持！`; }
  else if (pct >= 70) { emoji = '👏'; msg = '很好！'; sub = `正確率 ${pct}%，再練幾次就能鞏固。`; }
  else { emoji = '📖'; msg = '繼續練習！'; sub = `正確率 ${pct}%，間隔重複就是要反覆來。`; }

  document.getElementById('quizContent').innerHTML = `
    <div class="result-screen">
      <div class="big-emoji">${emoji}</div>
      <h2>${msg}</h2>
      <p>${sub}<br><br>正確 ${totalCorrect} / ${totalAnswered} 題</p>
      <button class="restart-btn" onclick="restartCurrent()">再練一次</button>
      ${renderWrongList()}
      <div class="kofi-cta">
        <a href="https://ko-fi.com/ines8964" target="_blank" rel="noopener">
          ☕ 喜歡這個工具？<u>請我喝杯咖啡</u>
        </a>
      </div>
    </div>
  `;
}

// ── FIREBASE SYNC ──
function setSyncStatus(s) {
  const d = document.getElementById('syncDot');
  if (d) d.className = 'sync-dot' + (s ? ' ' + s : '');
}
function updateUserBadge() {
  const el = document.getElementById('userLabel');
  if (!el) return;
  if (!currentUserId) { el.textContent = '設定 ID'; setSyncStatus(''); return; }
  el.textContent = FIREBASE_DB_URL ? currentUserId : currentUserId + ' ☁︎✗';
  if (!FIREBASE_DB_URL) setSyncStatus('');
}
function openUserModal() {
  const overlay = document.getElementById('userModalOverlay');
  const input = document.getElementById('userIdInput');
  document.getElementById('userModalErr').textContent = '';
  input.value = currentUserId;
  document.getElementById('userCancelBtn').style.display = currentUserId ? '' : 'none';
  overlay.classList.add('open');
  setTimeout(() => input.focus(), 80);
}
function closeUserModal() {
  document.getElementById('userModalOverlay').classList.remove('open');
}
async function confirmUserId() {
  const val = document.getElementById('userIdInput').value.trim();
  const err = document.getElementById('userModalErr');
  if (!/^[a-zA-Z0-9_-]{3,20}$/.test(val)) {
    err.textContent = '只能用英文、數字、- 或 _，長度 3–20 字元';
    return;
  }
  const changed = val !== currentUserId;
  currentUserId = val;
  localStorage.setItem(USER_ID_KEY, currentUserId);
  closeUserModal();
  updateUserBadge();
  if (changed) {
    kanaProgress = {}; vocabProgress = {};
    await initAndStart();
  }
}

// level 讀回時夾在合法範圍內；intervals 長度若改變，越界值會讓卡片永遠不再出現
function clampLevel(v) {
  const n = Number(v);
  if (!Number.isFinite(n)) return null;
  return Math.min(Math.max(Math.round(n), 0), intervals.length - 1);
}
function sanitizeProgress(obj) {
  const out = {};
  for (const [k, v] of Object.entries(obj || {})) {
    const lv = clampLevel(v);
    if (lv != null) out[k] = lv;
  }
  return out;
}
function mergeProgress(local, cloud) {
  const merged = sanitizeProgress(local);
  for (const [k, v] of Object.entries(cloud || {})) {
    const lv = clampLevel(v);
    if (lv != null) merged[k] = Math.max(merged[k] ?? 0, lv);
  }
  return merged;
}

async function fetchFromFirebase() {
  if (!FIREBASE_DB_URL || !currentUserId) return false;
  try {
    setSyncStatus('syncing');
    const ctrl = new AbortController();
    const tid = setTimeout(() => ctrl.abort(), 5000);
    const res = await fetch(FIREBASE_DB_URL + '/progress/' + currentUserId + '/' + QUIZ_TYPE + '.json',
      { signal: ctrl.signal });
    clearTimeout(tid);
    if (!res.ok) throw new Error(res.status);
    const data = await res.json();
    if (data && typeof data === 'object') {
      // 逐卡取較高 level 合併，不讓雲端資料蓋掉本機進度
      kanaProgress  = mergeProgress(kanaProgress,  data.kana);
      vocabProgress = mergeProgress(vocabProgress, data.vocab);
      localStorage.setItem(STORAGE_KANA,  JSON.stringify(kanaProgress));
      localStorage.setItem(STORAGE_VOCAB, JSON.stringify(vocabProgress));
      schedulePushToFirebase();
    }
    setSyncStatus('synced');
    return true;
  } catch(e) {
    setSyncStatus(e.name === 'AbortError' ? '' : 'error');
    return false;
  }
}
function schedulePushToFirebase() {
  if (!FIREBASE_DB_URL || !currentUserId) return;
  clearTimeout(syncTimer);
  setSyncStatus('syncing');
  syncTimer = setTimeout(async () => {
    try {
      await fetch(FIREBASE_DB_URL + '/progress/' + currentUserId + '/' + QUIZ_TYPE + '.json', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ kana: kanaProgress, vocab: vocabProgress })
      });
      setSyncStatus('synced');
    } catch(e) { setSyncStatus('error'); }
  }, 3000);
}

function loadProgress() {
  try {
    kanaProgress  = sanitizeProgress(JSON.parse(localStorage.getItem(STORAGE_KANA)  || '{}'));
    vocabProgress = sanitizeProgress(JSON.parse(localStorage.getItem(STORAGE_VOCAB) || '{}'));
  } catch(e) { kanaProgress = {}; vocabProgress = {}; }
}
function saveProgress() {
  localStorage.setItem(STORAGE_KANA,  JSON.stringify(kanaProgress));
  localStorage.setItem(STORAGE_VOCAB, JSON.stringify(vocabProgress));
  schedulePushToFirebase();
}

async function initAndStart() {
  loadProgress();
  updateUserBadge();
  if (FIREBASE_DB_URL && currentUserId) await fetchFromFirebase();
  rebuildQueues();
  nextCard();
}

// ── INIT ──
if (!currentUserId && FIREBASE_DB_URL) {
  openUserModal();
  loadProgress(); updateUserBadge();
  rebuildQueues();
  nextCard();
} else {
  initAndStart();
}
