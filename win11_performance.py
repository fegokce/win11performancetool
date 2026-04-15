"""
Win11 Debloat Tool - CLI
Çalıştırma: Admin olarak çalıştır
"""

import subprocess
import sys
import ctypes
import os
from typing import Callable

# ─── Renk kodları ────────────────────────────────────────────────────────────
class C:
    RESET  = "\033[0m"
    BOLD   = "\033[1m"
    RED    = "\033[91m"
    GREEN  = "\033[92m"
    YELLOW = "\033[93m"
    CYAN   = "\033[96m"
    WHITE  = "\033[97m"
    GRAY   = "\033[90m"

# ─── Yardımcı fonksiyonlar ────────────────────────────────────────────────────
def is_admin() -> bool:
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def run_cmd(cmd: str, shell: bool = True) -> tuple[bool, str]:
    try:
        result = subprocess.run(
            cmd,
            shell=shell,
            capture_output=True,
            text=True,
            timeout=60
        )
        return result.returncode == 0, result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        return False, "Zaman aşımı"
    except Exception as e:
        return False, str(e)

def run_ps(script: str) -> tuple[bool, str]:
    cmd = [
        "powershell.exe",
        "-NoProfile",
        "-NonInteractive",
        "-ExecutionPolicy", "Bypass",
        "-Command", script
    ]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120
        )
        return result.returncode == 0, result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        return False, "Zaman aşımı"
    except Exception as e:
        return False, str(e)

def ok(msg: str):
    print(f"  {C.GREEN}✓{C.RESET} {msg}")

def fail(msg: str, detail: str = ""):
    print(f"  {C.RED}✗{C.RESET} {msg}", end="")
    if detail:
        print(f" {C.GRAY}({detail.strip()[:80]}){C.RESET}", end="")
    print()

def skip(msg: str):
    print(f"  {C.YELLOW}─{C.RESET} {msg}")

def header(title: str):
    print(f"\n{C.CYAN}{C.BOLD}{'─'*55}{C.RESET}")
    print(f"{C.CYAN}{C.BOLD}  {title}{C.RESET}")
    print(f"{C.CYAN}{C.BOLD}{'─'*55}{C.RESET}")

def confirm(msg: str) -> bool:
    ans = input(f"\n{C.YELLOW}?{C.RESET} {msg} {C.GRAY}[e/H]{C.RESET}: ").strip().lower()
    return ans in ("e", "evet", "y", "yes")

def apply_step(description: str, fn: Callable) -> None:
    success, detail = fn()
    if success:
        ok(description)
    else:
        fail(description, detail)

