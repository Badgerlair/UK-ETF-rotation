param(
    [Parameter(Mandatory = $true)]
    [string]$InputPath,

    [Parameter(Mandatory = $true)]
    [string]$OutputPath
)

$ErrorActionPreference = 'Stop'

function Get-Sha256Hex([string]$Path) {
    $stream = [System.IO.File]::OpenRead($Path)
    $algorithm = [System.Security.Cryptography.SHA256]::Create()
    try {
        return ([System.BitConverter]::ToString($algorithm.ComputeHash($stream))).Replace('-', '').ToLowerInvariant()
    }
    finally {
        $stream.Dispose()
        $algorithm.Dispose()
    }
}

$resolvedInput = (Resolve-Path -LiteralPath $InputPath).Path
$resolvedOutput = [System.IO.Path]::GetFullPath($OutputPath)
$outputDirectory = [System.IO.Path]::GetDirectoryName($resolvedOutput)
$volatileOutput = [System.IO.Path]::Combine(
    $outputDirectory,
    ([System.IO.Path]::GetFileNameWithoutExtension($resolvedOutput) + '.word-export.tmp.pdf')
)

if (-not [System.IO.Directory]::Exists($outputDirectory)) {
    [System.IO.Directory]::CreateDirectory($outputDirectory) | Out-Null
}

$word = $null
$document = $null

try {
    $word = New-Object -ComObject Word.Application
    $word.Visible = $false
    $word.DisplayAlerts = 0

    # Open read-only so field refresh and PDF export cannot mutate the
    # deterministic DOCX artefact created by build_docx.py.
    $document = $word.Documents.Open($resolvedInput, $false, $true)

    foreach ($tableOfContents in $document.TablesOfContents) {
        $tableOfContents.Update() | Out-Null
    }

    foreach ($field in $document.Fields) {
        $field.Update() | Out-Null
    }

    # wdExportFormatPDF = 17.  Word performs pagination using the installed
    # production renderer, including mixed portrait/landscape sections.
    $document.ExportAsFixedFormat($volatileOutput, 17)
}
finally {
    if ($null -ne $document) {
        $document.Close($false)
        [void][System.Runtime.InteropServices.Marshal]::FinalReleaseComObject($document)
    }

    if ($null -ne $word) {
        $word.Quit()
        [void][System.Runtime.InteropServices.Marshal]::FinalReleaseComObject($word)
    }

    [GC]::Collect()
    [GC]::WaitForPendingFinalizers()
}

if (-not [System.IO.File]::Exists($volatileOutput)) {
    throw "Word completed without creating the expected PDF: $volatileOutput"
}

$python = 'C:\Users\paulh\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
$normaliser = Join-Path $PSScriptRoot 'normalize_pdf.py'
& $python $normaliser $volatileOutput $resolvedOutput
if ($LASTEXITCODE -ne 0) {
    throw "PDF metadata normalisation failed with exit code $LASTEXITCODE"
}
Remove-Item -LiteralPath $volatileOutput -Force

$pdf = Get-Item -LiteralPath $resolvedOutput
[pscustomobject]@{
    input = $resolvedInput
    output = $pdf.FullName
    bytes = $pdf.Length
    sha256 = Get-Sha256Hex $pdf.FullName
} | ConvertTo-Json -Depth 2
