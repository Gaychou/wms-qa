# SQL Server integration

This adapter lets QA tasks use SQL Server as an executable oracle instead of a manual-only check.

## Environment variables

Put secrets in `.qa-agent/local/.env` and keep that directory out of source control:

```dotenv
QA_SQLSERVER_SERVER=127.0.0.1,1433
# Or use QA_SQLSERVER_HOST=127.0.0.1 + QA_SQLSERVER_PORT=1433
QA_SQLSERVER_DATABASE=IWMS_TEST
QA_SQLSERVER_USER=qa_user
QA_SQLSERVER_PASSWORD=change-me
# QA_SQLSERVER_PASS is accepted as an alias for QA_SQLSERVER_PASSWORD
QA_SQLSERVER_TRUST_CERT=1
QA_SQLSERVER_ALLOW_WRITE=0
```

For Windows Integrated Security:

```dotenv
QA_SQLSERVER_SERVER=localhost
QA_SQLSERVER_DATABASE=IWMS_TEST
QA_SQLSERVER_INTEGRATED_SECURITY=1
QA_SQLSERVER_TRUST_CERT=1
```

## Read-only DB oracle

Prefer an already-connected SQL Server tool/MCP when one is available. Otherwise run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass `
  -File "$env:QA_AGENT_DIR\scripts\sqlserver_query.ps1" `
  -Mode Read `
  -Query "SET NOCOUNT ON; SELECT Status FROM dbo.TBillOrderInfo WHERE BillId='...';"
```

The helper returns JSON containing `rowCount` and `rows`.

## PRE/POST data preparation

Write SQL is intentionally blocked unless BOTH are true:

- `-Mode Write`
- `QA_SQLSERVER_ALLOW_WRITE=1`

Use write mode only against a disposable QA database or explicitly approved test data. Save the original value before PRE and restore it in POST.

For WMS flows, DB verification should normally check the main business row plus important side effects such as inventory, wave/pick records, SN records, interface/outbox rows and business logs.


## Compatibility aliases

For existing WMS environments the helper also accepts:

- `QA_SQLSERVER_HOST` + optional `QA_SQLSERVER_PORT` instead of `QA_SQLSERVER_SERVER`
- `QA_SQLSERVER_PASS` instead of `QA_SQLSERVER_PASSWORD`

Prefer `QA_SQLSERVER_SERVER` and `QA_SQLSERVER_PASSWORD` for new setups.
