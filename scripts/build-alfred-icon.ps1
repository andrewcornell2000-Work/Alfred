#Requires -Version 5.1
<#
.SYNOPSIS
    Build assets/alfred.ico from a transparent PNG source with proper alpha.
#>
param(
    [string]$SourcePng = (Join-Path $PSScriptRoot "..\assets\alfred-source.png"),
    [string]$OutputIco = (Join-Path $PSScriptRoot "..\assets\alfred.ico"),
    [int[]]$Sizes = @(256, 48, 32, 16)
)

$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing

function Get-SquareBitmap([System.Drawing.Image]$Source, [int]$Size) {
    $canvas = New-Object System.Drawing.Bitmap $Size, $Size, ([System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
    $graphics = [System.Drawing.Graphics]::FromImage($canvas)
    $graphics.Clear([System.Drawing.Color]::Transparent)
    $graphics.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
    $graphics.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::HighQuality
    $graphics.PixelOffsetMode = [System.Drawing.Drawing2D.PixelOffsetMode]::HighQuality

    $scale = [Math]::Min($Size / $Source.Width, $Size / $Source.Height) * 0.82
    $drawW = [int]($Source.Width * $scale)
    $drawH = [int]($Source.Height * $scale)
    $x = [int](($Size - $drawW) / 2)
    $y = [int](($Size - $drawH) / 2)
    $graphics.DrawImage($Source, $x, $y, $drawW, $drawH)
    $graphics.Dispose()
    return $canvas
}

function Write-PngIco {
    param(
        [System.Drawing.Bitmap[]]$Images,
        [string]$Path
    )

    $msList = New-Object System.Collections.Generic.List[byte[]]
    foreach ($img in $Images) {
        $ms = New-Object System.IO.MemoryStream
        $img.Save($ms, [System.Drawing.Imaging.ImageFormat]::Png)
        $msList.Add($ms.ToArray()) | Out-Null
        $ms.Dispose()
    }

    $count = $Images.Count
    $headerSize = 6 + (16 * $count)
    $offset = $headerSize
    $fs = [System.IO.File]::Create($Path)
    $bw = New-Object System.IO.BinaryWriter($fs)

    $bw.Write([uint16]0)
    $bw.Write([uint16]1)
    $bw.Write([uint16]$count)

    for ($i = 0; $i -lt $count; $i++) {
        $size = $Images[$i].Width
        $bw.Write([byte]([Math]::Min($size, 255)))
        $bw.Write([byte]([Math]::Min($size, 255)))
        $bw.Write([byte]0)
        $bw.Write([byte]0)
        $bw.Write([uint16]1)
        $bw.Write([uint16]32)
        $bw.Write([uint32]$msList[$i].Length)
        $bw.Write([uint32]$offset)
        $offset += $msList[$i].Length
    }

    foreach ($bytes in $msList) { $bw.Write($bytes) }
    $bw.Close()
    $fs.Close()
}

if (-not (Test-Path $SourcePng)) {
    throw "Source PNG not found: $SourcePng"
}

$source = [System.Drawing.Bitmap]::FromFile($SourcePng)
$bitmaps = foreach ($size in $Sizes) { Get-SquareBitmap $source $size }
Write-PngIco -Images $bitmaps -Path $OutputIco
$source.Dispose()
foreach ($bmp in $bitmaps) { $bmp.Dispose() }

Write-Host "Wrote $OutputIco ($($Sizes -join ', ') px, alpha preserved)"
