
$PgBin = "D:\codeapp\postgreSQL\postgresql-18.6-5-windows-x64-binaries\pgsql\bin"
$DataDir = "D:\codeapp\postgreSQL\data"
$LogFile = "D:\codeapp\postgreSQL\postgres.log"
$PgCtl = Join-Path $PgBin "pg_ctl.exe"

# Check required files
if (-not (Test-Path $PgCtl)) {
    Write-Host "ERROR: pg_ctl.exe not found." -ForegroundColor Red
    exit 1
}

if (-not (Test-Path (Join-Path $DataDir "PG_VERSION"))) {
    Write-Host "ERROR: PostgreSQL data directory is invalid." -ForegroundColor Red
    exit 1
}

# Check whether PostgreSQL is already running
& $PgCtl -D $DataDir status 2>$null

if ($LASTEXITCODE -eq 0) {
    Write-Host "PostgreSQL is already running." -ForegroundColor Green
    exit 0
}

# Start PostgreSQL
Write-Host "Starting PostgreSQL..."

& $PgCtl -D $DataDir -l $LogFile -o "-p 5432" start

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Startup failed. Check the PostgreSQL log:" -ForegroundColor Red
    Write-Host $LogFile
    exit 1
}

# Verify the port
$PortReady = Test-NetConnection 127.0.0.1 -Port 5432 -InformationLevel Quiet

if ($PortReady) {
    Write-Host "PostgreSQL started successfully. Port 5432 is available." -ForegroundColor Green
} else {
    Write-Host "ERROR: PostgreSQL started, but port 5432 is unavailable." -ForegroundColor Red
    Write-Host "Check the log:"
    Write-Host $LogFile
    exit 1
}
