# 🚀 Quick Fix: Enable Microphone Recording (5 Minutes)

## The Problem
Your app can't record audio when launched normally because it's not code-signed, which prevents macOS from showing the microphone permission dialog.

## The Solution
Ad-hoc code signing (FREE, no Apple Developer account needed).

---

## Step-by-Step Instructions

### 1️⃣ Sign Your Existing App

```bash
cd /Users/nishaan/Documents/Development/FormFillerSoftware

# Sign the app in dist folder
./sign_app.sh dist/PhysioClinicAssistant.app
```

**What this does:**
- Removes quarantine attributes that block permissions
- Signs all libraries inside the app
- Adds entitlements for microphone access
- Makes the app trusted enough to show permission dialogs

**Expected output:**
```
🔐 Ad-hoc code signing: dist/PhysioClinicAssistant.app
1️⃣  Removing quarantine attributes...
2️⃣  Signing embedded libraries...
3️⃣  Signing main executable...
4️⃣  Signing app bundle...
5️⃣  Verifying signature...
✅ Ad-hoc signing complete!
```

---

### 2️⃣ Move App to Applications (Recommended)

```bash
# If the app is not already in Applications
cp -R dist/PhysioClinicAssistant.app /Applications/
```

---

### 3️⃣ Launch the App Properly (First Time Only)

**IMPORTANT:** On first launch, you MUST right-click → Open

1. Open Finder
2. Navigate to `/Applications`
3. Find `PhysioClinicAssistant.app`
4. **Right-click** (or Control-click) on the app
5. Select **"Open"** from the menu
6. Click **"Open"** in the security dialog

**Why this is needed:**
- macOS Gatekeeper blocks unsigned/ad-hoc signed apps on first launch
- Right-click → Open bypasses this one-time restriction
- After first successful launch, you can open normally

---

### 4️⃣ Test Recording

1. App should open successfully
2. Enter a patient name
3. Select your microphone from the dropdown
4. Click **"Start Recording"**
5. **THIS TIME** you should see: "PhysioClinicAssistant would like to access the microphone"
6. Click **"Allow"**
7. Speak clearly into the microphone
8. Click **"Stop Recording"**

---

### 5️⃣ Verify It Worked

```bash
# Check the recorded audio file
# It should be in: ~/Library/Application Support/PhysioClinicAssistant/data/
# Find today's date folder, then your appointment folder
# Play the audio file - you should hear your voice!

# Quick check:
ls -lh ~/Library/Application\ Support/PhysioClinicAssistant/data/*/*/recording.wav
```

**The audio file should:**
- Be more than a few KB in size (silence is tiny)
- Play back your voice when opened
- Generate a transcript with your actual words

---

## 🎯 Quick Verification

### Test 1: Is the app signed?
```bash
codesign --verify --verbose dist/PhysioClinicAssistant.app
# ✅ Should say: "valid on disk"
```

### Test 2: Does it have microphone entitlements?
```bash
codesign -d --entitlements :- dist/PhysioClinicAssistant.app | grep audio
# ✅ Should show: com.apple.security.device.audio-input
```

### Test 3: Check System Preferences
```bash
open "x-apple.systempreferences:com.apple.preference.security?Privacy_Microphone"
```
- ✅ Look for "PhysioClinicAssistant" in the list
- ✅ Make sure it's checked/enabled

---

## 🚨 Troubleshooting

### Problem: "Permission Denied" when running sign_app.sh
```bash
chmod +x sign_app.sh
./sign_app.sh dist/PhysioClinicAssistant.app
```

### Problem: App says "damaged and can't be opened"
```bash
xattr -cr dist/PhysioClinicAssistant.app
# Then try opening again with right-click → Open
```

### Problem: Still no permission dialog after signing
```bash
# Reset the permission system for your app
tccutil reset Microphone com.physioclinic.assistant

# Try recording again - dialog should appear
```

### Problem: App not in System Preferences → Microphone
1. Make sure you launched the app at least once
2. Make sure you clicked "Start Recording" at least once
3. Restart the app
4. Try recording again

---

## 🔄 Future Builds

For all future builds, use the updated build script:

```bash
# This now includes automatic ad-hoc signing
python3 build_mac.py
```

The updated `build_mac.py` will:
- ✅ Automatically do ad-hoc signing
- ✅ Include entitlements
- ✅ Remove quarantine attributes
- ✅ Create a properly signed DMG

---

## ✅ Success Checklist

- [ ] Ran `./sign_app.sh dist/PhysioClinicAssistant.app` successfully
- [ ] App opens when right-clicked → Open
- [ ] Microphone permission dialog appeared
- [ ] Clicked "Allow" on the permission dialog
- [ ] Recorded a test message
- [ ] Audio file contains actual speech (not silence)
- [ ] App appears in System Preferences → Microphone
- [ ] Transcript contains correct words

**Once all checked, your microphone recording is fixed!** 🎉

---

## 📞 Still Having Issues?

If recording still doesn't work after following these steps:
1. Check the detailed analysis in `MICROPHONE_PERMISSION_FIX.md`
2. Run the debugging commands in that file
3. Check Console.app for TCC permission errors
4. Make sure no other app is using the microphone

**The most common issue is forgetting to right-click → Open on first launch!**