# ─── 1. TELEMETRİ / GİZLİLİK ─────────────────────────────────────────────────
TELEMETRY_TASKS = [
    ("Telemetri servisi devre dışı (DiagTrack)",
     lambda: run_ps(
         'Stop-Service -Name "DiagTrack" -Force -ErrorAction SilentlyContinue; '
         'Set-Service -Name "DiagTrack" -StartupType Disabled'
     )),
    ("Telemetri servisi devre dışı (dmwappushservice)",
     lambda: run_ps(
         'Stop-Service -Name "dmwappushservice" -Force -ErrorAction SilentlyContinue; '
         'Set-Service -Name "dmwappushservice" -StartupType Disabled'
     )),
    ("Cortana devre dışı (kayıt defteri)",
     lambda: run_ps(
         'New-Item -Path "HKLM:\\SOFTWARE\\Policies\\Microsoft\\Windows\\Windows Search" '
         '-Force -ErrorAction SilentlyContinue | Out-Null; '
         'Set-ItemProperty -Path "HKLM:\\SOFTWARE\\Policies\\Microsoft\\Windows\\Windows Search" '
         '-Name "AllowCortana" -Value 0 -Type DWord -Force'
     )),
    ("Telemetri seviyesi 0 yap (kayıt defteri)",
     lambda: run_ps(
         'Set-ItemProperty -Path "HKLM:\\SOFTWARE\\Policies\\Microsoft\\Windows\\DataCollection" '
         '-Name "AllowTelemetry" -Value 0 -Type DWord -Force -ErrorAction SilentlyContinue'
     )),
    ("Reklam ID kapat",
     lambda: run_ps(
         'New-Item -Path "HKCU:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\AdvertisingInfo" '
         '-Force -ErrorAction SilentlyContinue | Out-Null; '
         'Set-ItemProperty -Path "HKCU:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\AdvertisingInfo" '
         '-Name "Enabled" -Value 0 -Type DWord -Force'
     )),
    ("Activity History kapat",
     lambda: run_ps(
         'Set-ItemProperty -Path "HKLM:\\SOFTWARE\\Policies\\Microsoft\\Windows\\System" '
         '-Name "EnableActivityFeed" -Value 0 -Type DWord -Force -ErrorAction SilentlyContinue; '
         'Set-ItemProperty -Path "HKLM:\\SOFTWARE\\Policies\\Microsoft\\Windows\\System" '
         '-Name "PublishUserActivities" -Value 0 -Type DWord -Force -ErrorAction SilentlyContinue'
     )),
    ("Konum servisi kapat",
     lambda: run_ps(
         'Set-ItemProperty -Path "HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\CapabilityAccessManager\\ConsentStore\\location" '
         '-Name "Value" -Value "Deny" -Type String -Force -ErrorAction SilentlyContinue'
     )),
    ("Feedback bildirimleri kapat",
     lambda: run_ps(
         'New-Item -Path "HKCU:\\SOFTWARE\\Microsoft\\Siuf\\Rules" -Force -ErrorAction SilentlyContinue | Out-Null; '
         'Set-ItemProperty -Path "HKCU:\\SOFTWARE\\Microsoft\\Siuf\\Rules" '
         '-Name "NumberOfSIUFInPeriod" -Value 0 -Type DWord -Force'
     )),
    ("Scheduled telemetri görevleri kapat",
     lambda: run_ps(
         '$tasks = @('
         '"\\Microsoft\\Windows\\Application Experience\\Microsoft Compatibility Appraiser",'
         '"\\Microsoft\\Windows\\Application Experience\\ProgramDataUpdater",'
         '"\\Microsoft\\Windows\\Autochk\\Proxy",'
         '"\\Microsoft\\Windows\\Customer Experience Improvement Program\\Consolidator",'
         '"\\Microsoft\\Windows\\Customer Experience Improvement Program\\UsbCeip",'
         '"\\Microsoft\\Windows\\DiskDiagnostic\\Microsoft-Windows-DiskDiagnosticDataCollector"'
         '); foreach ($t in $tasks) { '
         'Disable-ScheduledTask -TaskPath (Split-Path $t) -TaskName (Split-Path $t -Leaf) '
         '-ErrorAction SilentlyContinue }'
     )),
    ("Windows Error Reporting kapat",
     lambda: run_ps(
         'Disable-WindowsOptionalFeature -Online -FeatureName "Windows-Error-Reporting-Service" '
         '-NoRestart -ErrorAction SilentlyContinue | Out-Null; '
         'Set-ItemProperty -Path "HKLM:\\SOFTWARE\\Microsoft\\Windows\\Windows Error Reporting" '
         '-Name "Disabled" -Value 1 -Type DWord -Force -ErrorAction SilentlyContinue'
     )),
]

# ─── 2. BLOATWARE ─────────────────────────────────────────────────────────────
BLOATWARE_APPS = [
    "Microsoft.BingNews",
    "Microsoft.BingWeather",
    "Microsoft.BingFinance",
    "Microsoft.BingSports",
    "Microsoft.BingSearch",
    "Microsoft.GamingApp",
    "Microsoft.Xbox.TCUI",
    "Microsoft.XboxApp",
    "Microsoft.XboxGameOverlay",
    "Microsoft.XboxGamingOverlay",
    "Microsoft.XboxIdentityProvider",
    "Microsoft.XboxSpeechToTextOverlay",
    "Microsoft.MicrosoftTeams",
    "MicrosoftTeams",
    "Microsoft.Teams",
    "Microsoft.ZuneMusic",
    "Microsoft.ZuneVideo",
    "Microsoft.MicrosoftSolitaireCollection",
    "Microsoft.MicrosoftMahjong",
    "Microsoft.MicrosoftJigsaw",
    "Microsoft.People",
    "Microsoft.Todos",
    "Microsoft.WindowsFeedbackHub",
    "Microsoft.WindowsMaps",
    "Microsoft.WindowsAlarms",
    "Microsoft.WindowsSoundRecorder",
    "Microsoft.PowerAutomateDesktop",
    "Microsoft.549981C3F5F10",   # Cortana app
    "Microsoft.Office.OneNote",
    "Microsoft.SkypeApp",
    "Microsoft.YourPhone",
    "Microsoft.GetHelp",
    "Microsoft.Getstarted",
    "MicrosoftCorporationII.MicrosoftFamily",
    "Clipchamp.Clipchamp",
    "Microsoft.OutlookForWindows",  # new Outlook
    "Microsoft.MicrosoftOfficeHub",
    "Microsoft.OneDriveSync",
    "king.com.CandyCrushSaga",
    "king.com.CandyCrushFriends",
    "SpotifyAB.SpotifyMusic",
    "Disney.37853D22215B2",
    "TikTok",
    "BytedancePte.Ltd.TikTok",
]

