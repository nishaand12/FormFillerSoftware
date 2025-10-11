# PhysioClinicAssistant - Installation Instructions

## ⚠️ Important: macOS Security Notice

This is a **test/beta build** that is not yet signed with an Apple Developer Certificate. When you download it, macOS may show a misleading error message saying the file is "damaged" - **it's not actually damaged**, this is just macOS's way of blocking unsigned apps downloaded from the internet.

## Quick Installation (2 Steps)

### Step 1: Remove the Security Flag

After downloading, open **Terminal** and paste this command:

```bash
xattr -cr ~/Downloads/PhysioClinicAssistant-*.dmg
```

Press Enter. This removes the security flag that macOS added when you downloaded the file.

### Step 2: Install Normally

Now double-click the DMG file and follow the installer!

---

## Alternative: Automated Helper Script

Download the `remove_quarantine.sh` script, then:

1. Open Terminal
2. Run: `bash ~/Downloads/remove_quarantine.sh`
3. Follow the prompts

---

## Alternative: Manual Right-Click Method

1. **Right-click** (or Control+click) the downloaded DMG file
2. Select **"Open"**
3. Click **"Open"** in the warning dialog
4. If you still see "damaged", use the Terminal command above instead

---

## Why This Happens

- macOS Gatekeeper protects users by checking if apps are signed by Apple-verified developers
- This test build doesn't have Apple's signature yet (requires paid developer account)
- macOS adds a "quarantine" flag to downloaded files and blocks unsigned apps
- The Terminal command simply removes this flag

**For production release:** The app will be properly signed and notarized, and none of this will be necessary!

---

## Other Distribution Options

To avoid this issue entirely, you can:

- ✅ **AirDrop** the file to other Macs (no quarantine flag added)
- ✅ **USB drive** - Copy to USB and install from there (no quarantine flag)
- ✅ **Local network sharing** - Share via macOS file sharing (no quarantine flag)

Files transferred these ways don't get the quarantine flag, so they'll open normally!

---

## Full Installation Process

1. Download `PhysioClinicAssistant-X.X.X-macOS.dmg`
2. Remove quarantine flag (use command above)
3. Double-click DMG file
4. Double-click installer app inside
5. Follow installation wizard
6. App will be placed on Desktop
7. Drag to Applications folder
8. Launch from Applications

On first launch, the app will:
- Check system requirements
- Download AI models (~4.3GB)
- Configure audio devices
- Set up database

---

## System Requirements

- macOS 10.15+ (Catalina or later)
- 8GB RAM minimum (16GB recommended)
- 10GB free disk space (plus 4.3GB for AI models)
- Microphone access
- Internet connection (for initial setup)

---

## Troubleshooting

### "Operation not permitted" when running xattr command
Make sure the file is actually in your Downloads folder, or use the full path to the file.

### Still getting "damaged" error after removing quarantine
Try removing quarantine from the installer app too:
```bash
xattr -cr /Volumes/PhysioClinicAssistant*/PhysioClinicAssistant-Installer.app
```

### Installer won't open
Right-click the installer → Open (instead of double-clicking)

---

## Security Note

⚠️ **Only install software from sources you trust!** These methods bypass macOS security checks. This build is provided for testing purposes only.

---

## Questions or Issues?

Please report any installation issues in the GitHub Issues tab or contact ceteasystems@gmail.com.

---

## For Future Production Release

The production version will be:
- ✅ Signed with Apple Developer Certificate
- ✅ Notarized by Apple
- ✅ No security workarounds needed
- ✅ Opens normally when downloaded

