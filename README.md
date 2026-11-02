# 하이코두 나라장터 입찰 대시보드

조달청 나라장터 용역 입찰공고를 하루 5번(한국시간 08·11·13·16·19시) 자동 수집해
하이코두 업종(교육·AI·SW·행사·학술용역)에 맞는 공고만 웹페이지로 보여줍니다.

- 필터 수정: `scripts/config.py`의 키워드 목록
- 즉시 갱신: Actions 탭 → "나라장터 대시보드 갱신" → Run workflow
- 인증키: Settings → Secrets and variables → Actions → `G2B_SERVICE_KEY`