def remove_bloatware():
    results = {"removed": 0, "skipped": 0, "failed": 0}
    for app in BLOATWARE_APPS:
        script = (
            f'$pkg = Get-AppxPackage -AllUsers -Name "{app}" -ErrorAction SilentlyContinue; '
            f'if ($pkg) {{ '
            f'Remove-AppxPackage -Package $pkg.PackageFullName -AllUsers -ErrorAction SilentlyContinue; '
            f'Get-AppxProvisionedPackage -Online | Where-Object DisplayName -like "{app}" | '
            f'Remove-AppxProvisionedPackage -Online -ErrorAction SilentlyContinue | Out-Null; '
            f'Write-Output "REMOVED" }} else {{ Write-Output "NOTFOUND" }}'
        )
        success, output = run_ps(script)
        if "REMOVED" in output:
            ok(f"Kaldırıldı: {app}")
            results["removed"] += 1
        elif "NOTFOUND" in output:
            skip(f"Bulunamadı (zaten yok): {app}")
            results["skipped"] += 1
        else:
            fail(f"Hata: {app}", output)
            results["failed"] += 1
    return results

# ─── 3. PERFORMANS OPTİMİZASYONU ─────────────────────────────────────────────
PERF_TASKS = [
    ("Güç planı: Yüksek Performans",
     lambda: run_cmd("powercfg /setactive 8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c")),
    ("Hızlı başlatma kapat (uyku sorunlarını önler)",
     lambda: run_cmd("powercfg /h off")),
    ("SysMain (Superfetch) servis kapat",
     lambda: run_ps(
         'Stop-Service -Name "SysMain" -Force -ErrorAction SilentlyContinue; '
         'Set-Service -Name "SysMain" -StartupType Disabled'
     )),
    ("Windows Search indexleme servis kapat",
     lambda: run_ps(
         'Stop-Service -Name "WSearch" -Force -ErrorAction SilentlyContinue; '
         'Set-Service -Name "WSearch" -StartupType Disabled'
     )),
    ("Görsel efektler: En iyi performans",
     lambda: run_ps(
         'Set-ItemProperty -Path "HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\VisualEffects" '
         '-Name "VisualFXSetting" -Value 2 -Type DWord -Force -ErrorAction SilentlyContinue'
     )),
    ("Şeffaflık efektleri kapat",
     lambda: run_ps(
         'Set-ItemProperty -Path "HKCU:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Themes\\Personalize" '
         '-Name "EnableTransparency" -Value 0 -Type DWord -Force -ErrorAction SilentlyContinue'
     )),
    ("Animasyonlar kapat",
     lambda: run_ps(
         'Set-ItemProperty -Path "HKCU:\\Control Panel\\Desktop\\WindowMetrics" '
         '-Name "MinAnimate" -Value 0 -Type String -Force -ErrorAction SilentlyContinue; '
         'Set-ItemProperty -Path "HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Advanced" '
         '-Name "TaskbarAnimations" -Value 0 -Type DWord -Force -ErrorAction SilentlyContinue'
     )),
    ("GameDVR (Xbox Game Bar kayıt) kapat",
     lambda: run_ps(
         'Set-ItemProperty -Path "HKCU:\\System\\GameConfigStore" '
         '-Name "GameDVR_Enabled" -Value 0 -Type DWord -Force -ErrorAction SilentlyContinue; '
         'Set-ItemProperty -Path "HKLM:\\SOFTWARE\\Policies\\Microsoft\\Windows\\GameDVR" '
         '-Name "AllowGameDVR" -Value 0 -Type DWord -Force -ErrorAction SilentlyContinue'
     )),
    ("Print Spooler servis kapat (yazıcı yoksa)",
     lambda: run_ps(
         'Stop-Service -Name "Spooler" -Force -ErrorAction SilentlyContinue; '
         'Set-Service -Name "Spooler" -StartupType Disabled'
     )),
    ("Remote Registry servis kapat",
     lambda: run_ps(
         'Stop-Service -Name "RemoteRegistry" -Force -ErrorAction SilentlyContinue; '
         'Set-Service -Name "RemoteRegistry" -StartupType Disabled'
     )),
    ("Fax servisi kapat",
     lambda: run_ps(
         'Stop-Service -Name "Fax" -Force -ErrorAction SilentlyContinue; '
         'Set-Service -Name "Fax" -StartupType Disabled'
     )),
    ("NTFS son erişim zamanı damgası kapat",
     lambda: run_cmd("fsutil behavior set disablelastaccess 1")),
    ("Prefetch aktif tut (SSD için de yararlı)",
     lambda: run_ps(
         'Set-ItemProperty -Path "HKLM:\\SYSTEM\\CurrentControlSet\\Control\\Session Manager\\Memory Management\\PrefetchParameters" '
         '-Name "EnablePrefetcher" -Value 3 -Type DWord -Force -ErrorAction SilentlyContinue'
     )),
]

