# Coders Core v2 개발 가이드

Coders는 공개 GitHub 저장소의 고정 커밋을 리소스의 서버·데이터·공동 계좌에서 실행합니다.
저장소 루트의 `coders.json`이 코드·엔드포인트·예산·요청 권한을 선언합니다.

화면의 워크스페이스는 앱을 여는 데이터 리소스입니다. 기본 앱 주소는 사용자×앱별 마지막으로 연 워크스페이스를 엽니다.
처음 방문하거나 해당 공간의 접근 권한·연결이 유효하지 않으면 워크스페이스 목록을 표시합니다.
공간을 명시한 주소는 그 공간을 열고, 실제 앱 화면이 열리면 마지막 공간을 갱신합니다.
같은 앱의 버전은 리소스의 데이터를 사용하며, 소유자가 리소스의 현재 실행 버전을 선택합니다.
비용은 선택한 워크스페이스의 공동 계좌에서 처리합니다.
계좌·워크스페이스·앱 설정은 왼쪽 앱 목록이 있는 전체 화면 대시보드에서 관리합니다.
워크스페이스 카드에는 공동 잔액·채우기가 표시되며, 모바일에서는 메뉴 버튼으로 목록을 엽니다.

## 연동 구조

```text
GitHub 저장소 + 전체 커밋 + coders.json
  → 명세 검증과 버전 준비
  → 사용자 로그인·리소스 입장
  → 소유자의 실행 버전·공통 권한·충전 목표 설정
  → 선택한 워크스페이스의 데이터와 공동 계좌에서 실행
```

앱은 GitHub 저장소 ID, 버전은 전체 40자리 커밋으로 식별합니다.
리소스는 앱에 소속된 독립된 워크스페이스입니다. 같은 앱의 버전들은 해당 데이터와 공동 잔액을 사용합니다.
여러 사용자는 워크스페이스를 공유하고 공동 계좌로 실행 비용을 지불합니다.
로그인은 coders.kr OIDC, 계좌와 권한 집행은 Core가 담당합니다.

