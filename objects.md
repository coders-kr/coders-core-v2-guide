# 워크스페이스 파일 저장소

`services: ["objects"]`는 리소스에 귀속된 관리형 파일 저장소를 준비합니다. PostgreSQL·Redis와 함께 선언할 수 있습니다. 세 서비스의 영속 데이터는 같은 보관 용량과 기간을 공유합니다. S3 처리는 Apache-2.0 라이선스의 Versity Gateway 1.10.0 POSIX 백엔드가 담당합니다. 파일은 제한된 파일시스템에 저장하며 실행 컨테이너에 파일 볼륨을 직접 노출하지 않습니다.

리소스 멤버는 앱을 통해 파일을 사용합니다. Core는 실행 신원·리소스 승인·보관 계약을 검증하고, 앱이 내부 문서별 권한을 집행합니다. 버전 업데이트와 서버 재시작 후에도 같은 리소스의 파일을 사용합니다.

## 연결

관리형 HTTP 실행기는 다음 환경변수를 제공합니다.

| 변수 | 값 |
|---|---|
| `AWS_ENDPOINT_URL_S3` | `http://127.0.0.1:9000/v1/objects` |
| `AWS_DEFAULT_REGION` | `us-east-1` |
| `CODERS_OBJECTS_BUCKET` | `workspace` |
| `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` | SDK 형식에 필요한 고정 값 `coders` |

실제 인증은 실행기에 결합된 Core 브로커 신원으로 집행합니다. SDK 환경변수의 고정 값에는 리소스 접근 권한이 담겨 있지 않습니다. 경로 방식(path-style)과 일반 HTTP 본문을 사용합니다.

S3 인터페이스는 Put/Get/Head/DeleteObject, DeleteObjects, CopyObject, HeadBucket, GetBucketLocation, ListObjectsV2와 multipart 업로드·조회·완료·취소를 제공합니다. Range와 조건부 조회를 전달합니다. 버킷 이름은 `workspace`입니다. 객체 이름은 제어문자와 `.`·`..` 경로 구간을 제외한 UTF-8 상대 경로이며 1,024바이트까지 지원합니다. `.sgwtmp` 등 저장 서버의 내부 이름은 예약됩니다.

버킷 생성·삭제·정책·ACL은 Coders가 관리합니다. 파일 복사는 같은 리소스 안에서 수행합니다. S3 SDK의 서명은 Core 브로커의 실행 신원으로 재서명하며, 외부 호출의 계좌·리소스 권한을 대신하지 않습니다.

```python
import os
import boto3
from botocore.config import Config

store = boto3.client(
    "s3",
    endpoint_url=os.environ["AWS_ENDPOINT_URL_S3"],
    config=Config(s3={"addressing_style": "path"},
                  request_checksum_calculation="when_required"),
)
store.put_object(Bucket="workspace", Key="images/sample.png",
                 Body=png_bytes, ContentType="image/png")
```

SDK는 path-style, 일반 본문과 Content-Length를 사용합니다. `DeleteObjects`에는 SDK가 계산하는 Content-MD5 또는 지원하는 체크섬 헤더가 필요합니다. AWS 청크 서명 전송 대신 일반 본문을 선택합니다. boto3의 `request_checksum_calculation="when_required"`와 Java AWS SDK의 동등한 설정을 사용하고, SDK 버전별 실제 요청을 검증합니다.

multipart의 각 요청에는 Core 브로커의 본문 상한이 적용됩니다. 일반 본문 상한을 넘는 전체 파일 전송에는 아래 링크를 사용합니다. AWS 사전 서명 URL은 Core의 실행 인증을 대체하지 않으며, 브라우저는 Coders 전송 링크 또는 앱의 인증된 파일 중계를 사용합니다.

## 실행·격리·공유

기본은 리소스별 전용 S3 서버입니다. 소유자는 **일반 설정 → 서버 공유 → 파일 저장소 서버 공유 허용**을 선택할 수 있습니다. `PUT /v1/resources/{id}/sharing`의 `share_objects`가 같은 설정입니다. 앱 서버 공유·DB 서버 공유와 각각 독립적인 동의입니다.

