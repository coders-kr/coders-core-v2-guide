# Coders Core v2 개발 가이드

Coders는 공개 GitHub 저장소의 고정 커밋을 사용자의 계좌와 데이터 리소스에서 실행합니다.
저장소 루트의 `coders.json`이 코드·엔드포인트·예산·요청 권한을 선언합니다.

화면의 워크스페이스는 앱을 여는 데이터 리소스입니다. 기본 앱 주소는 사용자×앱별 마지막으로 연 워크스페이스를 엽니다.
처음 방문하거나 해당 공간의 접근 권한·연결이 유효하지 않으면 워크스페이스 목록을 표시합니다.
공간을 명시한 주소는 그 공간을 열고, 실제 앱 화면이 열리면 마지막 공간을 갱신합니다.
같은 앱의 새 커밋 버전도 이 기록을 사용하며 요청한 커밋 버전으로 실행합니다.
비용은 선택한 워크스페이스의 공동 계좌에서 처리합니다.
계좌·워크스페이스·앱 설정은 왼쪽 앱 목록이 있는 전체 화면 대시보드에서 관리합니다.
워크스페이스 카드에는 공동 잔액·채우기가 표시되며, 모바일에서는 메뉴 버튼으로 목록을 엽니다.

## 연동 구조

```text
GitHub 저장소 + 전체 커밋 + coders.json
  → 명세 검증과 버전 준비
  → 사용자 로그인·리소스 선택·권한과 충전 목표 동의
  → 선택한 워크스페이스의 데이터와 공동 계좌에서 실행
```

앱은 GitHub 저장소 ID, 버전은 전체 40자리 커밋으로 식별합니다.
리소스는 앱에 소속된 독립된 워크스페이스입니다. 같은 앱의 버전들은 해당 데이터와 공동 잔액을 사용합니다.
여러 사용자는 워크스페이스를 공유하고 공동 계좌로 실행 비용을 지불합니다.
로그인은 coders.kr OIDC, 계좌와 권한 집행은 Core가 담당합니다.