# ─── 4. WINDOWS UPDATE ────────────────────────────────────────────────────────
UPDATE_TASKS = [
    ("Windows Update: Sadece güvenlik güncellemeleri (otomatik driver güncelleme kapat)",
     lambda: run_ps(
         'New-Item -Path "HKLM:\\SOFTWARE\\Policies\\Microsoft\\Windows\\WindowsUpdate" '
         '-Force -ErrorAction SilentlyContinue | Out-Null; '
         'New-Item -Path "HKLM:\\SOFTWARE\\Policies\\Microsoft\\Windows\\WindowsUpdate\\AU" '
         '-Force -ErrorAction SilentlyContinue | Out-Null; '
         'Set-ItemProperty -Path "HKLM:\\SOFTWARE\\Policies\\Microsoft\\Windows\\WindowsUpdate" '
         '-Name "ExcludeWUDriversInQualityUpdate" -Value 1 -Type DWord -Force'
     )),
    ("Otomatik yeniden başlatma kapat",
     lambda: run_ps(
         'Set-ItemProperty -Path "HKLM:\\SOFTWARE\\Policies\\Microsoft\\Windows\\WindowsUpdate\\AU" '
         '-Name "NoAutoRebootWithLoggedOnUsers" -Value 1 -Type DWord -Force -ErrorAction SilentlyContinue'
     )),
    ("Windows Update P2P (diğer bilgisayarlara dağıtım) kapat",
     lambda: run_ps(
         'New-Item -Path "HKLM:\\SOFTWARE\\Policies\\Microsoft\\Windows\\DeliveryOptimization" '
         '-Force -ErrorAction SilentlyContinue | Out-Null; '
         'Set-ItemProperty -Path "HKLM:\\SOFTWARE\\Policies\\Microsoft\\Windows\\DeliveryOptimization" '
         '-Name "DODownloadMode" -Value 0 -Type DWord -Force'
     )),
    ("Microsoft Store otomatik güncelleme kapat",
     lambda: run_ps(
         'New-Item -Path "HKLM:\\SOFTWARE\\Policies\\Microsoft\\WindowsStore" '
         '-Force -ErrorAction SilentlyContinue | Out-Null; '
         'Set-ItemProperty -Path "HKLM:\\SOFTWARE\\Policies\\Microsoft\\WindowsStore" '
         '-Name "AutoDownload" -Value 2 -Type DWord -Force'
     )),
    ("Windows Update servisi manuel moda al (devre dışı değil, sadece otomatik başlamaz)",
     lambda: run_ps(
         'Set-Service -Name "wuauserv" -StartupType Manual -ErrorAction SilentlyContinue'
     )),
]

# ─── MENÜ ─────────────────────────────────────────────────────────────────────
def print_banner():
    print(f"""
{C.CYAN}{C.BOLD}
  ██████╗ ███████╗██████╗ ██╗      ██████╗  █████╗ ████████╗
  ██╔══██╗██╔════╝██╔══██╗██║     ██╔═══██╗██╔══██╗╚══██╔══╝
  ██║  ██║█████╗  ██████╔╝██║     ██║   ██║███████║   ██║   
  ██║  ██║██╔══╝  ██╔══██╗██║     ██║   ██║██╔══██║   ██║   
  ██████╔╝███████╗██████╔╝███████╗╚██████╔╝██║  ██║   ██║   
  ╚═════╝ ╚══════╝╚═════╝ ╚══════╝ ╚═════╝ ╚═╝  ╚═╝   ╚═╝   
{C.RESET}{C.GRAY}  Win11 Debloat Tool  |  github.com/fegokce  |  v1.0{C.RESET}
""")

def print_menu():
    print(f"""
{C.BOLD}  Ana Menü:{C.RESET}

  {C.CYAN}[1]{C.RESET} Telemetri & Gizlilik    ({len(TELEMETRY_TASKS)} işlem)
  {C.CYAN}[2]{C.RESET} Bloatware Kaldır        ({len(BLOATWARE_APPS)} uygulama)
  {C.CYAN}[3]{C.RESET} Performans Optimizasyonu ({len(PERF_TASKS)} işlem)
  {C.CYAN}[4]{C.RESET} Windows Update Ayarları  ({len(UPDATE_TASKS)} işlem)
  {C.CYAN}[5]{C.RESET} HEPSİNİ UYGULA
  {C.CYAN}[0]{C.RESET} Çıkış
""")

