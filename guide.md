# Coders Core v2 호환 개발 가이드

실행할 코드는 공개 GitHub 저장소에 두고 전체 40자리 커밋 해시로 호출합니다.
루트의 `coders.json`이 코드·엔드포인트 연결·예산·요청 권한을 선언합니다.
직접 코드 업로드와 변경 가능한 엔드포인트 등록은 지원하지 않습니다.


이 가이드는 Core 0.6의 공개 실행 규약을 설명합니다.

## 연동 구조

```text
공개 GitHub 저장소 + 40자리 커밋 + coders.json
  → 최초 접속 시 명세 검증·아티팩트 준비
  → 사용자 로그인·프로젝트 연결·권한 동의
  → 사용자별 계좌·권한·데이터 영역에서 실행
```

같은 버전의 코드는 한 번 보관하고 함께 참조합니다. 사용자별 잔액·권한·저장 데이터는
분리합니다. 로그인은 기존 coders.kr 인증을 재사용하며, 계좌와 원장은 Core v2가 관리합니다.
개발자는 일반 ASGI 코드를 작성하고, Core는 실행 비용과 자원 호출을 처리합니다.

[공개 예제 실행하기](https://api.coders.kr/coders-kr/coders-github-example/443c957a547d890891d1365ab31d0a5794b4229e) · [예제 저장소](https://github.com/coders-kr/coders-github-example)

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
    "analyze": {"file": "api/analyze.py", "budget": "11.000"}
  },
  "permissions": []
}
```

`frontend`는 선택이며 파일 엔드포인트는 Python ASGI의 `app`을 제공합니다.
공식 자원을 직접 연결할 때는 `file` 대신 `endpoint: "coders-openai"` 등을 사용합니다.
`file`과 `endpoint`를 동시에 지정하지 않습니다. 파일 경로는 레포 내부 상대 경로입니다.
엔드포인트별 `budget`이 없으면 `request_budget`을 사용하며 기본값은 30원입니다.
최소 컴퓨팅 예약과 요청 요금을 확보할 수 있어야 코드가 실행됩니다.

```python
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class Input(BaseModel):
    text: str

@app.post("/")
def analyze(body: Input):
    # 계좌 키나 계좌 생성·폐쇄 코드는 필요하지 않습니다.
    return {"characters": len(body.text)}
```

## GitHub 버전 실행

```text
프로젝트 첫 방문:
https://api.coders.kr/{owner}/{repo}/{40자리-commit}

엔드포인트:
https://api.coders.kr/{owner}/{repo}/{40자리-commit}/analyze
```

처음 접속하면 Coders가 공개 저장소를 다운로드하고 명세를 검증합니다.
개발자 빌드 스크립트는 실행하지 않습니다. API 첫 호출은 준비 중 `202`와
`execution_started: false`, 상태 URL을 반환할 수 있습니다.
준비가 완료되면 같은 본문·멱등성 키로 다시 호출합니다.

외부 백엔드 호출자는 `Coders-Grant` 계좌 인증, `Coders-Budget` 원화 상한,
`Idempotency-Key`를 전달합니다. `Coders-Trust`는 지원하지 않습니다.
사용자 기본 계좌 키에 해당 프로젝트의 활성 연결이 있으면 승인된 프로젝트 계좌를 사용합니다.
실행 중인 코드가 다른 프로젝트를 호출할 때는 자신의 실행 영역과 권한을 계속 상속합니다.

브랜치·태그·latest는 실행 버전으로 사용하지 않습니다. 새 커밋은 새 배포이며
사용자 연결과 권한이 자동으로 새 배포로 옮겨가지 않습니다.
같은 커밋의 코드·명세·예산을 수정하는 공개 API는 없습니다.

## 예산과 계좌

금액은 실제 원화(KRW)입니다. 내부 계산은 소수점 여섯 자리, 화면 표시는 세 자리입니다.
API 금액은 `"11.000"`처럼 문자열로 지정할 수 있습니다.

사용자가 목표 잔액 100원을 선택하면 처음 허용할 때 기본 계좌에서 프로젝트 계좌를
100원까지 채웁니다. 한국 시간 자정마다 부족분만 보충합니다. 40원이 남았다면 60원을
옮기며, 100원 이상이면 옮기지 않습니다. 추가 할당한 미사용 잔액도 유지합니다.
기본 계좌가 부족하면 보충되지 못한 금액이 남을 수 있습니다.
목표 잔액은 매일 쓸 수 있는 금액의 상한이 아닙니다.

요청 예산은 최대 배정액이며 가격이 아닙니다. 예산 안에서 컴퓨팅·자원 사용량과
승인된 송금을 지출하고, 종료 후 남은 금액을 반환합니다. 실제 비용보다 예산이 크면
요청 시작 시 더 많은 잔액이 필요할 수 있습니다. 엔드포인트별로 적정 예산을 선언하세요.

계좌 분할과 종료는 Core 내부 동작입니다. 실행 코드가 계좌 키를 받거나 하위 계좌를
명시적으로 만들고 닫을 필요가 없습니다. 저장소 예약 같은 장기 자원도 내부에서 관리합니다.

## 권한과 사용자 동의

기본은 사용자·프로젝트별 격리입니다. 직접 외부 네트워크는 차단하며,
자기 데이터 영역의 계산·저장에는 별도 외부 전송 권한이 필요하지 않습니다.
실제 컴퓨팅·저장 비용은 실행 예산에서 지출합니다.

명세의 선택적 `permissions`는 다음 권한을 요청할 수 있습니다.

| 권한 | 허용 범위 |
|---|---|
| `transfer` | 1원 단위 송금, 송금자 정보 비공개, 한국 시간 자정 합산 지급 |
| `transfer-precise` | 소수점 송금과 즉시 지급 |
| `openai` | 공식 OpenAI 연결을 통한 데이터 전송 |
| `network` | 실행 코드의 직접 외부 통신; 사용자 데이터 반출 가능 |
| `frontend` | 개발자 HTML·JavaScript 실행; 입력 데이터 접근·반출 가능 |

사용자는 첫 연결에서 요청된 권한을 선택합니다. `all`은 위 다섯 권한을 한 번에
승인하는 선택지이며 별도 신뢰 모드나 권한 검사 우회가 아닙니다.
개별 작업 승인, 기간·반복 한도, 데이터 공유 승인은 기존 권한 API를 따릅니다.
공식 엔드포인트라고 해서 외부 전송을 자동 허가하지 않습니다.

`frontend`를 허용하지 않으면 Coders가 `.coders-ui.json`을 렌더링합니다.
사용자가 허용한 프론트 JavaScript의 행동을 백엔드 네트워크 격리로 통제할 수는 없습니다.
직접 네트워크, 프론트 실행, 송금은 각각 별도 승인입니다.

## 실행 코드와 프론트 연동

Core는 실행마다 `CODERS_URL`이라는 로컬 자원 중개 주소를 제공합니다.
이 주소로 보내는 요청은 현재 실행에 자동으로 귀속됩니다.
실행 코드에는 계좌 비밀 키를 전달하지 않습니다.

```python
import os
import httpx