[공개 예제](https://api.coders.kr/cykim8811/coders-http-example/6a01565e841de03f4276a8770c63227c896f7175) · [예제 저장소](https://github.com/cykim8811/coders-http-example)

## 최소 프로젝트

```text
coders.json
Dockerfile
requirements.txt
api/main.py
public/index.html
public/.coders-ui.json
.github/workflows/coders-build.yml
```

```json
{
  "version": 2,
  "name": "텍스트 분석",
  "frontend": {"directory": "public"},
  "endpoints": {
    "analyze": {"path": "/analyze", "methods": ["POST"], "budget": "11.00"}
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

@app.post("/analyze")
def analyze(body: Input):
    # 일반적인 HTTP 앱입니다. 비용·권한은 Core가 처리합니다.
    return {"characters": len(body.text)}
```

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY api ./api
USER 65534:65534
CMD ["sh", "-c", "exec uvicorn api.main:app --host 0.0.0.0 --port $PORT"]
```

`requirements.txt`에 `fastapi`, `uvicorn`과 앱 의존성을 선언합니다. Node.js·Express·Next.js 등도
같은 방식으로 Dockerfile에서 코드와 의존성을 준비하고 `PORT`에서 HTTP를 제공합니다.

### 공개 GitHub Actions 빌드

공개 레포의 `.github/workflows/coders-build.yml`이 GitHub-hosted runner에서 이미지를 빌드합니다.
이미지는 공개 GHCR 패키지 `ghcr.io/{owner}/{repo}:sha-{전체 커밋}`에 게시합니다.
패키지 이름을 별도로 사용하는 앱은 `coders.json`의 `image`에 태그 없는 GHCR 이름을 선언합니다.
새 GHCR 패키지는 설정 화면에서 Public으로 지정합니다.

워크플로는 `docker/build-push-action`으로 `linux/amd64` 이미지를 게시하고
`actions/attest-build-provenance`에 `subject-name`, 빌드 결과 `subject-digest`,
`push-to-registry: true`를 전달합니다. 권한은 `contents: read`, `packages: write`,
`id-token: write`, `attestations: write`입니다.

[실행 가능한 워크플로 예제](https://github.com/cykim8811/coders-http-example/blob/main/.github/workflows/coders-build.yml)

Core는 공개 레포 ID·게시 커밋·GitHub-hosted 빌드 증명을 확인한 후 이미지 digest를 고정합니다.
검증된 이미지를 준비하고 첫 접속을 진행합니다. 빌드가 준비되지 않았으면 준비 상태에 원인을 표시하며,
다시 준비할 수 있습니다. 빌드는 개발자의 GitHub Actions에서 수행합니다.
압축 이미지 용량의 기본 상한은 512 MiB입니다.

### HTTP 실행 계약

- `0.0.0.0:$PORT`에서 HTTP 서버를 실행합니다. 현재 포트는 8080입니다.
- 실행 사용자는 UID/GID `65534`이며, 루트 파일시스템은 읽기 전용입니다.
- `/tmp`는 실행 환경에 귀속된 64 MiB 임시 영역입니다. 영속 데이터는 `DATABASE_URL`로 저장합니다.
- 이미지의 추가 `VOLUME` 선언은 허용된 저장 범위에 포함되지 않습니다.
- Core 자원 호출은 `CODERS_URL`, PostgreSQL은 `DATABASE_URL`을 사용합니다.
- 계좌·관리자·공급자 비밀키는 Core가 관리합니다.

리소스마다 선택된 버전의 HTTP 서버를 실행합니다. 같은 리소스의 여러 사용자가 HTTP와
WebSocket을 통해 동시에 접속하며, 메모리와 DB 연결 풀을 함께 사용합니다.
Core는 리소스 간 실행 환경·네트워크·데이터·자금을 격리합니다.

HTTP 이미지 서버의 HTTP 요청과 WebSocket 연결에는 검증한 실행 문맥을 전달합니다.

| 헤더 | 값 |
| --- | --- |
| `Coders-User-Id` | 현재 요청의 Coders 사용자 ID |
| `Coders-Resource-Id` | 현재 리소스 ID |
| `Coders-Resource-Role` | 해당 사용자가 리소스 소유자이면 `owner`, 다른 멤버이면 `member` |

Core는 클라이언트가 보낸 신원·역할 헤더를 제외하고 현재 원장에서 확인한 값을 주입합니다.
앱은 Core가 중계한 요청의 사용자 ID와 역할을 바탕으로 내부 권한을 집행합니다.
리소스의 멤버는 앱에 같은 데이터 접근 권한을 제공하며, 리소스 소유자가 공통 실행 권한을 관리합니다.

소유자는 **자동 중지**와 **계속 실행**을 선택합니다. 자동 중지는 활성 요청·연결이 없어진 뒤
기본 30초의 유휴 구간에서 종료하고, 계속 실행은 접속이 없는 시간도 공동 계좌로 실행합니다.
실행 환경은 재시작될 수 있으며 영속 상태는 DB에 저장합니다.

Core는 리소스 계좌의 서버 예산으로 실행을 유지하고 내부 예산 갱신 시 DB 연결을 정리합니다.
SQLAlchemy는 `pool_pre_ping=True`, Node.js `pg.Pool`은 유휴 연결의 `error` 처리를 구성합니다.
끊긴 연결은 새로 생성합니다. HTTP 응답은 최대 본문 크기 안에서 모아서 반환합니다.
기본 리소스당 동시 연결 한도는 32개입니다. 실행 용량 부족은 `503 sandbox_busy`입니다.

### Redis

리소스 소유자가 **Redis · 보관 및 실행**에서 활성화하면 HTTP 이미지 앱에 `REDIS_URL`을 제공합니다.
일반 Redis 클라이언트를 사용하며, 앱 이미지에 클라이언트 의존성을 설치합니다.

```python
import os
from redis.asyncio import Redis

redis = Redis.from_url(os.environ["REDIS_URL"], decode_responses=True)
await redis.set("greeting", "안녕하세요")
```

Redis는 앱 자동 중지와 별개로 실행되며 CPU·메모리 비용은 공동 잔액에서 지출합니다.
소유자는 실행·일시 중지·삭제를 관리합니다. 잔액 부족 시 실행을 멈추고 구매한 보관 기간 동안 파일을 유지합니다.
기본 데이터 메모리는 64 MiB이며 `noeviction`과 AOF 영속성을 적용합니다.
서버 재시작과 연결 갱신에 대응해 클라이언트 재연결을 구성합니다.
같은 리소스의 키·채널을 사용하며 관리·설정·복제·외부 이동 명령은 Core 서비스 ACL을 따릅니다.

### 앱 초기 관리자 지정

Docmost 같은 앱은 소유자가 처음 접속할 때 `Coders-Resource-Role: owner`와
`Coders-User-Id`를 사용해 초기 관리자를 지정합니다. 리소스 ID나 소유자 사용자 ID를
배포 설정에 고정할 필요가 없습니다.

```python
from fastapi import HTTPException, Request


def bootstrap_owner_id(request: Request) -> str:
    # Coders가 중계한 요청에서 검증한 소유자 신원을 확인합니다.
    if request.headers.get("coders-resource-role") != "owner":
        raise HTTPException(403, "리소스 소유자가 초기 설정을 완료해야 합니다.")
    return request.headers["coders-user-id"]
```

앱은 초기 설정 완료 여부와 관리자 계정을 리소스 DB에 원자적으로 저장합니다.
멤버가 먼저 방문하면 소유자의 초기 설정을 기다리는 화면을 표시합니다.
이후 관리자·편집자 등 앱 내부 역할은 앱 정책으로 관리합니다.
신원 헤더는 요청별로 읽으며, 리소스의 여러 사용자가 공유하는 프로세스 전역 값으로 보관하지 않습니다.

### WebSocket

HTTP 이미지에서 WebSocket 경로를 구현하고 엔드포인트에 `GET`을 선언합니다.

```json
"live": {"path": "/live", "methods": ["GET"], "budget": "11.00"}
```

서버는 일반 WebSocket 핸들러를 구현합니다. Python 이미지는 `fastapi`, `uvicorn`, `websockets`를
의존성으로 준비합니다.

```python
from fastapi import WebSocket, WebSocketDisconnect

@app.websocket("/live")
async def live(socket: WebSocket):
    await socket.accept()
    try:
        while True:
            await socket.send_text(await socket.receive_text())
    except WebSocketDisconnect:
        pass
```

앱 프론트에서는 프로젝트 세션으로 같은 출처의 `/api/live`에 연결합니다.

```javascript
const url = new URL('/api/live', location.href);
url.protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
const socket = new WebSocket(url);
socket.onmessage = event => console.log(event.data);
```

서버 클라이언트는 `wss://api.coders.kr/{owner}/{repo}/{commit}/live`를 사용하고,
`Coders-Grant`, `Coders-Budget`, `Idempotency-Key`, 필요시 `Coders-Resource` 헤더를 전달합니다.
배포 준비와 워크스페이스 연결을 완료한 뒤 접속합니다. 브라우저 세션 연결은 정확한 `Origin`을 검증합니다.
계좌 키는 서버 클라이언트의 헤더로 전달합니다. 재접속마다 새로운 멱등 키로 실행을 접수합니다.

HTTP와 WebSocket은 같은 리소스 서버를 사용합니다. 서버 실행 비용은 연결 수와 별도로
한 번 계량하고 리소스 공동 계좌에서 지출합니다. 내부 실행 예산 갱신 중에도 연결을 유지합니다.
기본 연결 최대 시간은 300초이며 앱은 재접속 후 DB에서 상태를 복원합니다.

텍스트·바이너리 메시지와 서브프로토콜을 지원하고, 메시지당 기본 최대 크기는 1 MiB입니다.
연결 전 예산 부족은 HTTP `402`, 실행 용량 부족은 `503`으로 거부합니다.
연결 후 예산 소진·권한 철회는 종료 코드 `1008`, 메시지 크기 초과는 `1009`,
최대 연결 시간·서버 종료는 `1001`로 연결을 닫습니다. 브라우저는 핸드셰이크의 오류 본문을
직접 읽을 수 없습니다. 계좌 확인과 채우기는 Coders 칩의 계좌 화면에서 처리합니다.
앱은 재접속 후 DB에서 상태를 복원합니다. 앱 작업의 중복 방지는 메시지의 작업 ID로 처리합니다.
연결 멱등 키는 연결 접수의 중복을 막습니다.

엔드포인트는 `path`, `methods`, `budget`, `openapi`를 선언합니다. 기본 경로는 `/`, 메서드는
`["POST"]`입니다. `openapi`는 같은 저장소의 JSON 파일입니다.
공식 자원 참조는 `{"endpoint":"coders-openai","budget":"5.00"}` 형식으로 선언합니다.
엔드포인트별 예산 기본값은 `request_budget`이며 생략 시 30원입니다.
`frontend`와 `endpoints` 중 하나 이상을 선언합니다. 프론트 디렉토리는 `index.html`을 포함합니다.
앱 기본 화면은 이 프론트 파일 또는 Core가 생성한 화면입니다. 컨테이너의 HTTP 응답은 선언한 엔드포인트 경로로 호출합니다.

단일 Python 파일을 실행하는 `version: 1`도 지원하며, `file`에 ASGI `app`을 정의한 파일을 지정합니다.

## GitHub 버전 실행

```text
앱 접속:
https://api.coders.kr/{owner}/{repo}/{40자리-commit}

엔드포인트:
https://api.coders.kr/{owner}/{repo}/{40자리-commit}/analyze
```

### 호스트별 경로와 인증

| 호스트 | 경로 | 용도·인증 |
| --- | --- | --- |
| `core-v2.coders.kr` | `GET /github/{owner}/{repo}/{commit}` | 로그인과 프로젝트 준비·접속 화면 |
| `core-v2.coders.kr` | `POST /github/{owner}/{repo}/{commit}/_prepare` | 명시적 준비. 로그인 세션과 CSRF 검증 |
| `core-v2.coders.kr` | `GET /github/{owner}/{repo}/{commit}/_status` | 공개 준비 상태 조회 |
| `api.coders.kr` | `GET /{owner}/{repo}/{commit}/_status` | 공개 준비 상태 조회 |
| `api.coders.kr` | `/{owner}/{repo}/{commit}/{endpoint}` | 계좌 키·예산·멱등성 키로 엔드포인트 호출 |
| 현재 앱 출처 | `/_coders/sdk.js`, `/api/{endpoint}` | 브라우저 SDK와 앱 세션 기반 호출 |

`api.coders.kr`의 앱 주소를 브라우저에서 HTML로 열면 Core의 준비·접속 화면으로 이동합니다.
명시적 `/_prepare`는 Core 확인 화면의 폼 요청이며 `csrf`와 준비 시도의 멱등 키인 `key`를 전달합니다.
준비 비용은 로그인한 사용자의 기본 계좌에서 지급합니다.
해당 요청은 `core-v2.coders.kr`의 로그인 호스트 검증을 받으며, `api.coders.kr`로 보내면
`403 invalid_host`가 반환됩니다.

외부 클라이언트는 공개 `/_status`로 상태를 조회하거나 계좌 인증으로 엔드포인트를 호출합니다.
아직 준비되지 않은 버전의 엔드포인트 호출은 아래 준비 응답을 반환합니다.
브라우저 SDK는 현재 앱 출처의 `/api/`를 사용하고 Core·API 도메인에는 직접 요청하지 않습니다.

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
소유자가 선택한 리소스 실행 버전과 API의 커밋이 일치해야 합니다. 버전 변경은 Core 설정에서 확정합니다.

## 예산과 계좌

```text
기본 계좌 → 워크스페이스 공동 계좌 → 실행 계좌 → 하위 실행·자원 예약
```

목표 금액은 직접 입력하거나 `100원 · 500원 · 1,000원` 버튼으로 채웁니다.
소유자는 처음 설정할 때와 한국 시간 자정에 자신의 기본 계좌에서 공동 목표 잔액까지 부족분을 채웁니다.
목표 계산은 가용액과 실행 중 예약액을 포함합니다. 수동 충전액과 미사용 잔액은 유지합니다.
기본 계좌가 부족하면 가능한 금액을 충전하고 부족분을 표시합니다.

HTTP 이미지 호출은 요청 접수 비용을 지불하고 리소스 공용 서버에 전달합니다.
서버는 공동 계좌에서 실행 예산을 별도로 확보하고 활성 시간을 한 번 계량합니다.
`Coders-Budget`은 요청 접수에 사용할 상한이며 공유 서버는 자신의 실행 예산으로 동작합니다.
공식 자원 참조와 하위 자원 호출은 지정된 자원 예산을 사용합니다.
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

첫 동의 화면의 매일 충전 목표 기본값은 100원입니다. 저장한 목표 잔액은 이후 설정에 유지됩니다.
리소스 소유자는 **기본 권한 허용**(앱이 명세에 요청한 권한), **모든 권한 허용**,
**커스텀 권한 설정** 중 선택합니다. 커스텀에서 개별 권한을 선택합니다.
개발자는 `permissions`로 기능을 요청하고 리소스 소유자가 Core에서 공통 실행 권한을 승인합니다.
`all`은 다섯 권한을 함께 선택합니다. 각 동작은 예산과 승인 검사를 받습니다.

리소스 소유자는 Core에서 멤버를 초대하고 앱의 실행 권한을 정합니다.
멤버별 읽기·수정 같은 내부 권한은 앱이 검증한 사용자 ID로 관리합니다.
공유·철회는 Core의 리소스 관리 화면과 사용자 세션 API에서 처리합니다.

`/account`의 워크스페이스 카드에서 공동 잔액을 확인하고 채우기와 설정을 엽니다.
리소스 목록과 앱 설정·첫 동의 화면은 리소스를 카드로 나열합니다.
리소스 카드를 누르면 해당 데이터 범위로 앱을 실행합니다. 카드의 `⋯`에서 공유와 권한을 관리합니다.

### 앱 이용료 받기

앱은 **리소스 공동 계좌에서 개발자의 Coders 계좌로 송금**하여 이용료를 받을 수 있습니다.
컴퓨팅·DB·Redis 등의 인프라 사용료는 Coders에 지급되고, 앱 이용료는 앱 코드가 정한
수취 계좌와 금액으로 지급됩니다. 개발자 수익 지급에는 일반 계좌 송금 API를 사용합니다.

1. 개발자는 자신의 `/account`에서 수취할 **계좌 ID**를 확인합니다. 계좌 ID는 입금 대상 식별자입니다.
2. `coders.json`의 `permissions`에 `transfer`를 선언합니다. 리소스 소유자는 Core 권한 화면에서 승인합니다.
3. 앱 서버가 `CODERS_URL`의 `/v1/accounts/transfers`를 호출합니다. Core가 현재 리소스의 권한·잔액·실행 예산을 검사합니다.
4. 일반 송금은 금액을 예약 정산 계좌로 옮긴 뒤 한국 시간 다음 자정에 수취 계좌별로 합산 지급합니다.

기존 `coders.json`의 권한 선언에 다음 항목을 포함합니다.

```json
"permissions": ["transfer"]
```

다음은 이용 건당 **10.00원**을 받는 앱 서버 예제입니다. 앱 이미지에 `httpx`를 설치하고,
수취 계좌 ID를 실제 개발자 계좌 ID로 바꿉니다.

```python
import os

import httpx

SELLER_ACCOUNT_ID = "개발자의_Coders_계좌_ID"


async def charge_usage(invoice_id: str):
    # invoice_id는 DB에 저장한 이용 건 ID입니다. 같은 이용 건의 재시도에 재사용합니다.
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post(
            os.environ["CODERS_URL"] + "/v1/accounts/transfers",
            headers={"Idempotency-Key": "app-fee:" + invoice_id},
            json={
                "recipient_id": SELLER_ACCOUNT_ID,
                "amount": "10",
                "mode": "standard",
            },
        )
        response.raise_for_status()
        # status="scheduled"는 자정 합산 지급을 위한 송금 접수 완료입니다.
        return response.json()
```

브로커가 현재 실행 계좌를 전달하므로 앱 코드는 계좌 비밀키를 보유할 필요가 없습니다.
승인된 송금 권한은 리소스 예산 안에서 반복 사용합니다. 수취 계좌·가격·청구 시점은 앱이 정합니다.
실행 예산에는 송금액과 Core 처리비·컴퓨팅 예약액이 함께 들어갑니다.

같은 이용 건의 재시도에는 같은 금액·수취 계좌·방식과 같은 `Idempotency-Key`를 사용합니다.
앱 서버의 내부 예산 갱신을 넘어 같은 리소스의 송금 결과를 재사용합니다.
서로 다른 이용 건에는 서로 다른 키를 부여합니다. 앱의 이용 내역과 송금 결과도 DB에 저장하여 관리합니다.

소수점 원화의 즉시 지급은 `transfer-precise` 권한과 `"mode": "precise"`를 사용합니다.
일반 송금은 1원 단위이며 수취인 화면에 송금자 정보를 공개하지 않습니다.

수취한 금액은 **Coders 내부 계좌 잔액**입니다. 현재 은행 계좌로 출금하는 기능은 제공하지 않습니다.
앱 소프트웨어의 상업적 이용 허용 여부는 해당 소프트웨어의 라이선스 조건으로 별도 확인합니다.

## 실행 코드와 프론트 연동

### 백엔드 호출

실행 코드는 `CODERS_URL`을 자원 API의 기준 주소로 사용합니다.
브로커가 현재 사용자·앱·리소스·실행 계좌 문맥으로 인증과 예산을 전달합니다.

워크스페이스 DB는 표준 PostgreSQL 연결 주소 `DATABASE_URL`로 사용합니다.

```python
import os
import psycopg

async def read_notes():
    # 현재 워크스페이스의 DB에 연결합니다.
    async with await psycopg.AsyncConnection.connect(os.environ["DATABASE_URL"]) as db:
        return await (await db.execute("SELECT * FROM notes")).fetchall()
```

일반 SQL·트랜잭션·COPY와 ORM을 사용합니다. psycopg·SQLAlchemy·asyncpg·pg 등 사용하는 드라이버를 앱 이미지의 의존성에 포함합니다.
워크스페이스 소유자가 용량과 보관 기간을 공동 계좌에서 선결제합니다. 실행 중 DB 연결 시간의
사용료는 리소스 서버의 실행 예산에서 지출합니다. 멤버별 내부 권한은 앱이 집행합니다.
DB 연결은 실행 수명과 현재 워크스페이스 권한에 귀속됩니다.

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

### SDK 반환값과 오류 처리

```javascript
const result = await coders.request('/api/analyze', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ text: '분석할 문장' })
});

console.log(result.status, result.ok); // HTTP 상태 코드와 2xx 성공 여부
console.log(result.data);             // JSON 해석 결과
console.log(result.response.headers); // 원본 fetch Response의 헤더

// SDK는 JSON을 복제한 Response로 읽으므로 원본 본문도 읽을 수 있습니다.
if (result.data === null) {
  console.log(await result.response.text());
}
```

| 필드 | 의미 |
| --- | --- |
| `status` | HTTP 상태 코드. `result.response.status`와 동일 |
| `ok` | HTTP 200–299이면 `true`. `result.response.ok`와 동일 |
| `data` | JSON 해석 결과. JSON 응답이 아니거나 HEAD·204·205·304 응답이면 `null` |
| `response` | 원본 Fetch API `Response`. 헤더와 `text()`·`json()`·`blob()` 등으로 본문 접근 |
| `executionId` | `Coders-Execution-Id` 응답 헤더. 없으면 `null` |
| `idempotencyKey` | 해당 요청에 사용한 `Idempotency-Key` |
| `requiresPermission` | 권한 승인 응답인 403에 유효한 Core 확인 URL이 있으면 `true` |
| `requiresAccountAction` | 유효한 Core 확인 URL이 있으면 `true` |
| `accountActionUrl` | 검증된 Core 확인 URL. 없으면 `null` |
| `retry()` | 원래 본문·메서드·멱등성 키로 같은 요청을 재전송하고 새 결과 반환 |

HTTP 4xx·5xx도 위 결과로 반환합니다. 앱은 `status`와 `data.error`를 확인하여 처리합니다.
네트워크 오류 또는 JSON으로 표시된 응답의 해석 실패는 `error.retry()`가 있는 예외를 던집니다.
앱 출처 밖이나 `/api/` 밖의 경로는 요청 전에 `TypeError`로 거부합니다.

```javascript
try {
  const result = await coders.request('/api/analyze', options);
  if (!result.ok) {
    // HTTP 오류 응답의 코드와 본문을 앱에서 처리합니다.
    showError(result.status, result.data);
  }
} catch (error) {
  // 응답 확인 실패는 성공·실패가 확정되지 않은 상태입니다.
  // 사용자 재시도 동작에 error.retry()를 연결하면 같은 본문과 키를 유지합니다.
  showRetry(error.message, error.retry);
}
```

위 예제의 `options`, `showError`, `showRetry`는 앱에서 구성합니다.
SDK 소스는 Core 저장소의 `src/coders/static/browser-sdk.js`입니다.
Core는 현재 앱 출처의 `/_coders/sdk.js`에서 이 모듈을 제공합니다.

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
| 502 `application_start_failed` | 앱 종료 코드·메모리 한도·필수 설정·DB·Redis 활성화 확인 |
| 503 `database_unavailable` | DB 복구 후 같은 키·본문으로 확인 |
| 503 `ledger_busy` | 충돌 해소 후 같은 키·본문으로 확인 |
| 통신 오류·결과 불명 | 기존 실행과 외부 작업 기록 확인 |

접수 전 거부는 같은 요청으로 재시도합니다. 접수된 요청은 같은 키로 기존 결과를 재생합니다.
종료된 실패 요청을 새로 실행할 때는 새 키를 사용합니다. 이미 발생한 사용 비용은 정산됩니다.
기본 선언형 화면은 승인 후 안전한 재시도를 자동 처리합니다.

## 지원 범위

- 공개 GitHub 저장소, 전체 40자리 커밋, `coders.json` version 2와 공개 빌드 이미지.
- Dockerfile에 포함된 앱·의존성과 표준 HTTP 서버.
- 일반 파일·디렉토리의 정적 프론트.
- 선택적 저장소 내부 OpenAPI JSON과 Swagger UI 호출.
- 앱별 독립 워크스페이스, 멤버 읽기·수정 권한, 워크스페이스 공동 계좌.
- 원화 여섯 자리 정산, 목표 잔액 충전, Polar 결제.

실행 아티팩트와 명세는 커밋에 고정되고, 런타임·자원 요율은 플랫폼 운영 설정으로 결정합니다.
운영은 단일 Core, 격리 범위별 HTTP 실행 환경과 워크스페이스별 PostgreSQL을 사용합니다.

## 호환 체크리스트

1. 공개 저장소 루트에 `coders.json`을 둡니다.
2. 코드 파일에 ASGI `app`을 제공하고 필요한 패키지를 확인합니다.
3. 실행·자원 사용을 감당하는 요청 예산을 선언합니다.
4. 외부 동작과 개발자 프론트에 필요한 권한을 선언합니다.
5. 워크스페이스 DB를 준비하고 `DATABASE_URL`을 일반 PostgreSQL 드라이버에 전달합니다.
6. 자원 호출은 `CODERS_URL`, 프론트 호출은 프로젝트 SDK를 사용합니다.
7. 준비 중·잔액 부족·승인·결과 불명 응답을 처리합니다.
8. 동일 작업의 키와 본문을 보존하고 실제 사용자 흐름을 확인합니다.
