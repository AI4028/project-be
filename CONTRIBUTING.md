# Contributing / 기여 방법

## Branches / 브랜치

```text
feature/<name>, fix/<name>, chore/<name>  →  PR into develop  →  develop into main (after checks pass)
```

```powershell
git checkout develop
git pull
git checkout -b feature/map-search
```

Never push straight to `main` or `develop`. `main`, `develop`에 직접 push하지 않습니다.

## Commits / 커밋

[Conventional Commits](https://www.conventionalcommits.org): `feat`, `fix`,
`docs`, `chore`, `refactor`, `test`. Short and lowercase.

```text
feat: add nearby stores endpoint
fix: keep websocket token checks off the event loop
```

## Pull requests / PR

- Run the tests first. PR 전에 테스트를 실행합니다.
  `.\.venv\Scripts\python.exe -m pytest`
- One topic per PR. PR 하나에 주제 하나.
- Never commit secrets, `.env` or kiosk keys (`ksk_...`). If one leaks, rotate it.
  비밀 값, `.env`, 키오스크 키는 커밋하지 않습니다. 유출되면 바로 교체합니다.