공유 서버에서도 요청의 버킷은 Core가 현재 리소스에 고정하며, 리소스별 파일은 기존의 독립된 용량 제한 파일시스템에 저장됩니다. 공유 설정을 바꿔도 파일 경로와 보관 계약은 유지됩니다. 변경 전에 시작한 전송을 정리한 후 새 실행 방식에 연결합니다.

서버는 사용 중 CPU·메모리 점유 비용을 공동 계좌에서 선예약·정산합니다. 공유 서버는 동시에 사용하는 리소스 수로 점유 비용을 나누며, 같은 리소스의 병렬 요청은 하나의 지분입니다. 마지막 전송 종료 시 서버를 중지하고 미사용 예약액을 반환합니다. 컨테이너는 다음 전송에 재사용합니다. 운영 기본값은 100m CPU·128 MiB 메모리입니다. 예산 감시 프로세스가 예약 기간을 집행하고, 갱신 실패 시 공유 엔진 전체를 중지합니다.

## 큰 파일 전송

앱은 `CODERS_URL`을 통해 파일 전송 링크를 발급합니다.

```python
async with httpx.AsyncClient(base_url=os.environ["CODERS_URL"]) as core:
    response = await core.post("/v1/objects/links", json={
        "key": "images/sample.png", "method": "PUT", "size": file_size,
        "content_type": "image/png", "seconds": 300,
    })
    response.raise_for_status()
    upload = response.json()
```

브라우저는 반환된 `url`에 지정한 메서드로 파일 본문을 전송합니다. `GET` 링크는 `key`와 `method`로 발급합니다. 링크는 최대 300초·한 번의 전송에 유효하며 리소스·사용자·승인 세대·객체·메서드에 결합됩니다. 전송 권한은 링크를 가진 호출자에게 전달됩니다. Core는 리소스 접근과 승인 세대를 다시 확인하고 진행 중 전송도 주기적으로 검사합니다.

한 번 사용한 링크의 재시도에는 새 링크를 발급합니다. 전송 URL은 비밀정보로 취급합니다. Core 접근 로그는 링크 토큰을 가립니다. `broker_path`는 같은 링크를 실행기의 Core 브로커로 호출할 때 사용하는 상대 경로입니다.

파일 전송은 64 KiB 단위로 중계합니다. 운영 기본 파일 상한은 512 MiB, 전송 제한 시간은 300초입니다. 업로드는 선언한 크기와 실제 크기가 일치해야 합니다. 다운로드 응답은 첨부 파일·`nosniff`·격리 CSP를 사용합니다.

## 요금과 복구

보관료는 워크스페이스의 선납 보관 계약에 포함됩니다. 파일 요청·전송 요금은 `요청 접수료 + 전송 바이트 × MiB당 전송 단가 / 1,048,576`입니다. 운영 설정 `project_file_krw_per_mib`가 전송 단가를 정합니다.

Core는 전송 상한에 해당하는 예산을 내부 계좌에 예약하고, 관측한 전송량을 정산한 뒤 미사용액을 반환합니다. 링크 발급도 Core 요청 접수료를 사용합니다. 중단된 프로세스의 미확정 전송은 제한 시간이 지난 뒤 예약 상한으로 정산합니다. 실제 파일 전송은 리소스 공동 계좌, 앱 내부 호출은 현재 실행 예산에서 비용을 부담합니다.

파일 교체는 저장 서버가 새 파일을 기록한 뒤 게시합니다. 교체와 multipart 업로드에는 임시 여유 용량이 필요합니다. 미완료 multipart 업로드는 SDK의 AbortMultipartUpload로 정리합니다. 워크스페이스 삭제·보관 만료 절차가 영속 파일을 정리하며, 워크스페이스 삭제 완료 시 파일 인덱스와 비밀정보도 정리합니다.

백업 단위는 **원장의 리소스·보관 계약과 워크스페이스 보관 볼륨**입니다. 운영자는 같은 시점의 원장·볼륨 백업을 함께 보관하고, 파일의 확장 속성과 저장 서버 메타데이터를 보존합니다. 자동 백업 주기와 보존 기간은 운영 백업 정책으로 관리합니다.
