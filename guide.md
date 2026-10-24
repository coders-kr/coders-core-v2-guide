# Coders Core v2 호환 개발 가이드

이 문서는 **2026-10-24 현재 구현**을 기준으로, 개발자가 자신의 코드와 프론트를 Coders Core v2에서 실행하거나 외부 서비스에서 Coders API를 호출하는 방법을 설명합니다.

기본 원칙은 다음과 같습니다.

- 일반적인 서비스 로직은 HTTP 코드로 작성합니다. 계좌 생성·정산 코드를 모든 서비스에 넣을 필요는 없습니다.
- 프로젝트에는 제공할 엔드포인트·프론트·요청 예산·필요 권한을 선언합니다.
- 사용자가 실행 계좌와 권한을 제공합니다. 선언만으로 권한이 부여되지는 않습니다.
- 다른 Coders 코드나 자원을 사용할 때는 현재 실행 계좌와 하위 호출 예산을 전달합니다.

## 1. 어떤 형태로 연결할 것인가

| 목적 | 연결 방법 | 필요한 것 |
| --- | --- | --- |
| GitHub 코드와 프론트를 Coders에서 실행 | 공개 저장소 + 전체 커밋 해시 | 루트의 `coders.json`, Python ASGI 파일, 선택적인 정적 프론트 |
| Coders에 등록한 프로젝트의 브라우저에서 API 호출 | 같은 출처의 `/api/{별칭}` | 프로젝트 연결, 브라우저 SDK 또는 HTTP 요청 |
| 자체 서버·CLI에서 Coders 엔드포인트 호출 | GitHub 커밋 주소 또는 `/v1/invoke/{이름}` | 계좌 키, 예산, 멱등성 키 |
| 실행 중인 코드에서 Coders 자원 사용 | 환경 변수 `CODERS_URL`의 중개 서버 | 현재 실행 계좌 키, 작업별 멱등성 키, 하위 호출 예산 |

현재 GitHub 실행은 임의의 웹 서버를 통째로 배포하는 방식이 아닙니다. 지원하는 ASGI 실행 형식으로 코드를 제공해야 합니다. 별도로 운영하는 서버가 Coders API를 호출하는 것은 일반 HTTP 클라이언트로 가능합니다.

## 2. 가장 작은 호환 프로젝트

저장소를 다음처럼 구성합니다.

```text
coders.json
api/
  analyze.py
public/
  index.html
  .coders-ui.json
```

### 2.1 프로젝트 명세: `coders.json`

```json
{
  "version": 1,
  "name": "텍스트 분석",
  "frontend": {"directory": "public"},
  "endpoints": {
    "analyze": {
      "file": "api/analyze.py",
      "path": "/",
      "methods": ["POST"],
      "budget": "11.000"
    }
  },
  "permissions": []
}
```

| 항목 | 의미와 조건 |
| --- | --- |
| `version` | 현재는 `1`만 지원합니다. |
| `name` | 프로젝트 표시 이름입니다. 1~80자입니다. |
| `frontend.directory` | 저장소 기준 상대 경로입니다. 해당 폴더에 `index.html`이 있어야 합니다. |
| `endpoints` | 프로젝트 API 별칭과 실행 대상을 연결합니다. 최대 32개입니다. |
| 엔드포인트 이름 | 영문 소문자로 시작하고 소문자·숫자·`_`·`-`를 쓰는 최대 40자 이름입니다. |
| `file` | 실행할 단일 UTF-8 Python ASGI 파일의 상대 경로입니다. |
| `path` | 코드가 받는 HTTP 경로입니다. 기본값은 `/`입니다. |
| `methods` | 허용할 메서드입니다. 기본값은 `["POST"]`이며 GET·POST·PUT·PATCH·DELETE를 지원합니다. |
| `budget` | 프로젝트 세션으로 이 엔드포인트를 호출할 때 배정할 원화 예산입니다. |
| `request_budget` | 엔드포인트의 `budget`이 없을 때 쓸 프로젝트 기본 예산입니다. 생략하면 30원입니다. |
| `permissions` | 첫 동의 화면에서 요청할 권한입니다. 현재 `transfer`, `transfer-precise`를 지원합니다. |

