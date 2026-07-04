# Alfred app icons

| File | Use |
|------|-----|
| `alfred.ico` | Windows shortcuts, `Alfred.exe`, `Alfred-Install.exe`, system tray |
| `alfred-icon-512.png` | Source PNG (512×512) |
| `alfred.png` | Legacy/alternate PNG |

Regenerate ICO after editing PNG:

```powershell
python -c "from PIL import Image; Image.open('assets/alfred-icon-512.png').save('assets/alfred.ico', sizes=[(s,s) for s in [16,32,48,64,128,256]])"
```

Built into exes via `build-installer.ps1 -icon assets\alfred.ico`.