async def child_call():
    # 고정 커밋 엔드포인트를 평범한 HTTP 요청으로 호출합니다.
    async with httpx.AsyncClient(base_url=os.environ["CODERS_URL"]) as client:
        return await client.post(
            "/github/owner/repo/0123456789012345678901234567890123456789/analyze",
            headers={"Idempotency-Key": "analyze-document"},
            json={"text": "하위 호출"},
        )
```

브로커가 인증을 붙이고 Core가 하위 실행 예산을 배정합니다.
격리된 코드가 아직 준비되지 않은 커밋을 호출하면 `403 deployment_not_prepared`로 거부합니다.
GitHub 다운로드도 외부 통신이므로 사용자가 그 버전을 먼저 준비하거나 `network`를 승인해야 합니다.
이미 준비된 불변 버전의 호출과 준비 상태 조회에는 외부 통신 권한이 필요하지 않습니다.
예산을 생략하면 엔드포인트 명세의 예산과 현재 가용액 중 작은 값을 사용합니다.
공식 자원 호출에서 예산을 생략하면 현재 가용액을 상한으로 사용합니다.
필요하면 `Coders-Budget`으로 더 작은 한도를 지정할 수 있습니다.
이 한도는 지출액이 아닌 최대 배정액입니다. 남은 금액은 종료 후 반환됩니다.

`/v1/accounts/split`, `/v1/accounts/close`는 공개·실행 코드 API가 아닙니다.
일반 실행 계좌는 Core가 만들고 닫습니다. 저장소 예약 같은 장기 자원도 내부에서 관리합니다.
다른 계좌 키를 브로커에 제공해 실행 주체를 바꿀 수 없습니다.

### 프론트 처리

기본 화면은 Coders의 `/run`입니다. `public/.coders-ui.json`에 입력과 액션을 선언하며,
개발자 JavaScript 없이 실행할 수 있습니다.

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

`frontend` 권한을 허용한 사용자는 프로젝트 전용 도메인에서 개발자 HTML·JavaScript를
실행합니다. 이 프론트에서는 Core의 ES 모듈을 사용할 수 있습니다.

```html
<script type="module">
  import { createClient } from '/_coders/sdk.js';
  const coders = createClient();
  const result = await coders.request('/api/analyze', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text: '안녕하세요' }),
  });
  console.log(result.status, result.data);
