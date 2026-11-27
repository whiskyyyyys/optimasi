"""Privacy, Telemetry, AI/Copilot removal, Hosts Blocker, and AppX Debloat tweaks."""

from __future__ import annotations

import subprocess

from optimasi.tweaks.models import (
    AppxRemove,
    Cmd,
    HostsBlock,
    RegDelete,
    RegSet,
    RiskLevel,
    ScheduledTask,
    ServiceConfig,
    Tweak,
)

CATEGORY_PRIVACY = "Privacy & Debloat"
_CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)


def get_installed_bloat_appx() -> set[str]:
    """Return a set of SAFE_BLOAT_APPX package keys currently installed on this Windows PC."""
    try:
        res = subprocess.run(
            ["powershell", "-NoProfile", "-Command", "Get-AppxPackage | Select-Object -ExpandProperty Name"],
            capture_output=True,
            text=True,
            timeout=12,
            creationflags=_CREATE_NO_WINDOW,
        )
        installed_raw = {line.strip().lower() for line in (res.stdout or "").splitlines() if line.strip()}
        matched: set[str] = set()
        for pkg, _ in SAFE_BLOAT_APPX:
            pkg_l = pkg.lower()
            if any(pkg_l in name for name in installed_raw):
                matched.add(pkg)
        return matched
    except Exception:
        return set()

TELEMETRY_DOMAINS = [
    "config.edge.skype.com",
    "arc.msn.com",
    "ris.api.iris.microsoft.com",
    "api.msn.com",
    "assets.msn.com",
    "c.msn.com",
    "g.msn.com",
    "ntp.msn.com",
    "srtb.msn.com",
    "www.msn.com",
    "fd.api.iris.microsoft.com",
    "staticview.msn.com",
    "mucp.api.account.microsoft.com",
    "query.prod.cms.rt.microsoft.com",
    "functional.events.data.microsoft.com",
    "browser.events.data.msn.com",
    "self.events.data.microsoft.com",
    "v10.events.data.microsoft.com",
    "v10c.events.data.microsoft.com",
    "us-v10c.events.data.microsoft.com",
    "eu-v10c.events.data.microsoft.com",
    "v10.vortex-win.data.microsoft.com",
    "vortex-win.data.microsoft.com",
    "telemetry.microsoft.com",
    "watson.telemetry.microsoft.com",
    "oca.telemetry.microsoft.com",
    "settings-win.data.microsoft.com",
    "vortex.data.microsoft.com",
    "telecommand.telemetry.microsoft.com",
    "statsfe2.ws.microsoft.com",
    "diagnostics.support.microsoft.com",
    "corp.sts.microsoft.com",
    "feedback.microsoft-hohm.com",
    "feedback.search.microsoft.com",
    "rad.msn.com",
    "ads.msn.com",
]

SAFE_BLOAT_APPX: list[tuple[str, str]] = [
    ("Microsoft.549981C3F5F10", "Cortana"),
    ("Clipchamp.Clipchamp", "Clipchamp Video Editor"),
    ("Microsoft.BingNews", "Microsoft News"),
    ("Microsoft.BingWeather", "Microsoft Weather"),
    ("Microsoft.BingSearch", "Bing Web Search App"),
    ("Microsoft.GetHelp", "Get Help"),
    ("Microsoft.Getstarted", "Windows Tips / Get Started"),
    ("Microsoft.MicrosoftSolitaireCollection", "Solitaire Collection"),
    ("Microsoft.People", "Microsoft People"),
    ("Microsoft.PowerAutomateDesktop", "Power Automate Desktop"),
    ("Microsoft.WindowsFeedbackHub", "Feedback Hub"),
    ("Microsoft.WindowsMaps", "Windows Maps"),
    ("Microsoft.ZuneMusic", "Groove / Media Player Legacy"),
    ("Microsoft.ZuneVideo", "Movies & TV"),
    ("Microsoft.YourPhone", "Phone Link"),
    ("MicrosoftTeams", "Microsoft Teams (Consumer)"),
    ("Microsoft.Todos", "Microsoft To Do"),
    ("Microsoft.MicrosoftOfficeHub", "Microsoft 365 Office Hub"),
    ("Microsoft.Copilot", "Windows Copilot App"),
    ("MicrosoftCorporationII.QuickAssist", "Quick Assist"),
]