def run_task_list(tasks: list[tuple[str, Callable]]):
    for desc, fn in tasks:
        apply_step(desc, fn)

def module_telemetry():
    header("1 / Telemetri & Gizlilik")
    if not confirm("Telemetri ve gizlilik ayarları uygulanacak. Devam?"):
        return
    run_task_list(TELEMETRY_TASKS)

def module_bloatware():
    header("2 / Bloatware Kaldır")
    print(f"\n  {C.GRAY}Kaldırılacak uygulama sayısı: {len(BLOATWARE_APPS)}{C.RESET}")
    if not confirm("Bu işlem geri alınamaz. Devam?"):
        return
    results = remove_bloatware()
    print(f"\n  {C.GREEN}Kaldırıldı: {results['removed']}{C.RESET}  "
          f"{C.YELLOW}Zaten yok: {results['skipped']}{C.RESET}  "
          f"{C.RED}Hata: {results['failed']}{C.RESET}")

def module_performance():
    header("3 / Performans Optimizasyonu")
    print(f"\n  {C.YELLOW}Not:{C.RESET} Print Spooler kapatılacak. Yazıcı kullanıyorsan atlamak için H de.")
    if not confirm("Performans optimizasyonları uygulanacak. Devam?"):
        return
    run_task_list(PERF_TASKS)

def module_update():
    header("4 / Windows Update Ayarları")
    if not confirm("Windows Update politikaları değiştirilecek. Devam?"):
        return
    run_task_list(UPDATE_TASKS)

def module_all():
    header("TÜM MODÜLLER")
    print(f"""
  {C.YELLOW}Uyarı:{C.RESET} Tüm modüller sırayla çalışacak:
   • Telemetri & Gizlilik
   • Bloatware Kaldır
   • Performans Optimizasyonu
   • Windows Update Ayarları
""")
    if not confirm("Tüm işlemler uygulanacak. Emin misin?"):
        return
    module_telemetry_silent()
    module_bloatware_silent()
    module_performance_silent()
    module_update_silent()
    print(f"\n{C.GREEN}{C.BOLD}  ✓ Tüm işlemler tamamlandı!{C.RESET}")
    print(f"  {C.YELLOW}Değişikliklerin tam etkisi için bilgisayarı yeniden başlat.{C.RESET}")

# Sessiz (confirm almayan) versiyonlar — "hepsi" modu için
def module_telemetry_silent():
    header("Telemetri & Gizlilik")
    run_task_list(TELEMETRY_TASKS)

def module_bloatware_silent():
    header("Bloatware Kaldır")
    results = remove_bloatware()
    print(f"\n  {C.GREEN}Kaldırıldı: {results['removed']}{C.RESET}  "
          f"{C.YELLOW}Zaten yok: {results['skipped']}{C.RESET}  "
          f"{C.RED}Hata: {results['failed']}{C.RESET}")

def module_performance_silent():
    header("Performans Optimizasyonu")
    run_task_list(PERF_TASKS)

def module_update_silent():
    header("Windows Update Ayarları")
    run_task_list(UPDATE_TASKS)

# ─── ANA DÖNGÜ ────────────────────────────────────────────────────────────────
def main():
    # Windows konsolunda ANSI renk desteği aç
    if sys.platform == "win32":
        os.system("color")
        import ctypes
        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)

    if not is_admin():
        print(f"\n{C.RED}{C.BOLD}  HATA: Bu tool Administrator olarak çalıştırılmalıdır!{C.RESET}")
        print(f"  {C.GRAY}Sağ tık → 'Yönetici olarak çalıştır'{C.RESET}\n")
        input("  Çıkmak için Enter'a bas...")
        sys.exit(1)

    print_banner()

    while True:
        print_menu()
        choice = input(f"{C.WHITE}  Seçim: {C.RESET}").strip()

        if choice == "1":
            module_telemetry()
        elif choice == "2":
            module_bloatware()
        elif choice == "3":
            module_performance()
        elif choice == "4":
            module_update()
        elif choice == "5":
            module_all()
        elif choice == "0":
            print(f"\n{C.GRAY}  Çıkılıyor...{C.RESET}\n")
            sys.exit(0)
        else:
            print(f"  {C.YELLOW}Geçersiz seçim.{C.RESET}")

        input(f"\n{C.GRAY}  Menüye dönmek için Enter'a bas...{C.RESET}")

if __name__ == "__main__":
    main()