[공개 예제](https://api.coders.kr/coders-kr/coders-github-example/443c957a547d890891d1365ab31d0a5794b4229e) · [예제 저장소](https://github.com/coders-kr/coders-github-example)

## 최소 프로젝트

```text
coders.json
api/analyze.py
public/index.html
public/.coders-ui.json
```

```json
{
  "version": 1,
  "name": "텍스트 분석",
  "frontend": {"directory": "public"},
  "endpoints": {
    "analyze": {"file": "api/analyze.py", "budget": "11.00"}
  },
  "permissions": []
}
```

```python
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class Input(BaseModel):
    text: str

@app.post("/")
def analyze(body: Input):
    # 실행 인증과 비용 정산은 Core가 담당합니다.
    return {"characters": len(body.text)}
```

코드 엔드포인트는 `file`과 선택적 `path`, `methods`, `budget`, `openapi`를 사용합니다.
기본 경로는 `/`, 메서드는 `["POST"]`입니다. `openapi`는 같은 저장소의 JSON 파일입니다.
공식 자원 참조는 `{"endpoint":"coders-openai","budget":"5.00"}` 형식으로 선언하고 자원의 메서드와 요청 계약을 따릅니다.
엔드포인트별 예산의 기본값은 `request_budget`이며, 생략 시 30원입니다.

`frontend`와 `endpoints` 중 하나 이상을 선언합니다. 프론트 디렉토리는 `index.html`을 포함합니다.
파일 경로는 저장소 기준 상대 경로이고, 프론트 디렉토리의 파일들이 공개 파일입니다.

## GitHub 버전 실행

```text
앱 접속:
https://api.coders.kr/{owner}/{repo}/{40자리-commit}

엔드포인트:
https://api.coders.kr/{owner}/{repo}/{40자리-commit}/analyze
```

첫 접속은 준비 화면에서 저장소·커밋 게시 여부·명세를 확인하고 실행 아티팩트를 보관합니다.
API 준비 중 응답은 `202`, `execution_started: false`와 상태 URL입니다.
준비 완료 후 같은 키와 본문으로 실행을 요청합니다.

외부 API 호출은 다음 헤더를 사용합니다.

```http
Coders-Grant: <계좌 키>
Coders-Budget: 30
Idempotency-Key: <이 요청의 고유 키>
```

사용자 기본 계좌 키는 활성 앱 연결을 선택합니다. 여러 리소스가 있으면
`Coders-Resource: <리소스 ID>`로 선택합니다. 인증은 계좌 키와 사용자 연결에서 확인합니다.
같은 앱의 게시된 새 버전은 기존 동의 범위 안에서 실행하고, 새 기능 권한은 추가 동의를 받습니다.

## 예산과 계좌

```text
기본 계좌 → 워크스페이스 공동 계좌 → 실행 계좌 → 하위 실행·자원 예약
```

목표 금액은 직접 입력하거나 `100원 · 500원 · 1,000원` 버튼으로 채웁니다.
소유자는 처음 설정할 때와 한국 시간 자정에 자신의 기본 계좌에서 공동 목표 잔액까지 부족분을 채웁니다.
목표 계산은 가용액과 실행 중 예약액을 포함합니다. 수동 충전액과 미사용 잔액은 유지합니다.
기본 계좌가 부족하면 가능한 금액을 충전하고 부족분을 표시합니다.

Core는 요청 예산을 예약하고 실제 사용액을 정산한 뒤 남은 금액을 반환합니다.
코드 실행에는 요청 접수 비용과 컴퓨팅 예약을 확보할 수 있는 예산을 지정합니다.
금액은 KRW이며 내부 여섯 자리, 화면 두 자리 정밀도를 사용합니다.

연결 해제는 개인의 접속을 종료하며 공동 잔액은 워크스페이스에 유지됩니다.
접수된 자녀 실행과 보관 계약은 자신의 예산과 수명에 따라 정산합니다.

## 권한과 사용자 동의

| 권한 | 허용 동작 |
|---|---|
| `transfer` | 정수 원 단위 송금, 송금자 비공개, 한국 시간 자정 합산 지급 |
| `transfer-precise` | 소수점 금액 즉시 송금 |
| `openai` | 공식 OpenAI 중개 API를 통한 외부 전송 |
| `network` | 컨테이너 직접 외부 통신 |
| `frontend` | 개발자 HTML·JavaScript 실행 |

개발자는 `permissions`로 기능을 요청하고 사용자는 Core에서 승인합니다.
`all`은 다섯 권한을 함께 선택합니다. 각 동작은 예산과 승인 검사를 받습니다.

리소스 소유자는 Core에서 사용자에게 읽기·수정 접근을 주고 앱 기능 상한을 정합니다.
호출자는 그 범위 안에서 사용할 기능과 비용을 승인합니다.
공유·철회는 Core의 리소스 관리 화면과 사용자 세션 API에서 처리합니다.

`/account`의 워크스페이스 카드에서 공동 잔액을 확인하고 채우기와 설정을 엽니다.
리소스 목록과 앱 설정·첫 동의 화면은 리소스를 카드로 나열합니다.
리소스 카드를 누르면 해당 데이터 범위로 앱을 실행합니다. 카드의 `⋯`에서 공유와 권한을 관리합니다.

## 실행 코드와 프론트 연동

### 백엔드 호출

실행 코드는 `CODERS_URL`을 자원 API의 기준 주소로 사용합니다.
브로커가 현재 사용자·앱·리소스·실행 계좌 문맥으로 인증과 예산을 전달합니다.

```python
import os
import httpx

async def read_notes():
    # 저장 요청은 선택된 리소스의 데이터 범위에 귀속됩니다.
    async with httpx.AsyncClient(base_url=os.environ["CODERS_URL"]) as client:
        return await client.get(
            "/store/my_app/notes",
            headers={"Idempotency-Key": "read-notes"},
        )
```

저장은 앱 리소스를 선택한 실행에서 호출합니다. 공유는 리소스 읽기·수정 권한을 따릅니다.
생성과 연장은 `retention_seconds`로 기간을 지정하고, DB 비용과 보관료는 호출 예산에서 지출합니다.
삭제 시 미사용 보관료는 실제 구매자 계좌로 환불합니다.

하위 코드 주소도 같은 문맥을 사용합니다. 코드 예산의 기본값은 엔드포인트 명세와 현재 가용액 중 작은 값입니다.
공식 자원 호출은 가용액을 기본 상한으로 사용하고 `Coders-Budget`으로 금액을 지정할 수 있습니다.
격리 실행의 하위 코드 버전은 사용자가 먼저 준비합니다.

### 프론트 처리

기본 화면은 Core가 `.coders-ui.json`을 렌더링합니다.

```json
{
  "title": "텍스트 분석",
  "actions": [{
    "title": "분석하기",
    "endpoint": "analyze",
    "fields": [{"name": "text", "label": "분석할 내용", "multiline": true}]
  }]
}
```

`frontend` 승인 시 개발자 프론트를 사용자·리소스·커밋별 출처의 iframe에서 실행합니다.
바깥 Core 화면과 `/c` 칩은 계좌·리소스·권한을 관리합니다.

```javascript
import { createClient } from '/_coders/sdk.js';
const coders = createClient();

const result = await coders.request('/api/analyze', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ text: '분석할 문장' })
});
```

SDK는 결과, 상태, 실행 ID, 멱등성 키, Core 확인 URL, 동일 요청의 `retry()`를 반환합니다.
`openAccountWindow(result.accountActionUrl)`는 사용자 클릭에서 Core 확인 창을 엽니다.
완료 알림의 출처·창·채널을 확인하고 결과를 호출자에게 반환합니다.
재시도 여부는 실행 상태와 아래 멱등성 규칙에 따라 결정합니다.

프론트 실행 권한과 직접 네트워크 권한은 각각 승인합니다.
개발자 프론트를 신뢰할 때는 입력 데이터 접근과 외부 전송 능력도 함께 고려합니다.

## 오류와 재시도

| 응답 | 후속 동작 |
|---|---|
| 202 준비 중 | 같은 키·본문으로 준비 완료 후 호출 |
| 402 잔액·예산 부족 | Core 충전 확인 URL에서 금액 확인 |
| 403 `permission_required` | 요청 ID로 Core에서 외부 동작 승인 |
| 403 `resource_required` | 실행할 앱 리소스 선택 |
| 403 `project_permission_required` | 연결·동의·철회 상태 확인 |
| 409 멱등성 충돌 | 동일 키의 입력과 실행 결과 확인 |
| 503 `database_unavailable` | DB 복구 후 같은 키·본문으로 확인 |
| 503 `ledger_busy` | 충돌 해소 후 같은 키·본문으로 확인 |
| 통신 오류·결과 불명 | 기존 실행과 외부 작업 기록 확인 |

접수 전 거부는 같은 요청으로 재시도합니다. 접수된 요청은 같은 키로 기존 결과를 재생합니다.
종료된 실패 요청을 새로 실행할 때는 새 키를 사용합니다. 이미 발생한 사용 비용은 정산됩니다.
기본 선언형 화면은 승인 후 안전한 재시도를 자동 처리합니다.

## 지원 범위

- 공개 GitHub 저장소, 전체 40자리 커밋, `coders.json` version 1.
- 단일 Python ASGI 파일과 플랫폼 설치 패키지.
- 일반 파일·디렉토리의 정적 프론트.
- 선택적 저장소 내부 OpenAPI JSON과 Swagger UI 호출.
- 앱별 독립 워크스페이스, 멤버 읽기·수정 권한, 워크스페이스 공동 계좌.
- 원화 여섯 자리 정산, 목표 잔액 충전, Polar 결제.

실행 아티팩트와 명세는 커밋에 고정되고, 런타임·자원 요율은 플랫폼 운영 설정으로 결정합니다.
운영은 단일 Core 저장소 제어와 요청별 Docker 실행을 사용합니다.

## 호환 체크리스트

1. 공개 저장소 루트에 `coders.json`을 둡니다.
2. 코드 파일에 ASGI `app`을 제공하고 필요한 패키지를 확인합니다.
3. 실행·자원 사용을 감당하는 요청 예산을 선언합니다.
4. 외부 동작과 개발자 프론트에 필요한 권한을 선언합니다.
5. 저장은 선택한 리소스 문맥과 `retention_seconds`를 사용합니다.
6. 자원 호출은 `CODERS_URL`, 프론트 호출은 프로젝트 SDK를 사용합니다.
7. 준비 중·잔액 부족·승인·결과 불명 응답을 처리합니다.
8. 동일 작업의 키와 본문을 보존하고 실제 사용자 흐름을 확인합니다.
