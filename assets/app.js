(() => {
  const root = document.documentElement;
  const theme = document.getElementById('theme-toggle');
  const scheme = matchMedia('(prefers-color-scheme: dark)');
  let preference;
  try { preference = localStorage.getItem('coders-guide-theme'); } catch {}
  const applyTheme = () => {
    const dark = preference ? preference === 'dark' : scheme.matches;
    root.dataset.theme = dark ? 'dark' : 'light';
    theme.setAttribute('aria-label', dark ? '라이트 모드로 전환' : '다크 모드로 전환');
    document.querySelector('meta[name=theme-color]').content = dark ? '#121418' : '#ffffff';
  };
  applyTheme();
  theme.addEventListener('click', () => {
    preference = root.dataset.theme === 'dark' ? 'light' : 'dark';
    try { localStorage.setItem('coders-guide-theme', preference); } catch {}
    applyTheme();
  });
  scheme.addEventListener('change', applyTheme);

  const toc = document.querySelector('.toc');
  const desktop = matchMedia('(min-width: 980px)');
  const fitToc = () => { toc.open = desktop.matches; };
  fitToc();
  desktop.addEventListener('change', fitToc);
  toc.querySelector('nav').addEventListener('click', event => {
    if (event.target.closest('a') && !desktop.matches) toc.open = false;
  });

  const status = document.getElementById('copy-status');
  const timers = new WeakMap();
  for (const button of document.querySelectorAll('.copy-code')) {
    button.addEventListener('click', async () => {
      const code = button.closest('.code-block').querySelector('code');
      clearTimeout(timers.get(button));
      try {
        await navigator.clipboard.writeText(code.textContent);
        button.textContent = '복사됨'; button.classList.add('copied');
        status.textContent = '코드를 클립보드에 복사했습니다.';
      } catch {
        const range = document.createRange(); range.selectNodeContents(code);
        const selection = getSelection(); selection.removeAllRanges(); selection.addRange(range);
        button.textContent = '선택됨';
        status.textContent = '코드를 선택했습니다. 복사 단축키를 눌러주세요.';
      }
      timers.set(button, setTimeout(() => {button.textContent = '복사'; button.classList.remove('copied');}, 1800));
    });
  }

  const sections = [...document.querySelectorAll('.prose h2[id]')];
  const links = [...toc.querySelectorAll('nav a')];
  const top = document.querySelector('.back-top');
  let scheduled = false;
  const update = () => {
    scheduled = false;
    let current = sections[0]?.id;
    for (const section of sections) {
      if (section.getBoundingClientRect().top <= 130) current = section.id;
    }
    for (const link of links) {
      if (link.hash === '#' + current) link.setAttribute('aria-current', 'location');
      else link.removeAttribute('aria-current');
    }
    top.hidden = scrollY < 600;
  };
  addEventListener('scroll', () => {
    if (!scheduled) {scheduled = true; requestAnimationFrame(update);}
  }, {passive:true});
  addEventListener('resize', update);
  update();
})();