def get_privacy_tweaks() -> list[Tweak]:
    return [
        Tweak(
            id="priv_telemetry_diag",
            name="Disable Windows Telemetry & Diagnostic Services",
            category=CATEGORY_PRIVACY,
            risk=RiskLevel.SAFE,
            source="HI+Optimizer V6 / CTT WinUtil",
            description="Sets AllowTelemetry=0, disables Feedback notifications, WER error reporting, and disables DiagTrack & dmwappushservice.",
            default_selected=True,
            tags=["privacy", "telemetry", "diagtrack"],
            apply_actions=[
                RegSet("HKLM", r"SOFTWARE\Policies\Microsoft\Windows\DataCollection", "AllowTelemetry", 0),
                RegSet("HKLM", r"SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\DataCollection", "AllowTelemetry", 0),
                RegSet("HKLM", r"SOFTWARE\Policies\Microsoft\Windows\DataCollection", "DoNotShowFeedbackNotifications", 1),
                RegSet("HKLM", r"SOFTWARE\Microsoft\Windows\Windows Error Reporting", "Disabled", 1),
                RegSet("HKCU", r"SOFTWARE\Microsoft\Siuf\Rules", "NumberOfSIUFInPeriod", 0),
                RegDelete("HKCU", r"SOFTWARE\Microsoft\Siuf\Rules", "PeriodInNanoSeconds"),
                ServiceConfig("DiagTrack", "disabled", "stopped"),
                ServiceConfig("dmwappushservice", "disabled", "stopped"),
            ],
            revert_actions=[
                RegDelete("HKLM", r"SOFTWARE\Policies\Microsoft\Windows\DataCollection", "AllowTelemetry"),
                RegSet("HKLM", r"SOFTWARE\Microsoft\Windows\Windows Error Reporting", "Disabled", 0),
                ServiceConfig("DiagTrack", "auto", "running"),
            ],
        ),
        Tweak(
            id="priv_disable_ai_copilot",
            name="Disable Windows 11 Copilot & AI Recall Snapshots",
            category=CATEGORY_PRIVACY,
            risk=RiskLevel.SAFE,
            source="Win11Debloat / CTT WinUtil",
            description="Disables Windows Copilot button/service, Recall AI data analysis, and Edge AI Copilot sidebar.",
            default_selected=True,
            tags=["ai", "copilot", "recall", "win11"],
            apply_actions=[
                RegSet("HKCU", r"Software\Policies\Microsoft\Windows\WindowsCopilot", "TurnOffWindowsCopilot", 1),
                RegSet("HKLM", r"SOFTWARE\Policies\Microsoft\Windows\WindowsCopilot", "TurnOffWindowsCopilot", 1),
                RegSet("HKCU", r"Software\Policies\Microsoft\Windows\WindowsAI", "DisableAIDataAnalysis", 1),
                RegSet("HKLM", r"SOFTWARE\Policies\Microsoft\Windows\WindowsAI", "DisableAIDataAnalysis", 1),
                RegSet("HKCU", r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced", "ShowCopilotButton", 0),
            ],
            revert_actions=[
                RegDelete("HKCU", r"Software\Policies\Microsoft\Windows\WindowsCopilot", "TurnOffWindowsCopilot"),
                RegDelete("HKLM", r"SOFTWARE\Policies\Microsoft\Windows\WindowsCopilot", "TurnOffWindowsCopilot"),
                RegDelete("HKCU", r"Software\Policies\Microsoft\Windows\WindowsAI", "DisableAIDataAnalysis"),
                RegDelete("HKLM", r"SOFTWARE\Policies\Microsoft\Windows\WindowsAI", "DisableAIDataAnalysis"),
                RegSet("HKCU", r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced", "ShowCopilotButton", 1),
            ],
        ),
        Tweak(
            id="priv_debloat_edge",
            name="Debloat Microsoft Edge (Stop Background Boost, AI & Shopping)",
            category=CATEGORY_PRIVACY,
            risk=RiskLevel.SAFE,
            source="Win11Debloat / Privacy.sexy",
            description="Stops Edge from pre-launching in background at Windows startup and disables Hubs Sidebar, Shopping Assistant & telemetry.",
            default_selected=True,
            tags=["edge", "browser", "ram", "debloat"],
            apply_actions=[
                RegSet("HKLM", r"SOFTWARE\Policies\Microsoft\Edge", "StartupBoostEnabled", 0),
                RegSet("HKLM", r"SOFTWARE\Policies\Microsoft\Edge", "BackgroundModeEnabled", 0),
                RegSet("HKLM", r"SOFTWARE\Policies\Microsoft\Edge", "HubsSidebarEnabled", 0),
                RegSet("HKLM", r"SOFTWARE\Policies\Microsoft\Edge", "EdgeShoppingAssistantEnabled", 0),
                RegSet("HKLM", r"SOFTWARE\Policies\Microsoft\Edge", "ShowRecommendationsEnabled", 0),
                RegSet("HKLM", r"SOFTWARE\Policies\Microsoft\Edge", "PersonalizationReportingEnabled", 0),
            ],
            revert_actions=[
                RegDelete("HKLM", r"SOFTWARE\Policies\Microsoft\Edge", "StartupBoostEnabled"),
                RegDelete("HKLM", r"SOFTWARE\Policies\Microsoft\Edge", "BackgroundModeEnabled"),
                RegDelete("HKLM", r"SOFTWARE\Policies\Microsoft\Edge", "HubsSidebarEnabled"),
                RegDelete("HKLM", r"SOFTWARE\Policies\Microsoft\Edge", "EdgeShoppingAssistantEnabled"),
            ],
        ),
        Tweak(
            id="priv_ads_spotlight",
            name="Disable Ads, Activity Feed, Content Delivery & Spotlight Bloat",
            category=CATEGORY_PRIVACY,
            risk=RiskLevel.SAFE,
            source="HI+Optimizer V6 / Win11Debloat",
            description="Stops silent auto-installed promotional apps, Start Menu suggestions, Advertising ID, and Activity History tracking.",
            default_selected=True,
            tags=["ads", "privacy", "spotlight", "bloat"],
            apply_actions=[
                RegSet("HKLM", r"SOFTWARE\Policies\Microsoft\Windows\System", "EnableActivityFeed", 0),
                RegSet("HKLM", r"SOFTWARE\Policies\Microsoft\Windows\System", "PublishUserActivities", 0),
                RegSet("HKLM", r"SOFTWARE\Policies\Microsoft\Windows\System", "UploadUserActivities", 0),
                RegSet("HKLM", r"SOFTWARE\Policies\Microsoft\Windows\AdvertisingInfo", "DisabledByGroupPolicy", 1),
                RegSet("HKLM", r"SOFTWARE\Policies\Microsoft\Windows\CloudContent", "DisableWindowsConsumerFeatures", 1),
                RegSet("HKCU", r"SOFTWARE\Policies\Microsoft\Windows\CloudContent", "DisableTailoredExperiencesWithDiagnosticData", 1),
                RegSet("HKCU", r"SOFTWARE\Microsoft\Windows\CurrentVersion\ContentDeliveryManager", "ContentDeliveryAllowed", 0),
                RegSet("HKCU", r"SOFTWARE\Microsoft\Windows\CurrentVersion\ContentDeliveryManager", "SilentInstalledAppsEnabled", 0),
                RegSet("HKCU", r"SOFTWARE\Microsoft\Windows\CurrentVersion\ContentDeliveryManager", "SystemPaneSuggestionsEnabled", 0),
                RegSet("HKCU", r"SOFTWARE\Microsoft\Windows\CurrentVersion\ContentDeliveryManager", "SubscribedContent-338388Enabled", 0),
                RegSet("HKCU", r"SOFTWARE\Microsoft\Windows\CurrentVersion\ContentDeliveryManager", "SubscribedContent-338389Enabled", 0),
                RegSet("HKCU", r"Software\Microsoft\Windows\CurrentVersion\UserProfileEngagement", "ScoobeSystemSettingEnabled", 0),
            ],
            revert_actions=[
                RegDelete("HKLM", r"SOFTWARE\Policies\Microsoft\Windows\AdvertisingInfo", "DisabledByGroupPolicy"),
                RegDelete("HKLM", r"SOFTWARE\Policies\Microsoft\Windows\CloudContent", "DisableWindowsConsumerFeatures"),
                RegSet("HKCU", r"SOFTWARE\Microsoft\Windows\CurrentVersion\ContentDeliveryManager", "ContentDeliveryAllowed", 1),
            ],
        ),
        Tweak(
            id="priv_telemetry_tasks",
            name="Disable Telemetry & CEIP Scheduled Background Tasks",
            category=CATEGORY_PRIVACY,
            risk=RiskLevel.SAFE,
            source="HI+Optimizer V6 / CTT WinUtil",
            description="Disables Microsoft Compatibility Appraiser, ProgramDataUpdater, Consolidator, UsbCeip, WinSAT, and QueueReporting.",
            default_selected=True,
            tags=["tasks", "telemetry", "ceip", "cpu"],
            apply_actions=[
                ScheduledTask(r"\Microsoft\Windows\Application Experience\Microsoft Compatibility Appraiser", False),
                ScheduledTask(r"\Microsoft\Windows\Application Experience\ProgramDataUpdater", False),
                ScheduledTask(r"\Microsoft\Windows\Customer Experience Improvement Program\Consolidator", False),
                ScheduledTask(r"\Microsoft\Windows\Customer Experience Improvement Program\UsbCeip", False),
                ScheduledTask(r"\Microsoft\Windows\Maintenance\WinSAT", False),
                ScheduledTask(r"\Microsoft\Windows\Windows Error Reporting\QueueReporting", False),
            ],
            revert_actions=[
                ScheduledTask(r"\Microsoft\Windows\Application Experience\Microsoft Compatibility Appraiser", True),
                ScheduledTask(r"\Microsoft\Windows\Application Experience\ProgramDataUpdater", True),
                ScheduledTask(r"\Microsoft\Windows\Customer Experience Improvement Program\Consolidator", True),
                ScheduledTask(r"\Microsoft\Windows\Customer Experience Improvement Program\UsbCeip", True),
                ScheduledTask(r"\Microsoft\Windows\Maintenance\WinSAT", True),
            ],
        ),
        Tweak(
            id="priv_hosts_blocker",
            name="Block Microsoft/MSN Telemetry & Ad Domains in Hosts File",
            category=CATEGORY_PRIVACY,
            risk=RiskLevel.MODERATE,
            source="HI+Optimizer V6 / Privacy.sexy",
            description=f"Adds {len(TELEMETRY_DOMAINS)} telemetry/MSN ad endpoints to a clean, reversible block in Windows hosts file.",
            tags=["hosts", "telemetry", "privacy", "ads"],
            apply_actions=[
                HostsBlock(TELEMETRY_DOMAINS, enable=True),
                Cmd("ipconfig /flushdns"),
            ],
            revert_actions=[
                HostsBlock([], enable=False),
                Cmd("ipconfig /flushdns"),
            ],
        ),
        Tweak(
            id="priv_remove_bloat_appx",
            name="Remove Pre-installed Windows Bloatware Apps (Safe List)",
            category=CATEGORY_PRIVACY,
            risk=RiskLevel.MODERATE,
            source="Win11Debloat / CTT WinUtil",
            description="Removes Cortana, Clipchamp, Bing News/Weather, Solitaire, People, Feedback Hub, Maps, Copilot App, etc. Keeps Store & Terminal.",
            tags=["debloat", "appx", "uwp", "storage"],
            apply_actions=[
                AppxRemove([pkg for pkg, _ in SAFE_BLOAT_APPX]),
            ],
            revert_actions=[],
        ),
        Tweak(
            id="priv_disable_onedrive",
            name="Disable Microsoft OneDrive Auto-Start & Integration",
            category=CATEGORY_PRIVACY,
            risk=RiskLevel.MODERATE,
            source="Win11Debloat / HI+Optimizer V6",
            description="Stops OneDrive background sync process and disables OneDrive file sync policy (does not delete local files).",
            tags=["onedrive", "debloat", "ram"],
            apply_actions=[
                Cmd("taskkill /f /im OneDrive.exe"),
                RegSet("HKLM", r"SOFTWARE\Policies\Microsoft\Windows\OneDrive", "DisableFileSyncNGSC", 1),
                RegDelete("HKCU", r"Software\Microsoft\Windows\CurrentVersion\Run", "OneDrive"),
            ],
            revert_actions=[
                RegDelete("HKLM", r"SOFTWARE\Policies\Microsoft\Windows\OneDrive", "DisableFileSyncNGSC"),
            ],
        ),
    ]
