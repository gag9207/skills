param([string]$Dir, [string]$DeckOut, [string]$TermOut, [string]$ArtOut)
# Assemble the presentation deck, the local revision terminal and the artifact page
# from one project folder: slides.html + deck.css + deck.json + img/*.
# Keep this file ASCII only: Windows PowerShell 5.1 misreads non-ASCII text in BOM-less scripts.
$ErrorActionPreference = 'Stop'
$u = New-Object System.Text.UTF8Encoding($false)
function ReadU($p) { [IO.File]::ReadAllText($p, $u) }
$assets = Join-Path (Split-Path $PSScriptRoot -Parent) 'assets'
$cfg = ReadU "$Dir\deck.json" | ConvertFrom-Json
function Fill($s) {
  $s.Replace('{{DECK_TITLE}}', $cfg.deckTitle).Replace('{{TERM_TITLE}}', $cfg.termTitle).Replace('{{TERM_SUB}}', $cfg.termSub).Replace('{{DECK_LABEL}}', $cfg.deckLabel).Replace('{{SHORT}}', $cfg.short).Replace('{{KEY}}', $cfg.key)
}
function Pick($name) { if (Test-Path "$Dir\$name") { "$Dir\$name" } else { Join-Path $assets $name } }

$slides = ReadU "$Dir\slides.html"
if (Test-Path "$Dir\img") {
  foreach ($f in Get-ChildItem "$Dir\img" -File) {
    $ext = $f.Extension.ToLower()
    $mime = switch ($ext) { '.png' {'image/png'} '.svg' {'image/svg+xml'} '.webp' {'image/webp'} default {'image/jpeg'} }
    $b = [Convert]::ToBase64String([IO.File]::ReadAllBytes($f.FullName))
    $slides = $slides.Replace('{{' + $f.BaseName + '}}', "data:$mime;base64,$b")
  }
}
$left = [regex]::Matches($slides, '\{\{[A-Za-z0-9_-]+\}\}') | ForEach-Object { $_.Value } | Sort-Object -Unique
if ($left) { "warning: no image for " + ($left -join ', ') }
$n = ([regex]::Matches($slides, '<section class="slide')).Count
$base = ReadU (Join-Path $assets 'viewport-base.css')
$deckCss = ReadU "$Dir\deck.css"

if ($DeckOut) {
  $d = Fill (ReadU (Pick 'deck_shell.html'))
  $d = $d.Replace('/*{{CSS_BASE}}*/', $base).Replace('/*{{CSS_DECK}}*/', $deckCss).Replace('<!--{{SLIDES}}-->', $slides)
  [IO.File]::WriteAllText($DeckOut, $d, $u)
  "deck $n slides, {0:N1} MB -> $DeckOut" -f ((Get-Item $DeckOut).Length / 1MB)
}
if ($TermOut -or $ArtOut) {
  $t = Fill (ReadU (Pick 'term.html'))
  $t = $t.Replace('/*{{CSS_DECK}}*/', $deckCss).Replace('<!--{{SLIDES}}-->', $slides)
  if ($ArtOut) {
    [IO.File]::WriteAllText($ArtOut, $t, $u)
    "artifact {0:N1} MB -> $ArtOut" -f ((Get-Item $ArtOut).Length / 1MB)
  }
  if ($TermOut) {
    $head = '<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"><style>:root{color-scheme:light}body{margin:0;font:14px sans-serif}img{max-width:100%}[hidden]{display:none!important}</style></head><body>'
    [IO.File]::WriteAllText($TermOut, $head + "`n" + $t + "`n</body></html>", $u)
    "terminal {0:N1} MB -> $TermOut" -f ((Get-Item $TermOut).Length / 1MB)
  }
}
