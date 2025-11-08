# 🚀 Szybki Start - Budowanie APK

## ✅ Wszystko jest gotowe!

Buildozer jest zainstalowany i skonfigurowany. Możesz teraz zbudować APK **jednym kliknięciem**!

## 🎯 Jak zbudować APK

### Opcja 1: Automatyczny skrypt (NAJŁATWIEJSZE)

**Po prostu kliknij dwukrotnie:**
```
BUILD_APK_AUTO.bat
```

To wszystko! Skrypt automatycznie:
- ✅ Uruchomi buildozer w WSL
- ✅ Zbuduje APK
- ✅ Pokaże gdzie znajdziesz plik APK

### Opcja 2: Ręcznie w WSL

W terminalu WSL:
```bash
cd /mnt/c/Users/admin/Projects/mapy
~/.local/bin/buildozer android debug
```

## ⏳ Czas budowania

- **Pierwsza kompilacja:** 30-60 minut (pobierze Android SDK/NDK)
- **Kolejne kompilacje:** 5-15 minut

## 📱 Gdzie znajdziesz APK?

Po zakończeniu budowania, plik APK będzie w:
```
bin/goodspeedrouteanalyzer-0.1-arm64-v8a-debug.apk
```
lub
```
bin/goodspeedrouteanalyzer-0.1-armeabi-v7a-debug.apk
```

## 🔧 Co jeśli coś nie działa?

1. **Sprawdź czy masz wystarczająco miejsca na dysku** (minimum 5GB)
2. **Upewnij się, że masz połączenie z internetem** (pierwsza kompilacja pobiera SDK)
3. **Sprawdź logi** - buildozer pokaże szczegóły błędów

## 📋 Co jest już skonfigurowane?

✅ Buildozer zainstalowany  
✅ Plik buildozer.spec skonfigurowany  
✅ Wszystkie zależności zdefiniowane  
✅ Uprawnienia Android (GPS, Internet)  
✅ Java zainstalowana  

## 🎉 Gotowe do startu!

Kliknij `BUILD_APK_AUTO.bat` i czekaj! 🚀

