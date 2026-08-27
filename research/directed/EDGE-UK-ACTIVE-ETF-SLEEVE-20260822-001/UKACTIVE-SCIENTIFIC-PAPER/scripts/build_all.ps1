param(
    [switch]$SkipRandomFigure,
    [switch]$SkipPdf
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

$paperRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$assetPython = 'C:\Python312\python.exe'
$documentPython = 'C:\Users\paulh\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
$node = 'C:\Users\paulh\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe'
$artifactTool = 'C:\Users\paulh\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\node_modules\@oai\artifact-tool\dist\artifact_tool.mjs'

$requiredExecutables = @($assetPython, $documentPython, $node)
foreach ($executable in $requiredExecutables) {
    if (-not (Test-Path -LiteralPath $executable -PathType Leaf)) {
        throw "Required runtime is unavailable: $executable"
    }
}
if (-not (Test-Path -LiteralPath $artifactTool -PathType Leaf)) {
    throw "Required spreadsheet validation module is unavailable: $artifactTool"
}

$assetArguments = @((Join-Path $PSScriptRoot 'generate_paper_assets.py'))
if ($SkipRandomFigure) {
    $assetArguments += '--skip-random-figure'
}
& $assetPython @assetArguments
if ($LASTEXITCODE -ne 0) { throw "Paper asset generation failed with exit code $LASTEXITCODE" }

$env:UKACTIVE_PAPER_ROOT = $paperRoot
$env:UKACTIVE_ARTIFACT_TOOL_MODULE = $artifactTool
& $node (Join-Path $PSScriptRoot 'validate_tabular_outputs.mjs')
if ($LASTEXITCODE -ne 0) { throw "Tabular validation failed with exit code $LASTEXITCODE" }

$markdown = Join-Path $paperRoot 'UKACTIVE_ETF_ROTATION_SCIENTIFIC_PAPER.md'
$docx = Join-Path $paperRoot 'UKACTIVE_ETF_ROTATION_SCIENTIFIC_PAPER.docx'
$pdf = Join-Path $paperRoot 'UKACTIVE_ETF_ROTATION_SCIENTIFIC_PAPER.pdf'
& $documentPython (Join-Path $PSScriptRoot 'build_docx.py') --markdown $markdown --output $docx
if ($LASTEXITCODE -ne 0) { throw "DOCX build failed with exit code $LASTEXITCODE" }

if (-not $SkipPdf) {
    & (Join-Path $PSScriptRoot 'convert_docx_to_pdf.ps1') -InputPath $docx -OutputPath $pdf
    if ($LASTEXITCODE -ne 0) { throw "PDF build failed with exit code $LASTEXITCODE" }
}

[pscustomobject]@{
    status = 'PASS'
    paper_root = $paperRoot
    randomisation_exact_reproduction = -not $SkipRandomFigure
    pdf_generated = -not $SkipPdf
    docx_sha256 = Get-Sha256Hex $docx
    pdf_sha256 = if ($SkipPdf) { $null } else { Get-Sha256Hex $pdf }
} | ConvertTo-Json -Depth 3