</script>
```

계좌 키나 로그인 토큰을 프론트에 넣지 않습니다. 로그인·연결·공통 `/c` 메뉴는 Core가 제공합니다.
SDK는 HTTP 오류도 `status`, `data`, `executionId`, `idempotencyKey`를 가진 결과로 반환합니다.
`result.retry()`는 원래 본문과 멱등성 키를 유지합니다. 전송 예외에도 `error.retry()`가 있습니다.

402이면 `requiresAccountAction`과 `accountActionUrl`을 확인합니다.
사용자 클릭 안에서 `coders.openAccountWindow(result.accountActionUrl)`를 호출하고,
승인 전 거부였던 요청은 같은 키로 재시도합니다. 이 SDK 함수 자체가 유료 요청을 자동 재실행하지는 않습니다.
Core의 기본 화면은 추가 할당 승인 후 모달을 닫고 원래 요청을 같은 키로 자동 재시도합니다.
직접 프론트를 구현할 때도 실행 여부를 확인하고, URL은 Core가 제공한 것만 사용하세요.

창 열기 결과는 `checked`, `closed`, `blocked`입니다. `blocked`이면 반환된 `url`을
새 탭 링크로 제공할 수 있습니다. `checked`는 화면 확인 알림이며 결제 성공 보증이 아닙니다.
SDK는 출처·창·채널을 검증합니다. 창을 닫았다는 이유만으로 새 키로 요청하지 마세요.

## 오류와 재시도

| 응답 | 처리 |
|---|---|
| `202`, `execution_started: false` | 준비 완료를 기다린 뒤 같은 요청을 다시 보냅니다. |
| `402 allocation_required` | Core가 반환한 확인 URL로 추가 할당을 승인합니다. |
| `403 permission_required` | Core의 권한 화면에서 동작을 승인합니다. |
| `403 project_permission_required` | 해당 프로젝트 연결과 선언 권한을 확인합니다. |
| `409 idempotency_conflict` | 같은 키로 본문·입력 조건을 바꾸지 않습니다. |
| 통신 오류·결과 불명 | 새 키로 즉시 재실행하지 않고 같은 요청 결과를 확인합니다. |

승인 전 거부는 같은 키로 재시도할 수 있습니다. 실행된 요청은 같은 키로 기존 결과를
재생합니다. 실패한 실행의 새 실행은 새 키를 사용하며 이미 발생한 비용은 반환하지 않습니다.
부모 요청 종료·브라우저 연결 종료는 접수된 자녀 작업의 취소가 아닙니다.

## 지원 범위

현재 공개 GitHub 저장소·명세 version 1·단일 Python ASGI 파일·정적 프론트를 지원합니다.
임의 빌드 명령·추가 패키지 설치·submodule·LFS·심볼릭 링크는 지원하지 않습니다.
코드 아티팩트는 한 번 보관하고 사용자별로 참조합니다. 계좌·권한·데이터는 공유하지 않습니다.
코드 해시는 안전성 보증이 아니며 런타임과 공급자 요율은 플랫폼 운영 정책을 따릅니다.

파일 엔드포인트의 Python 소스는 최대 131,072자입니다. 저장소 다운로드는 최대 20 MiB,
정적 프론트 합계는 최대 10 MiB·256개 파일로 제한합니다. 런타임에 없는 패키지를
설치하는 빌드 과정은 없습니다. FastAPI·httpx 등 제공 패키지 범위 안에서 작성하세요.

엔드포인트의 선택적 `openapi`에는 저장소 내부 OpenAPI JSON 파일 경로를 지정할 수 있습니다.
문서는 코드와 같은 커밋에 고정되며, 대시보드 상세에서 Swagger UI로 요청을 보낼 수 있습니다.
공식 OpenAI 자원은 공급자 설정과 사용자 `openai` 승인이 모두 필요합니다.


## 호환 체크리스트

- 저장소 루트에 version 1 `coders.json`을 두고, 전체 40자리 커밋으로 호출합니다.
- Python 파일은 ASGI `app`을 제공하고 파일·명세·프론트를 같은 커밋에 둡니다.
- 필요한 예산과 권한만 선언합니다. 새 커밋의 사용자 연결과 권한은 별개입니다.
- 실행 코드의 자원 호출은 `CODERS_URL`로 보냅니다. 계좌 생성·폐쇄·키 처리는 넣지 않습니다.
- 기본 격리에서는 외부 통신과 개발자 JavaScript를 실행하지 않습니다.
- 송금·OpenAI·직접 네트워크·프론트 권한은 각각 승인받습니다.
- 202·402·403과 실행 여부를 확인하고, 재시도는 같은 본문·멱등성 키를 유지합니다.
- 사용자 계좌·데이터·권한을 다른 사용자의 실행과 공유하지 않습니다.
- 직접 프론트를 제공하면 필요한 정적 자산을 함께 넣고, 계좌 키를 브라우저에 저장하지 않습니다.
