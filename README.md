# Coders Core v2 호환 개발 가이드

공개 웹 문서: https://docs.coders.kr/

로그인·실행 계좌 없이 읽는 정적 개발자 문서입니다. 서비스 코드는 포함하지 않습니다.

## 수정과 배포

- `guide.md`: 문서 원본
- `build.py`: Markdown → 정적 HTML 변환
- `assets/`: 스타일·목차·코드 복사·테마 및 글꼴
- `.github/workflows/pages.yml`: main 갱신 시 GitHub Pages 자동 배포

```bash
python -m pip install -r requirements.txt
python build.py
python -m http.server 8000 --directory _site
```

`guide.md` 또는 화면 자산을 수정해 main에 push하면 자동 배포됩니다.
외부 JavaScript CDN이나 로그인 API에 의존하지 않습니다. 문서 안의 실행 서비스 링크는 별도로 Coders 로그인이 필요할 수 있습니다.

글꼴 라이선스는 `assets/fonts/*-OFL.txt`에 포함되어 있습니다.

## 공개 도메인

- 공유 주소: https://docs.coders.kr/
- DNS: `docs.coders.kr` CNAME → `coders-kr.github.io` (DNS only)
- GitHub Pages의 Custom domain: `docs.coders.kr`
- HTTPS 인증서와 리디렉션은 GitHub Pages에서 관리합니다.

GitHub Actions 배포를 사용하므로 도메인 설정은 Pages 설정에 저장되며, `CNAME` 파일에 의존하지 않습니다.
