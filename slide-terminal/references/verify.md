# 브라우저 측정

## 띄우기

덱 HTML은 file:// 로도 열리지만, 측정·스크린샷을 안정적으로 하려면 점검용 서버로 띄운다.

```powershell
& "<스킬경로>\scripts\serve.ps1" -Root "<덱이 있는 폴더>" -Port 8785 -Minutes 15
```
(run_in_background로 실행) → 브라우저 창에서 `http://localhost:8785/<덱파일>.html#4` 처럼 쪽번호를 붙여 연다.

## 전 쪽 측정 스크립트

브라우저 창의 javascript 도구에서 실행한다. 모든 쪽을 돌며 문제만 돌려준다.

```js
(() => {
  const out = [];
  const slides = [...document.querySelectorAll('.deck-stage > .slide')];
  slides.forEach((s, i) => {
    const prev = s.className; s.classList.add('active', 'visible');
    const sr = s.getBoundingClientRect(), f = sr.width / 1920;
    const P = i + 1, issue = m => out.push(P + '쪽: ' + m);
    // 1) 슬라이드 밖으로 나간 요소
    s.querySelectorAll('*').forEach(e => {
      const r = e.getBoundingClientRect(); if (!r.width || !r.height) return;
      if (r.right > sr.right + 2 || r.bottom > sr.bottom + 2) issue('밖으로 넘침 ' + e.className + ' 「' + e.textContent.trim().slice(0, 20) + '」');
    });
    // 2) 상자 안 넘침
    s.querySelectorAll('.k-card,.k-col,td,.k-body').forEach(e => {
      if (e.scrollHeight > e.clientHeight + 2 || e.scrollWidth > e.clientWidth + 2) issue('상자 넘침 ' + e.className + ' 「' + e.textContent.trim().slice(0, 20) + '」');
    });
    // 3) 제목 한 줄
    const t = s.querySelector('.k-title');
    if (t) { const lh = parseFloat(getComputedStyle(t).lineHeight); if (t.getBoundingClientRect().height / f > lh * 1.5) issue('제목 두 줄'); }
    // 4) 단 끝 정렬
    s.querySelectorAll('.k-row').forEach(row => {
      const cols = [...row.children].filter(c => c.getBoundingClientRect().height > 0);
      if (cols.length < 2) return;
      const lastBottom = c => { const k = [...c.children].filter(x => x.getBoundingClientRect().height); return k.length ? k[k.length - 1].getBoundingClientRect().bottom : c.getBoundingClientRect().bottom; };
      const tops = cols.map(c => c.getBoundingClientRect().top / f), bots = cols.map(c => lastBottom(c) / f);
      const d1 = Math.max(...tops) - Math.min(...tops), d2 = Math.max(...bots) - Math.min(...bots);
      if (d1 > 3 || d2 > 6) issue('단 정렬 어긋남 위 ' + d1.toFixed(0) + 'px / 아래 ' + d2.toFixed(0) + 'px');
    });
    // 5) 쪽번호
    const pg = s.querySelector('.k-foot > span:last-child');
    if (pg && pg.textContent.trim() !== String(P)) issue('쪽번호 ' + pg.textContent.trim() + ' ≠ ' + P);
    s.className = prev;
  });
  return out.length ? out : ['문제 없음 (' + slides.length + '쪽)'];
})()
```

단 아래 끝 차이는 내용 길이 때문에 생길 수 있다(출발용 뼈대 4쪽도 내용이 짧아 168px 어긋남으로 잡힌다). 사용자가 맞추라고 한 쪽(대부분)은 마지막 상자를 `flex:1`로 늘리거나 간격을 조정해 맞춘다.

## 팔레트 점검

```js
(() => {
  const ok = new Set(['#055f9b','#cfe0ec','#9bbfd7','#6a9fc3','#044775','#032e4e','#73be1e','#e3f2d2','#c7e5a5','#abd878','#568e16','#3a5f0f','#1ba1c8','#d1ecf4','#a4d9e9','#76c7de','#147996','#0e5064','#666666','#e0e0e0','#c2c2c2','#a3a3a3','#4d4d4d','#333333','#85714d','#e7e3db','#cec6b8','#b6aa94','#64553a','#433927','#8a8d8f','#e8e8e9','#d0d1d2','#b9bbbc','#686a6b','#454647','#ffffff','#000000','#b8322a','#e6b3ae','#8e2a22','#fbedec']);
  const hex = c => { const m = c.match(/\d+(\.\d+)?/g); if (!m || (m[3] !== undefined && +m[3] === 0)) return null; return '#' + m.slice(0, 3).map(v => (+v).toString(16).padStart(2, '0')).join(''); };
  const bad = {};
  document.querySelectorAll('.deck-stage .slide *').forEach(e => {
    const cs = getComputedStyle(e);
    ['color', 'backgroundColor', 'borderTopColor'].forEach(p => { const h = hex(cs[p]); if (h && !ok.has(h)) bad[h] = (bad[h] || 0) + 1; });
  });
  return bad;
})()
```

반투명 색(rgba)은 섞인 결과라 목록에 없을 수 있다. 눈에 띄는 것만 확인한다.

## 스크린샷

고친 쪽마다 `#쪽번호`로 이동해 스크린샷을 찍어 본다. 표지·사진이 있는 쪽은 확대(zoom)로 깨짐을 확인한다.
