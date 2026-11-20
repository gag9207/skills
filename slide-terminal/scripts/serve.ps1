param([string]$Root, [int]$Port = 8770, [int]$Minutes = 20)
# Tiny static file server for checking local pages in the browser pane. Re-reads files on every request.
$l = New-Object System.Net.HttpListener
$l.Prefixes.Add("http://localhost:$Port/")
$l.Start()
$deadline = (Get-Date).AddMinutes($Minutes)
while ((Get-Date) -lt $deadline) {
  $t = $l.GetContextAsync()
  while (-not $t.Wait(500)) { if ((Get-Date) -ge $deadline) { break } }
  if (-not $t.IsCompleted) { break }
  $c = $t.Result
  $name = [Uri]::UnescapeDataString($c.Request.Url.AbsolutePath.TrimStart('/'))
  $path = Join-Path $Root $name
  if ((Test-Path $path -PathType Leaf)) {
    $bytes = [IO.File]::ReadAllBytes($path)
    $c.Response.ContentType = 'text/html; charset=utf-8'
    $c.Response.OutputStream.Write($bytes, 0, $bytes.Length)
  } else { $c.Response.StatusCode = 404 }
  $c.Response.Close()
}
$l.Stop()