`frontend`와 `endpoints` 중 하나 이상이 필요합니다. 알 수 없는 필드는 거부합니다. 명세 파일이 없는 저장소의 자동 감지나 대시보드 설정과의 병합은 지원하지 않습니다.

엔드포인트의 `file` 대신 다음처럼 현재 설치된 공식 어댑터를 연결할 수도 있습니다. `file`과 `endpoint`는 동시에 지정할 수 없습니다.

```json
{
  "endpoint": "coders-openai",
  "budget": "30.000"
}
```

공식 어댑터 이름을 적는 것과 사용자에게 데이터 전송 권한을 받는 것은 별개입니다. 임의의 가변 사용자 엔드포인트를 이 참조 항목에 연결하는 것은 현재 지원하지 않습니다.

### 2.2 백엔드: `api/analyze.py`

```python
from fastapi import FastAPI, Request

app = FastAPI()


@app.post("/")
async def analyze(request: Request):
    # 일반적인 HTTP 코드입니다. 계좌 생성이나 반환 코드는 필요하지 않습니다.
    body = await request.json()
    text = body.get("text", "")
    return {"characters": len(text), "words": len(text.split())}
```

실행 모듈은 `app`이라는 ASGI 애플리케이션을 제공해야 합니다. `uvicorn.run()`으로 포트를 열거나 서버를 계속 띄워두지 않습니다. 실행기가 요청을 전달하고 응답 후 컨테이너를 정리합니다.

플랫폼 이미지에 설치된 패키지만 사용할 수 있습니다. 현재 예제의 FastAPI·httpx는 사용 가능하지만, `requirements.txt`, npm 스크립트, Dockerfile을 자동 실행하지 않습니다. 저장소의 다른 Python 파일도 실행 컨테이너에 함께 복사되지 않습니다. 로컬 모듈 import나 저장소 파일 읽기에 의존하지 마세요.

