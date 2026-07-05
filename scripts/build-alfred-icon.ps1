#Requires -Version 5.1
<#
.SYNOPSIS
    Build assets/alfred.ico from a transparent PNG source.
    Writes classic BMP-based ICO (required for ps2exe / Windows exe embedding).
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

function Get-ClassicIconImageBytes([System.Drawing.Bitmap]$Bitmap) {
    $width = $Bitmap.Width
    $height = $Bitmap.Height
    $pixelCount = $width * $height
    $andMaskRowBytes = [int][Math]::Ceiling($width / 8.0)
    $andMaskSize = $andMaskRowBytes * $height

    $ms = New-Object System.IO.MemoryStream
    $bw = New-Object System.IO.BinaryWriter($ms)

    # BITMAPINFOHEADER
    $bw.Write([uint32]40)
    $bw.Write([int32]$width)
    $bw.Write([int32]($height * 2))
    $bw.Write([uint16]1)
    $bw.Write([uint16]32)
    $bw.Write([uint32]0)
    $bw.Write([uint32]0)
    $bw.Write([int32]0)
    $bw.Write([int32]0)
    $bw.Write([uint32]0)
    $bw.Write([uint32]0)

    $rect = New-Object System.Drawing.Rectangle 0, 0, $width, $height
    $data = $Bitmap.LockBits($rect, [System.Drawing.Imaging.ImageLockMode]::ReadOnly, [System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
    try {
        $stride = $data.Stride
        $row = New-Object byte[] (4 * $width)
        for ($y = $height - 1; $y -ge 0; $y--) {
            [System.Runtime.InteropServices.Marshal]::Copy([IntPtr]::Add($data.Scan0, $y * $stride), $row, 0, $row.Length)
            for ($x = 0; $x -lt $width; $x++) {
                $i = $x * 4
                $bw.Write($row[$i])     # B
                $bw.Write($row[$i + 1]) # G
                $bw.Write($row[$i + 2]) # R
                $bw.Write($row[$i + 3]) # A
            }
        }
    } finally {
        $Bitmap.UnlockBits($data)
    }

    $bw.Write((New-Object byte[] $andMaskSize))
    $bytes = $ms.ToArray()
    $bw.Close()
    $ms.Close()
    return $bytes
}

function Write-ClassicIco {
    param(
        [System.Drawing.Bitmap[]]$Images,
        [string]$Path
    )

    $imageBytes = @($Images | ForEach-Object { Get-ClassicIconImageBytes $_ })
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
        $bw.Write([uint32]$imageBytes[$i].Length)
        $bw.Write([uint32]$offset)
        $offset += $imageBytes[$i].Length
    }

    foreach ($bytes in $imageBytes) { $bw.Write($bytes) }
    $bw.Close()
    $fs.Close()
}

if (-not (Test-Path $SourcePng)) {
    throw "Source PNG not found: $SourcePng"
}

$source = [System.Drawing.Bitmap]::FromFile($SourcePng)
$bitmaps = @($Sizes | ForEach-Object { Get-SquareBitmap $source $_ })
Write-ClassicIco -Images $bitmaps -Path $OutputIco
$source.Dispose()
foreach ($bmp in $bitmaps) { $bmp.Dispose() }

Write-Host "Wrote $OutputIco ($($Sizes -join ', ') px, classic ICO for exe embedding)"
