// 좋은 글귀 설정 폼을 코어 설정 저장 필드와 관리 액션에 연결합니다.
(function () {
  const panel = root.querySelector('.gq-quote-settings');
  if (!panel) return;
  const query = selector => panel.querySelector(selector);
  const message = query('[data-quote-management-status]');
  const defaults = {korean_enabled: true, zen_enabled: true, zen_terms: true, korean_weight: config.local_weight ?? 60, zen_weight: 35, positive_weight: 5, quote_language: 'both', quote_font_size: 32, quote_author_font_size: 15, background_source: 'random', photo_refresh_hours: 3,
    quote_en_font: config.quote_en_font === undefined ? config.quote_font : config.quote_en_font,
    quote_en_font_size: config.quote_en_font_size === undefined ? config.quote_font_size ?? 32 : 32};
  const fontSelects = [query('[name=quote_font]'), query('[name=quote_en_font]'), query('[name=quote_author_font]')], fontStatus = query('[data-quote-font-status]');
  for (const select of fontSelects) {
    const value = config[select.name] ?? defaults[select.name];
    const saved = typeof value === 'string' ? value : '';
    if (saved) select.append(new Option(`${saved} · 저장된 글꼴`, saved));
  }
  for (const input of panel.querySelectorAll('[name]')) {
    const value = config[input.name] ?? defaults[input.name];
    if (input.type === 'checkbox') input.checked = [true, 1, '1', 'true', 'on'].includes(value);
    else if (value != null) input.value = String(value);
  }
  const refreshHours = query('[name=photo_refresh_hours]');
  const normalizeRefreshHours = () => {
    const value = refreshHours.value === '' ? 3 : Number(refreshHours.value);
    refreshHours.value = String(Math.max(1, Math.min(24, Math.round(Number.isFinite(value) ? value : 3))));
  };
  refreshHours.addEventListener('change', normalizeRefreshHours);
  refreshHours.addEventListener('blur', normalizeRefreshHours);
  normalizeRefreshHours();
  const fontSize = query('[name=quote_font_size]'), fontRange = query('[data-quote-font-size]');
  const enSize = query('[name=quote_en_font_size]'), enRange = query('[data-quote-en-font-size]');
  const authorSize = query('[name=quote_author_font_size]'), authorRange = query('[data-quote-author-font-size]');
  function normalizeAuthorSize() {
    const max = Number(fontSize.value) - 1, value = authorSize.value === '' ? 15 : Number(authorSize.value);
    authorSize.max = authorRange.max = String(max);
    authorSize.value = authorRange.value = String(Math.max(8, Math.min(max, Math.round(Number.isFinite(value) ? value : 15))));
  }
  for (const [size, range] of [[fontSize, fontRange], [enSize, enRange]]) {
    const normalize = () => {
      const value = size.value === '' ? 32 : Number(size.value);
      size.value = range.value = String(Math.max(16, Math.min(96, Math.round(Number.isFinite(value) ? value : 32))));
      if (size === fontSize) normalizeAuthorSize();
    };
    size.addEventListener('input', () => { if (size.value && size.validity.valid) range.value = size.value; });
    size.addEventListener('change', normalize);
    size.addEventListener('blur', normalize);
    range.addEventListener('input', () => { size.value = range.value; normalize(); });
    normalize();
  }
  authorSize.addEventListener('input', () => { if (authorSize.value && authorSize.validity.valid) authorRange.value = authorSize.value; });
  authorSize.addEventListener('change', normalizeAuthorSize);
  authorSize.addEventListener('blur', normalizeAuthorSize);
  authorRange.addEventListener('input', () => { authorSize.value = authorRange.value; });
  const fontsPromise = (async () => {
    try {
      const response = await fetch('/api/media/fonts', {credentials: 'same-origin', signal: AbortSignal.timeout(15000)});
      const data = await response.json();
      if (!response.ok || !data.success || !Array.isArray(data.fonts)) throw new Error();
      if (!panel.isConnected) return [];
      const fonts = [...new Set(data.fonts.map(font => font.name).filter(name => typeof name === 'string' && name))].sort((a, b) => a.localeCompare(b, 'ko'));
      let missing = false;
      for (const select of fontSelects) {
        const selected = select.value;
        select.replaceChildren(new Option('코어 글꼴 상속', ''), ...fonts.map(name => new Option(name, name)));
        if (selected && !fonts.includes(selected)) { select.append(new Option(`${selected} · 설치 목록에 없음`, selected)); missing = true; }
        select.value = selected;
      }
      fontStatus.textContent = missing
        ? '저장된 글꼴이 설치 목록에 없습니다. 선택값은 유지하며 해당 영역은 코어 글꼴을 사용합니다.'
        : '설치된 글꼴을 한국어·영어·저자에 각각 적용합니다. 아래 설정 저장 버튼을 눌러 적용하세요.';
      return data.fonts;
    } catch { fontStatus.textContent = '글꼴 목록을 불러오지 못했습니다. 기존 선택은 유지됩니다.'; }
    return [];
  })();
  for (const [language, label, select, size] of [
    ['ko', '한국어', fontSelects[0], fontSize], ['en', '영어', fontSelects[1], enSize], ['author', '저자', fontSelects[2], authorSize],
  ]) {
    const sample = root.querySelector(`[data-quote-preview=${language}]`), caption = root.querySelector(`[data-quote-preview-label=${language}]`);
    if (!sample || !caption) continue;
    let version = 0;
    const connected = () => root.isConnected && panel.isConnected && root.contains(panel) && root.contains(sample);
    const updateCaption = () => { caption.textContent = `${label} · ${select.value || '코어 기본'} · ${parseFloat(sample.style.fontSize)}px`; };
    const updateSize = () => {
      if (!connected() || !size.value || !size.validity.valid) return;
      sample.style.fontSize = `${Number(size.value)}px`; updateCaption();
    };
    const updateFont = async () => {
      const token = ++version, name = select.value;
      const current = () => connected() && version === token && select.value === name;
      if (!current()) return;
      sample.style.removeProperty('font-family'); updateCaption();
      if (!name) return;
      const base = getComputedStyle(sample).fontFamily;
      try {
        const font = (await fontsPromise).find(font => font.name === name);
        if (!font?.url || !current()) return;
        const url = new URL(font.url, location.origin);
        if (url.origin !== location.origin || url.username || url.password || !url.pathname.startsWith('/static/fonts/custom/')) return;
        const {loadAndApplyCustomFont} = await import('/static/js/viewer_settings.js');
        if (!current()) return;
        const family = await loadAndApplyCustomFont(name, url.href);
        if (current() && family === `CustomFont_${name.replace(/\s+/g, '_')}`) sample.style.fontFamily = `${JSON.stringify(family)}, ${base}`;
      } catch {}
    };
    for (const event of ['input', 'change', 'focusout']) panel.addEventListener(event, updateSize);
    select.addEventListener('change', updateFont);
    updateSize(); updateFont();
  }
  let busy = false;
  async function action(action_id, context = {}) {
    const {state} = await import('/static/js/state.js');
    const response = await fetch('/api/media/context-menu/book/plugins/action', {
      method: 'POST', credentials: 'same-origin', signal: AbortSignal.timeout(30000),
      headers: {'Content-Type': 'application/json', 'X-Good-Quotes': '1'},
      body: JSON.stringify({type: state.currentLibraryType || 'general', plugin_id: pluginId, action_id, context}),
    });
    const result = await response.json();
    if (!response.ok || !result.success) throw new Error(result.error || '글귀 작업에 실패했습니다.');
    return result;
  }
  async function perform(job) {
    if (busy) return;
    busy = true; message.textContent = '처리 중입니다.';
    panel.querySelectorAll('button').forEach(button => button.disabled = true);
    try { await job(); } catch (error) { message.textContent = error.message || '입력과 연결 상태를 확인해 주세요.'; }
    finally { busy = false; if (panel.isConnected) { panel.querySelectorAll('button').forEach(button => button.disabled = false); } }
  }
  query('[data-quote-refresh]').addEventListener('click', () => perform(async () => {
    const result = await action('quotes_manage');
    if (!panel.isConnected) return;
    const labels = {healthy: '정상', disabled: '꺼짐', 'terms-pending': '이용 범위 미확인', cooldown: '잠시 대기', 'no-eligible-content': '사용 가능한 문구 없음'};
    query('[data-quote-provider-state]').textContent = result.providers.map(provider => `${provider.name} ${labels[provider.status] || provider.status} (${provider.effective_weight}%)`).join(' / ');
    const backgroundLabels = {healthy: '정상', cooldown: '실패 후 잠시 대기', unknown: '아직 요청 없음'};
    const backgrounds = result.backgrounds || {providers: []};
    query('[data-quote-background-state]').textContent = `배경(${({random: '5곳 무작위', gradient: '그라데이션'})[backgrounds.selected] || backgrounds.selected}) · ` +
      backgrounds.providers.map(item => `${item.name} ${backgroundLabels[item.status] || item.status}` +
        (item.failures ? ` (실패 ${item.failures}회${item.last_code ? ` · HTTP ${item.last_code}` : ''})` : '')).join(' / ');
    message.textContent = '공급원 상태를 확인했습니다. 설정 변경은 아래 설정 저장 버튼을 눌러 적용하세요.';
  }));
})();