순수 ASGI를 직접 구현한다면 HTTP뿐 아니라 lifespan 시작·종료 이벤트를 올바르게 처리하거나 lifespan 미지원 규약을 따라야 합니다. 동작하는 순수 ASGI 예제는 [로컬 예제](https://github.com/coders-kr/coders-github-example/blob/main/api/analyze.py)를 참고하세요.

컨테이너의 메모리·파일·백그라운드 태스크는 영속 저장소가 아닙니다. 요청 사이에 유지할 데이터는 Coders 저장소 등 별도의 지속성 있는 자원에 저장합니다. ASGI 코드가 `202`를 반환해도 컨테이너의 백그라운드 작업이 계속 살아 있지는 않습니다.

### 2.3 sandbox 화면: `public/.coders-ui.json`

```json
{
  "title": "텍스트 분석",
  "actions": [
    {
      "title": "분석하기",
      "endpoint": "analyze",
      "fields": [
        {"name": "text", "label": "분석할 내용", "multiline": true}
      ]
    }
  ]
}
```

Coders가 입력 화면을 만들고 `{"text":"입력값"}`을 해당 엔드포인트에 POST합니다. 이 화면에서 사용할 엔드포인트는 JSON 응답을 반환하도록 작성합니다. 임의의 개발자 JavaScript를 실행하거나 개발자 HTML의 폼을 그대로 사용하지 않습니다.

`actions`는 최대 16개, 작업별 `fields`도 최대 16개입니다. `endpoint`는 `coders.json`에 있는 별칭이어야 합니다. 필드 이름은 영문 소문자로 시작하는 소문자·숫자·`_` 조합이며 최대 40자입니다.

이 파일이 없으면 sandbox에서는 HTML의 제한된 텍스트 미리보기만 표시합니다. 기본 모드에서도 서비스 버튼을 제공하려면 선언형 화면을 함께 넣으세요.

### 2.4 all 화면: `public/index.html`

```html
<!doctype html>
<html lang="ko">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>텍스트 분석</title>
<form>
  <textarea name="text" required></textarea>
  <button>분석하기</button>
</form>
<pre role="status"></pre>
<script type="module">
import { createClient } from '/_coders/sdk.js';
const coders = createClient();
const form = document.querySelector('form');
const output = document.querySelector('pre');

form.addEventListener('submit', async event => {
  event.preventDefault();
  try {
    const result = await coders.request('/api/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({text: form.elements.text.value}),
    });
    output.textContent = JSON.stringify(result.data, null, 2);
  } catch {
    output.textContent = '결과를 확인하지 못했습니다.';
  }
});
</script>
</html>
```

이 코드는 기본 호출 예제입니다. 잔액 부족과 재시도 처리는 아래 규약을 추가로 적용합니다.

all에서는 프로젝트의 HTML·JavaScript를 실행합니다. CSS·JS·폰트 등은 공개 폴더에 함께 넣어 같은 출처에서 제공하세요. 현재 프론트의 CSP는 외부 CDN 스크립트·외부 fetch 등을 허용하지 않으므로, all이라는 이유만으로 임의의 외부 브라우저 리소스가 로드되지는 않습니다. 서버 코드의 직접 외부 통신 허용과 구분해야 합니다.

`/api/`와 `/_coders/`는 예약 경로입니다. 프로젝트 프론트에서 계좌 비밀 키나 Coders 로그인 토큰을 저장·전달하지 않습니다. Core가 프로젝트 세션으로 실행 계좌를 선택합니다.

## 3. GitHub에서 처음 실행하기

저장소를 공개로 만들고 루트에 명세와 코드를 커밋합니다. 브랜치 이름 대신 **전체 40자리 커밋 해시**로 접속합니다.

```text
브라우저 진입
https://api.coders.kr/{owner}/{repo}/{commit}

엔드포인트 호출
https://api.coders.kr/{owner}/{repo}/{commit}/analyze
```

브라우저에서는 로그인 → 필요한 경우 준비 화면 → 프로젝트 사용 동의 → 실행 화면으로 이어집니다. 같은 커밋의 준비 결과는 공유하고, 사용자별 계좌·권한·데이터는 분리합니다. 같은 저장소라도 커밋이 다르면 별도 프로젝트 주소와 연결을 사용합니다.

새 커밋은 새 주소입니다. 이미 준비된 주소의 코드를 덮어쓰지 않습니다. 커밋을 고정해도 플랫폼 런타임 업데이트까지 고정하는 재현 빌드를 의미하지는 않습니다.

실제 공개 예제: [coders-kr/coders-github-example](https://github.com/coders-kr/coders-github-example). 복사 가능한 파일은 이 저장소의 [examples/github](https://github.com/coders-kr/coders-github-example/blob/main/coders.json)에도 있습니다.

### 외부 API 호출

다음은 신뢰할 수 있는 서버나 CLI에서 실행합니다. 환경 변수에는 저장소·커밋·계좌 키와 작업별 `REQUEST_KEY`를 설정합니다. 같은 작업을 재전송할 때는 `REQUEST_KEY`도 유지합니다.

```bash
curl --request POST \
  "https://api.coders.kr/${GITHUB_OWNER}/${GITHUB_REPO}/${COMMIT_SHA}/analyze" \
  --header "Coders-Grant: ${CODERS_ACCOUNT_KEY}" \
  --header 'Coders-Budget: 11.000' \
  --header "Idempotency-Key: ${REQUEST_KEY}" \
  --header 'Content-Type: application/json' \
  --data '{"text":"안녕하세요 Coders"}'
```

| 헤더 | 규약 |
| --- | --- |
| `Coders-Grant` | 호출 계좌의 비밀 키입니다. 최상위·하위 계좌 키를 사용할 수 있습니다. |
| `Coders-Budget` | 이 요청에 배정할 원화 예산입니다. 실제 사용료를 고정하는 값은 아닙니다. |
| `Idempotency-Key` | 같은 작업의 재전송에 유지할 1~128자 키입니다. 새로운 작업에는 새 키를 씁니다. |
| `Coders-Trust` | 선택 사항입니다. 생략하면 상위 정책을 상속합니다. sandbox에서 더 넓은 모드로 바꿀 수 없습니다. |

이미 등록된 엔드포인트는 Core 호스트의 `/v1/invoke/{이름}`에 같은 규약으로 호출합니다. 이 서버 API를 다른 출처의 프론트에서 계좌 키를 넣어 직접 호출하는 패턴으로 설계하지 마세요. 브라우저 프로젝트는 같은 출처의 `/api/{별칭}`과 세션을 사용합니다.

### 준비 중의 `202`

아직 준비되지 않은 커밋에 API 요청을 보내면 원래 엔드포인트 대신 다음과 같은 준비 상태를 반환합니다.

```json
{
  "state": "queued",
  "execution_started": false,
  "status_url": "https://core-v2.coders.kr/github/OWNER/REPO/COMMIT/_status",
  "status_path": "/github/OWNER/REPO/COMMIT/_status"
}
```

1. `status_url`을 조회합니다. 중개 서버 안에서는 상대 경로인 `status_path`를 사용할 수 있습니다.
2. `state=ready`가 되면 **같은 본문·예산·요청 키**로 원래 API를 다시 호출합니다.
3. 준비가 실패하면 오류를 확인합니다. 실패 후 재준비는 60초가 지난 뒤 새 준비 요청 키로 시작합니다.

처음 준비를 시작한 계좌가 준비 시도 비용을 지불합니다. 현재는 운영자가 설정한 요청 기본 요금이며, 실패한 준비도 청구됩니다. 같은 준비 작업을 기다리는 다른 호출자에게 준비비를 다시 청구하지 않습니다. 준비비와 이후 실행 예산을 모두 감당할 가용액이 필요합니다.

이 `202`는 **직접 호출한 GitHub 엔드포인트가 아직 실행되지 않았다**는 의미입니다. 이미 실행된 상위 코드가 하위 준비 결과를 받아 `202`로 반환한 경우, 상위 실행의 재전송은 기존 결과를 재생할 수 있습니다. 상위 코드의 실행 ID와 상태도 함께 구분해야 합니다.

## 4. 계좌·예산·요금 규칙

사용자의 기본 계좌 아래에 프로젝트 계좌를 두고, Core가 호출마다 실행 계좌를 분할합니다. 코드에는 부모 키 대신 **새 실행 계좌 키**를 전달합니다.

- 평범한 요청 완료와 실행 계좌 반환은 Core가 처리합니다. 개발자 코드가 매번 계좌를 닫을 필요는 없습니다.
- 명시적으로 만든 장기 보유 계좌는 보유자가 별도로 종료해야 합니다.
- 요청 연결이 끊어져도 이미 접수된 실행이 바로 취소되는 것은 아닙니다.
- 실패해도 이미 발생한 컴퓨팅 비용·외부 자원 사용·확정 송금은 사라지지 않습니다.
- GitHub 저장소 소유자에게 자동 지급되는 서비스 이용료는 없습니다. 지급이 필요하면 일반 송금 API를 사용합니다.

### 예산은 가격과 다릅니다

호스팅 실행은 요청 접수 비용과 컴퓨팅 예약을 먼저 확보합니다. 하위 호출·송금·저장소 사용도 같은 실행 계좌 안에서 예산을 사용합니다. 사용하지 않은 돈은 원장 규칙에 따라 상위로 돌아갑니다.

따라서 **30원 송금 코드의 예산을 30원으로 잡으면 부족할 수 있습니다.** 요청료와 컴퓨팅 예약, 하위 호출까지 포함해 배정해야 합니다. 예제의 `11.000`은 작은 처리 작업용 예산이며 모든 서비스에 적용할 고정값이 아닙니다. 단가·예약액·시간 제한은 운영 설정을 확인하세요.

원화는 소수점 여섯 자리까지 처리하고 화면에서는 소수점 세 자리로 표시합니다. 요청 금액에는 쉼표·`원` 표시를 넣지 않고 `"30.000001"` 같은 십진 문자열을 사용하면 됩니다. 회계 계산은 부동소수점 대신 Decimal 등 정확한 십진 연산으로 처리합니다.

### 프로젝트의 매일 충전 목표

첫 동의 때 목표가 100원이면 기본 계좌에서 프로젝트 잔액을 100원까지 채웁니다. 이후 한국 시간 자정에 부족분만 보충합니다. 실행 중인 하위 예산도 잔액에 포함하며, 100원 이상 남아 있으면 회수하거나 추가 충전하지 않습니다.

낮에 잔액이 부족하면 자동 보충하지 않고 추가 할당을 확인받습니다. 기본 계좌가 부족하면 가능한 만큼만 채우고 부족분을 표시합니다. 목표 잔액은 **일별 지출 한도도, 무료 지급액도 아닙니다.**

## 5. sandbox와 all의 호환 조건

| 항목 | sandbox | all |
| --- | --- | --- |
| 백엔드 실행 | 격리 실행, 직접 외부 네트워크 차단 | 직접 외부 통신 허용 |
| 프론트 | Coders 선언형 `/run` 화면 | 프로젝트 HTML·JavaScript |
| 외부 서비스·데이터 전송 | Coders 중개 경로와 승인된 권한 사용 | 넓은 코드 권한 적용. API별 소유권 검사는 유지 |
| 송금 | 선언하고 허용받은 송금 권한과 공통 제한 적용 | 직접 송금 허용. 예산·잔액·API 금액 규칙은 적용 |
| 하위 실행 | 같은 격리 정책·실행 영역 상속 | 상위 권한보다 넓힐 수 없음 |

신규 기본값은 sandbox입니다. 기존 `coders-only`는 호환 모드로 남아 있으며 새 프로젝트의 기본 설계로 삼지 않습니다.

일반 코드가 직접 외부 API를 부르는 구조라면 all에서 동작할 수 있어도 sandbox 호환을 위해 수정이 필요합니다. 외부 작업을 Coders의 승인된 중개 엔드포인트로 옮기고, 사용자가 필요한 권한을 허용하도록 연결합니다.

### 프로젝트 권한 선언

```json
{
  "permissions": ["transfer", "transfer-precise"]
}
```

위 내용은 `coders.json`의 해당 항목입니다. 전체 명세의 다른 필드도 함께 작성해야 합니다.

- `transfer`: 일반 송금. 1원 단위, 송금자 정보 비공개, 한국 시간 다음 자정에 수취 계좌별 합산 지급입니다.
- `transfer-precise`: 정밀 송금. 소수점 여섯 자리까지 즉시 지급합니다.
- 송금 대상과 실제 금액은 코드가 결정합니다. 사용자는 프로젝트의 송금 권한을 한 번 허용하고, 이후 예산과 공통 제한 안에서 사용합니다.
- 선언한 권한을 거절하거나 나중에 철회할 수 있습니다. 코드는 거절을 처리해야 합니다.
- OpenAI·행 공유 등은 현재 별도의 권한 요청 흐름입니다. 지원하지 않는 이름을 `permissions`에 임의로 추가할 수 없습니다.

## 6. 실행 코드에서 하위 호출·송금하기

실행 중인 코드에는 다음 값이 제공됩니다.

| 값 | 용도 |
| --- | --- |
| 요청 헤더 `Coders-Grant` | 현재 실행에 배정된 계좌 키 |
| 요청 헤더 `Coders-Trust` | 실제 적용된 실행 모드 |
| 요청 헤더 `Idempotency-Key` | 현재 실행에 대응하는 키. 하위 작업별 키의 기반으로 사용할 수 있음 |
| 환경 변수 `CODERS_URL` | 실행 계좌에 묶인 로컬 Coders 중개 서버 주소 |

중개 서버를 사용할 때는 현재 키만 전달합니다. 부모 계좌 키, 다른 사용자의 키, 관리자 키를 가져오거나 전달하지 않습니다.

다음은 이미 등록된 하위 엔드포인트를 호출하는 코드 조각입니다. `my-child-endpoint`는 실제 등록 이름으로 바꿉니다. 상위 요청 예산에는 자신의 컴퓨팅 비용 외에 아래의 11원도 들어 있어야 합니다.

```python
import os
import httpx

async def call_child(request, payload):
    async with httpx.AsyncClient(base_url=os.environ["CODERS_URL"]) as client:
        response = await client.post(
            "/v1/invoke/my-child-endpoint",
            headers={
                "Coders-Grant": request.headers["Coders-Grant"],
                "Coders-Budget": "11.000",
                "Idempotency-Key": request.headers["Idempotency-Key"] + ":child",
            },
            json=payload,
        )
        return response
```

하위 호출을 위해 개발자가 먼저 계좌를 만들 필요는 없습니다. Core가 예산을 분할하고 하위 실행 키를 전달합니다. 서로 다른 하위 작업에는 `:child-a`, `:child-b`처럼 다른 키를 사용하고, 같은 작업의 재전송에는 같은 키와 입력을 유지합니다.

현재 중개 서버에서 허용하는 주요 경로는 다음과 같습니다.

- `/v1/invoke/{이름}`: 등록 엔드포인트 실행
- `/github/{owner}/{repo}/{commit}/{endpoint}` 및 `/_status`: GitHub 코드 실행·준비 상태 조회
- `/v1/accounts/current`, `/split`, `/transfers`, `/close`: 현재 계좌 작업
- `/v1/permissions/requests`: 권한 요청
- `/store/...`: 지원하는 데이터 저장소 작업

이 경로들은 `CODERS_URL` 기준의 상대 경로로 호출합니다. 중개 서버에 임의 외부 URL을 넣어 프록시처럼 사용할 수 없습니다.

송금은 `/v1/accounts/transfers`에 현재 계좌 키와 작업 키를 넣어 다음 본문으로 POST합니다. 이 계좌 관리 요청 자체에는 `Coders-Budget` 대신 현재 계좌의 가용액을 사용하며 요청 비용도 필요합니다.

```json
{
  "recipient_id": "수취 계좌의 공개 ID",
  "amount": "30.000",
  "mode": "standard"
}
```

`standard`는 일반 송금, `precise`는 정밀 송금입니다. `mode`를 생략하면 허용된 프로젝트 송금 모드에 따라 결정되므로 의도가 분명하면 명시하세요. 일반 송금의 `status=scheduled`는 접수·정산 대기이며 즉시 지급 완료를 뜻하지 않습니다. 상세 규약은 [권한 문서](https://docs.coders.kr/#permissions)를 참고하세요.

## 7. 오류와 재시도

| 응답 | 해야 할 일 |
| --- | --- |
| `202` + `execution_started:false` | GitHub 준비 상태를 기다린 뒤 같은 원래 요청을 재전송합니다. |
| `402` | `error.code`로 잔액·추가 할당·컴퓨팅 문제를 구분합니다. 제공된 계좌 확인 경로가 있으면 연결합니다. |
| `403 permission_required` | Coders 승인 화면에서 권한을 확인합니다. 승인만으로 작업이 실행된 것은 아닙니다. |
| 그 밖의 `403` | 정책 완화·소유권·격리 경계 위반 등입니다. 사용자 승인 창으로 모두 해결할 수는 없습니다. |
| `409` | 멱등성 키 충돌, 실행 진행 중, 종료 상태 등을 오류 코드로 구분합니다. |
| `422` | 명세·입력·준비 실패 내용을 확인합니다. |
| 전송 오류·결과 불명 | 같은 본문·예산·키로 결과를 확인합니다. 바로 새 키를 만들지 않습니다. |

`Coders-Execution-Id`는 접수된 실행을 식별합니다. 같은 계좌에서 같은 키와 같은 입력을 재전송하면 기존 실행 결과를 재생하고, 입력·예산 등을 바꾸면 충돌할 수 있습니다.

- **접수 전 거부:** 계좌 확인·추가 할당 후 같은 원래 요청을 재시도합니다.
- **이미 완료된 실행의 실패:** 같은 키는 실패 결과를 재생합니다. 작업을 새로 실행하려면 새 키가 필요하며 비용이 추가될 수 있습니다.
- **지급·외부 작업이 있었거나 결과가 불명확한 실행:** 전체 요청을 새 키로 자동 재실행하지 않습니다. 이미 수행된 부작용을 먼저 확인합니다.

컴퓨팅 예약 부족과 실행 중 컴퓨팅 예산 소진은 다릅니다. 후자는 요청 예산 숫자를 크게 하는 것만으로 항상 해결되지 않으므로 처리 시간·하위 호출 구조·운영 설정을 함께 확인합니다.

### 프론트 처리

sandbox 화면은 Core가 계좌·권한 확인 모달과 안전한 재시도를 처리합니다. all 프론트는 개발자가 SDK 결과를 보고 UX를 연결합니다.

- `result.requiresAccountAction`, `result.accountActionUrl`로 Core의 확인 화면에 연결합니다.
- 별도 사용자 클릭에서 `coders.openAccountWindow(url)`를 호출하거나, SDK가 검증한 URL을 그대로 새 탭 링크로 제공합니다.
- 창 확인 결과 `checked`는 확인 알림이며 결제 성공·잔액 보증이 아닙니다.
- 접수 전 거부는 사용자의 재시도 동작에 `result.retry()`를 연결할 수 있습니다. SDK는 확인 창을 닫았다는 이유만으로 유료 요청을 자동 실행하지 않습니다.
- 전송 예외의 `error.retry()`도 기존 키·본문을 유지합니다.

현재 SDK의 `openAccountWindow()`는 URL의 기존 쿼리를 채널 값으로 교체합니다. 엔드포인트별 예산을 쓰는 경우 `endpoint` 정보가 빠져 확인 금액이 프로젝트 기본 예산을 기준으로 표시될 수 있습니다. 정확한 URL을 유지해야 할 때는 반환된 `accountActionUrl`을 그대로 새 탭 링크로 연결하세요. 프론트 연동의 핵심 규약은 이 절의 [프론트 처리](https://docs.coders.kr/#frontend)에 있습니다.

공통 `/c` 칩은 `/run`과 all의 HTML 페이지에 Core가 제공합니다. 직접 잔액 조회 코드를 넣거나 칩에 계좌 키를 전달할 필요가 없습니다. all 프로젝트 코드는 칩의 Coders 출처 iframe 안에 있는 계좌 정보를 직접 읽을 수 없습니다.

## 8. 현재 지원 범위 확인

| 항목 | 현재 상태 |
| --- | --- |
| 공개 GitHub 저장소 + `coders.json` | 지원 |
| 비공개 저장소·명세 없는 자동 감지 | 미지원 |
| 단일 Python ASGI 파일, 소스 최대 131,072자 | 지원 |
| 임의 패키지 설치·빌드·다중 파일 Python 패키지·Dockerfile | 미지원 |
| Git submodule·LFS·심볼릭 링크 | 미지원 |
| 정적 프론트 | 기본 최대 10 MiB·256파일. `api`, `_coders` 최상위 경로는 예약 |
| GitHub 아카이브 | 기본 최대 20 MiB, 최대 4,096항목. 실행 준비 단계에서 코드를 실행하지 않음 |
| sandbox의 임의 JavaScript 프론트 | 미지원. `.coders-ui.json` 사용 |
| GitHub 명세의 `env`·비밀값 주입 | 미지원. 비밀값을 코드나 공개 폴더에 넣는 방식으로 대체하지 않음 |
| OpenAPI | 일반 엔드포인트 등록 API에서 선택적으로 지원. 현재 `coders.json`에는 `openapi` 필드가 없음 |
| 실행 후 컨테이너의 백그라운드 작업 유지 | 미지원 |
| 기본 HTTP 요청·응답 크기 | 각각 1 MiB. 실제 운영 설정에 따라 달라질 수 있음 |

하위 파일 경로에는 빈 경로, 절대 경로, `.`·`..` 경로 요소, `?`, `#`, 역슬래시를 사용하지 않습니다. 공개 폴더 밖의 파일은 프론트로 제공하지 않습니다.

## 9. 호환 완료 점검

- [ ] 루트에 유효한 `coders.json`이 있고, 전체 커밋 해시로 접근한다.
- [ ] 명세의 파일·경로·메서드와 실제 `app`의 라우트가 맞는다.
- [ ] 추가 설치·로컬 모듈·영속 프로세스에 의존하지 않는다.
- [ ] sandbox를 지원한다면 선언형 화면이 있고, 해당 작업은 JSON을 반환한다.
- [ ] all 프론트의 리소스는 같은 출처에서 제공하며 계좌 비밀 키를 포함하지 않는다.
- [ ] 예산에 접수 비용·컴퓨팅 예약·하위 작업 비용을 포함했다.
- [ ] 필요한 송금 권한을 선언하고, 거절·철회도 처리한다.
- [ ] 하위 호출은 현재 계좌 키와 작업별 키를 사용하고 정책을 완화하지 않는다.
- [ ] 준비 중 202, 잔액 부족 402, 권한 부족 403을 각각 처리한다.
- [ ] 결과 불명 재전송과 명시적인 새 실행을 구분해 중복 지급을 방지한다.

관련 주제: [GitHub 준비](https://docs.coders.kr/#github) · [계좌·예산](https://docs.coders.kr/#budget) · [권한](https://docs.coders.kr/#permissions) · [오류·재시도](https://docs.coders.kr/#errors).

[Core v2 OpenAPI](https://core-v2.coders.kr/openapi.json)에서 API 경로와 입력 형식을 확인할 수 있습니다.
