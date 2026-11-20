param([Parameter(Mandatory=$true)][string]$Dir)
# Create a new deck project folder: starter slides.html + deck.json + img/, and the proven deck.css design system.
# Refuses to overwrite an existing slides.html. ASCII only (PowerShell 5.1).
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
if (Test-Path "$Dir\slides.html") { throw "slides.html already exists in $Dir" }
New-Item -ItemType Directory -Force "$Dir\img" | Out-Null
Copy-Item "$root\assets\starter\slides.html" "$Dir\slides.html"
Copy-Item "$root\assets\starter\deck.json" "$Dir\deck.json"
Copy-Item "$root\examples\bp-v2\deck.css" "$Dir\deck.css"
Get-ChildItem "$root\assets\starter\img" -File | Copy-Item -Destination "$Dir\img"
"project ready: $Dir"
Get-ChildItem $Dir -Recurse -File | Select-Object -ExpandProperty FullName
