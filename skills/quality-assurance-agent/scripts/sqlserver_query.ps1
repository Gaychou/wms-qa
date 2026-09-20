param(
    [string]$Query,
    [string]$QueryFile,
    [ValidateSet("Read","Write")][string]$Mode = "Read",
    [int]$CommandTimeout = 60
)

$ErrorActionPreference = "Stop"

if (-not $Query -and -not $QueryFile) {
    throw "Specify -Query or -QueryFile."
}
if ($QueryFile) {
    $Query = Get-Content -Raw -Encoding UTF8 $QueryFile
}

$server = $env:QA_SQLSERVER_SERVER
if (-not $server -and $env:QA_SQLSERVER_HOST) {
    $server = $env:QA_SQLSERVER_HOST
    if ($env:QA_SQLSERVER_PORT) {
        $server = "$server,$($env:QA_SQLSERVER_PORT)"
    }
}
$database = $env:QA_SQLSERVER_DATABASE
$user = $env:QA_SQLSERVER_USER
$password = $env:QA_SQLSERVER_PASSWORD
if (-not $password) {
    $password = $env:QA_SQLSERVER_PASS
}
$integrated = ($env:QA_SQLSERVER_INTEGRATED_SECURITY -eq "1")
$trust = ($env:QA_SQLSERVER_TRUST_CERT -ne "0")

if (-not $server -or -not $database) {
    throw "Set QA_SQLSERVER_SERVER (or QA_SQLSERVER_HOST + optional QA_SQLSERVER_PORT) and QA_SQLSERVER_DATABASE."
}

$writePattern = '(?is)\b(INSERT|UPDATE|DELETE|MERGE|TRUNCATE|DROP|ALTER|CREATE|GRANT|REVOKE|DENY|EXEC(?:UTE)?|DBCC)\b'
$isWriteSql = [regex]::IsMatch($Query, $writePattern)

if ($Mode -eq "Read" -and $isWriteSql) {
    throw "Write SQL rejected in Read mode."
}

if ($Mode -eq "Write" -and $env:QA_SQLSERVER_ALLOW_WRITE -ne "1") {
    throw "Write SQL is disabled. Set QA_SQLSERVER_ALLOW_WRITE=1 explicitly for controlled QA PRE/POST data preparation."
}

$builder = New-Object System.Data.SqlClient.SqlConnectionStringBuilder
$builder["Data Source"] = $server
$builder["Initial Catalog"] = $database
$builder["Application Name"] = "wms-qa"
$builder["Connect Timeout"] = 15
$builder["TrustServerCertificate"] = $trust

if ($integrated) {
    $builder["Integrated Security"] = $true
} else {
    if (-not $user -or -not $password) {
        throw "Set QA_SQLSERVER_USER and QA_SQLSERVER_PASSWORD/QA_SQLSERVER_PASS, or QA_SQLSERVER_INTEGRATED_SECURITY=1."
    }
    $builder["User ID"] = $user
    $builder["Password"] = $password
}

$conn = New-Object System.Data.SqlClient.SqlConnection($builder.ConnectionString)
$cmd = $conn.CreateCommand()
$cmd.CommandText = $Query
$cmd.CommandTimeout = $CommandTimeout

try {
    $conn.Open()

    if ($Mode -eq "Write" -or $isWriteSql) {
        $affected = $cmd.ExecuteNonQuery()
        [pscustomobject]@{
            ok = $true
            mode = "Write"
            affectedRows = $affected
        } | ConvertTo-Json -Compress
        exit 0
    }

    $adapter = New-Object System.Data.SqlClient.SqlDataAdapter($cmd)
    $table = New-Object System.Data.DataTable
    [void]$adapter.Fill($table)

    $rows = @()
    foreach ($row in $table.Rows) {
        $obj = [ordered]@{}
        foreach ($col in $table.Columns) {
            $value = $row[$col.ColumnName]
            if ($value -is [DBNull]) { $value = $null }
            $obj[$col.ColumnName] = $value
        }
        $rows += [pscustomobject]$obj
    }

    [pscustomobject]@{
        ok = $true
        mode = "Read"
        rowCount = $table.Rows.Count
        rows = $rows
    } | ConvertTo-Json -Depth 8 -Compress
}
finally {
    if ($conn.State -ne [System.Data.ConnectionState]::Closed) {
        $conn.Close()
    }
    $conn.Dispose()
}
