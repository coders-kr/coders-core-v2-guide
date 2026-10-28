# 워크스페이스 활동

활동은 같은 워크스페이스의 사용자와 Agent가 현재 진행 상황을 공유하는 선택 기능입니다.
앱은 상태 조회와 행동 실행에 기존 HTTP API를 사용하고, 활동으로 화면 갱신과 강조 시점을 알립니다.
데이터의 기준은 워크스페이스 DB입니다.

## 실행 가능한 데모

[함께 쓰기 데모](https://core-v2.coders.kr/use/gh-e2ac3f0106c86b75e4fbfeabde) · [공개 저장소와 CLI 연결 방법](https://github.com/cykim8811/coders-activity-demo#agent-연결)

로그인 후 워크스페이스를 생성하고 문서를 엽니다.
브라우저에서 제목을 저장하거나 같은 워크스페이스의 CLI에서 `python3 agent.py save '새 제목'`을 실행하면
열린 브라우저가 데이터를 다시 읽고 문서 영역을 강조합니다.
`python3 agent.py state`는 문서와 가능한 행동을, `python3 agent.py watch`는 실시간 활동을 제공합니다.
브라우저와 Agent는 동일한 앱 API와 PostgreSQL 데이터를 사용합니다.
CLI 연결에는 기존 Coders 계좌 인증 키와 같은 워크스페이스 ID를 사용합니다.
워크스페이스 생성·보관·실행에는 일반 Coders 요금이 적용됩니다.

## 링크 하나로 Agent 연결

1. 앱의 Coders 칩에서 **Agent 연결 → 연결 링크 만들기 → 링크 복사**를 선택합니다.
2. Agent에게 링크를 전달합니다. 링크에는 연결 절차와 고정된 앱 명세·소스 주소가 있습니다.
3. Agent가 연결 요청을 만들면 사용자에게 승인 링크와 확인 코드를 보여줍니다.
4. 사용자는 코드·워크스페이스를 확인하고 연결 기간을 선택합니다. 기본값은 **24시간**, 선택지는 **1시간·24시간·7일**입니다.
5. 승인된 Agent는 같은 워크스페이스의 API와 활동 구독에 접속합니다.

연결 링크는 24시간, 승인 대기 요청은 10분 동안 유효합니다.
승인된 연결은 해당 사용자·워크스페이스·앱 커밋과 현재 승인 범위에 묶입니다.
워크스페이스 권한·버전 변경, 개인 연결 해제, 만료, Agent 연결 해제 시 인증이 종료됩니다.
공동 잔액 사용과 앱에 허용된 동작은 기존 실행 규칙으로 처리합니다.
Agent 연결 화면에서 승인 대기·활성 연결을 확인하고 해제합니다.
이미 접수된 유료 작업은 기존 정산 규칙으로 마무리합니다.

표준 라이브러리만 사용하는 [Python 연결 도우미](https://dev.coders.kr/agent-connect.py):

```bash
python3 agent-connect.py 'Coders에서 복사한 연결 링크' --name '내 Agent'
```

도우미는 승인 링크·확인 코드를 출력하고, 승인 후 권한이 제한된 인증 파일을 `~/.config/coders/agents/`에 저장합니다.
파일에는 `app_url`, `account_key`, `resource_id`, `expires_at`이 있습니다.
인증 키와 `device_code`는 로컬 비밀 정보로 취급합니다.
공개 데모의 CLI는 인증 파일을 직접 읽습니다.

```bash
python3 agent.py --connection /path/to/connection.json state
python3 agent.py --connection /path/to/connection.json watch
python3 agent.py --connection /path/to/connection.json save 'Agent가 바꾼 제목'
```

Agent에게 링크를 전달할 때 사용자의 작업 지시를 함께 제공합니다.
앱 소스와 README는 앱 개발자가 작성한 자료이며, Agent는 이를 사용자 지시와 구분해 취급합니다.

## 이벤트

```json
{
  "action_id": "3f7ddf99-c9b5-434a-9ff2-d479fc180aa8",
  "target": "document:123",
  "action": "save",
  "status": "completed",
  "changed": true,
  "actor_label": "Agent"
}
```

- `action_id`: 한 행동을 식별하는 UUID. 같은 행동의 시작·완료·실패에 공유합니다.
- `target`: 앱이 정의하는 대상 ID, 최대 200자.
- `action`: 동작 이름, 최대 80자.
- `status`: `started`, `completed`, `failed`.
- `changed`: 실제 저장이 커밋된 완료 이벤트에 지정합니다. 기본값은 `false`입니다.
- `actor_label`: 앱이 보고하는 표시 이름, 최대 80자. 인증된 Agent 신원과 구분됩니다.

Core는 `cursor`, `created_at`, `actor`를 붙입니다.
`actor.kind=user`이면 인증된 실행 범위의 사용자 ID가 포함됩니다.
공유 서버에서 발행하면 `actor.kind=app`과 `user_id=null`로 표시합니다.
서버 소유자를 해당 행동의 수행자로 간주하지 않습니다.
`actor.project`는 검증된 실행 버전을 식별합니다.

같은 워크스페이스·발행자·행동 ID·상태의 재발행은 보관 이력 안에서 동일 이벤트를 반환합니다.
같은 식별자의 입력을 바꾸면 `409 idempotency_conflict`가 반환됩니다.

## 발행

앱 실행 중 기존 Core 브로커에 공식 엔드포인트를 호출합니다.
브로커가 현재 실행의 인증과 워크스페이스를 연결합니다.

```python
async with httpx.AsyncClient(base_url=os.environ["CODERS_URL"]) as core:
    result = await core.post(
        "/v1/invoke/coders-activity",
        headers={"Coders-Budget": "2", "Idempotency-Key": operation_key},
        json={"action_id": action_id, "target": "document:123", "action": "save",
              "status": "completed", "changed": True, "actor_label": "Agent"},
    )
```

발행은 기존 요청 예산·요금·중복 요청 규칙을 따릅니다.
워크스페이스와 수행자 정보는 인증된 실행에서 결정됩니다.
DB 커밋과 Core 이벤트 발행은 각각의 트랜잭션입니다.
앱은 저장 트랜잭션에 발행 대기를 기록하고, 발행 실패 시 저장 결과를 유지한 채 알림을 재시도할 수 있습니다.
예제는 `action_id`로 저장을 멱등 처리하고 발행 대기를 기록합니다.
새로운 요청 키를 쓰는 재시도에는 일반 요청 요금이 적용됩니다.

활동은 앱이 보고한 동작을 전달합니다. 구독자는 알림을 받으면 실제 데이터를 다시 조회합니다.
지연된 발행 때문에 이벤트 도착 순서와 DB 변경 순서가 다를 수 있습니다.

## 구독

브라우저는 프로젝트 세션으로 `GET /_coders/activity`를 사용합니다.
Core 격리 화면에는 `GET /run/{handle}/activity`가 제공됩니다.
CLI는 기존 승인된 계좌 인증으로 다음 주소를 사용합니다.

```text
GET https://api.coders.kr/{owner}/{repo}/{commit}/_activity?after=12
Coders-Grant: <existing-account-key>
Coders-Resource: <workspace-id>
```

기본 계좌 인증은 해당 코드에 이미 승인된 워크스페이스 연결로 해석됩니다.
연결이 여러 개면 `Coders-Resource`로 선택합니다.
실행에 묶인 계좌는 `GET /v1/workspace/activity`로 같은 범위를 구독할 수도 있습니다.
계좌 키는 CLI 환경변수로 전달하고 프론트 소스에 포함하지 않습니다.

응답 형식:

```json
{"cursor":13,"reset":false,"events":[{"cursor":13,"target":"document:123"}]}
```

실제 이벤트는 앞서 정의한 전체 필드를 포함합니다.
`after`가 없으면 현재 커서와 `reset=true`를 즉시 반환합니다.
이벤트가 있으면 최대 64개를 순서대로 반환하고, 없으면 최대 20초 기다립니다.
`wait=0`은 대기 없는 조회입니다.
최근 256개 이벤트를 PostgreSQL에 보관합니다.
이력을 놓치거나 잘못된 미래 커서를 사용하면 `reset=true`와 최신 커서를 반환합니다.
클라이언트는 이때 현재 앱 데이터를 다시 읽습니다.
구독은 계좌 잔액 화면과 같은 인증된 제어 정보 조회이며 실행 계좌를 분할하지 않습니다.
대기 중에도 세션·계좌·워크스페이스 권한을 재검사합니다.
동시 대기 구독은 Core 프로세스당 워크스페이스별 32개로 제한합니다.

## 브라우저 SDK와 강조

```javascript
const stop = createClient().watchActivity({
  onReset: () => reloadDocument(),
  async onEvent(event) {
    if (event.changed) await reloadDocument();
    renderActivity(event);
  },
  onError(error) { showConnectionError(error); },
  highlight: true,
});
window.addEventListener('pagehide', stop, { once: true });
```

`onReset`과 `onEvent`는 필수이며 Promise를 반환할 수 있습니다.
네트워크 오류에는 마지막 처리 커서로 재접속하고 `onReset`에서 데이터를 다시 읽습니다.
인증·권한 오류에는 구독을 중단합니다.
`AbortSignal` 또는 반환된 `stop()` 함수로 구독을 종료할 수 있습니다.
콜백 재시도에 대비해 화면 갱신을 멱등하게 처리합니다.
앱은 정기 재조회나 발행 대기 처리로 DB와 화면의 상태를 수렴시킬 수 있습니다.

```html
<section data-coders-target="document:123">...</section>
```

`highlight:true`는 같은 대상 ID의 컴포넌트만 강조합니다.
강조는 선택 기능이며, 모션 감소 설정을 존중합니다.
DOM 구조·화면 좌표는 이벤트 규약에 포함되지 않습니다.
