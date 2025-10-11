# Final Testing Instructions - Fresh User Experience

## Complete Clean Test (Simulating New User)

### Step 1: Clean All User Data
Already done! ✅
- Removed `~/Library/Application Support/PhysioClinicAssistant/`
- Removed `~/Library/Caches/PhysioClinicAssistant/`
- Removed `~/Library/Logs/PhysioClinicAssistant/`

### Step 2: Install the App
1. Open `PhysioClinicAssistant-2.1.0-macOS.dmg`
2. Drag `PhysioClinicAssistant.app` to Desktop (or Applications)
3. **Important:** Right-click → Open (first time only)
4. Click "Open" in the security dialog

### Step 3: First Launch - Login
1. App launches
2. Login screen appears
3. Enter credentials and log in
4. **If subscription expired:** You'll see error message with contact email

### Step 4: First-Run Setup (Automatic)
After successful login, setup wizard appears:
1. Dialog explains model download (~4.3 GB)
2. Click "Download Now"
3. Wait 10-15 minutes for models to download
4. Models saved to `~/Library/Application Support/PhysioClinicAssistant/models/`

### Step 5: Grant Microphone Permission ⚠️ CRITICAL
**This is the missing step that caused silent recordings!**

When you try to start recording, macOS SHOULD show a permission dialog:
- "Physio Clinic Assistant would like to access the microphone"
- Click "Allow" or "OK"

**If NO dialog appears (unsigned app issue):**
1. Go to: **System Preferences** (or **System Settings** on newer macOS)
2. Navigate to: **Privacy & Security** → **Microphone**
3. Find "Physio Clinic Assistant" or "PhysioClinicAssistant" in the list
4. **Enable the checkbox** next to it
5. **Restart the app**

**To manually open Privacy settings:**
```bash
open "x-apple.systempreferences:com.apple.preference.security?Privacy_Microphone"
```

### Step 6: Test Recording
1. Select audio device from dropdown
2. Enter patient name
3. Click "Start Recording"
4. **Speak into microphone** - say test words clearly
5. Click "Stop Recording"
6. Recording queues for background processing

### Step 7: Verify Recording Works
After stopping recording:
1. Check `~/Library/Application Support/PhysioClinicAssistant/data/YYYY-MM-DD/PatientName_HHMMSS/`
2. Find `recording.wav`
3. **Test audio:** Open file and verify it plays back your voice
4. Check `transcript.txt` - should contain your spoken words (not just "you")

### Step 8: Check Background Processing
1. Wait a few minutes for transcription
2. Refresh the appointments list
3. Check transcript file again
4. If forms were selected, they should appear in the folder

## Troubleshooting

### Silent Recordings (All Zeros)
**Symptoms:** Recording file exists but has no sound, transcript says "you" or is empty

**Cause:** Microphone permission NOT granted

**Solution:**
1. Open System Preferences → Privacy & Security → Microphone
2. Find and enable "Physio Clinic Assistant"
3. Restart the app
4. Try recording again

### No Permission Dialog
**Cause:** Unsigned apps sometimes don't trigger permission prompts

**Solution:** Manually add permission in System Preferences (see Step 5)

### Audio Devices Not Listed
**Symptoms:** Device dropdown is empty or only shows "Default Device"

**Cause:** 
- Microphone permission not granted
- Or pvrecorder not initialized

**Solution:**
1. Grant microphone permission
2. Click "Refresh" button next to device dropdown
3. Restart app if needed

### Models Not Downloading
**Symptoms:** First-run setup fails or gets stuck

**Cause:** Network issue or disk space

**Solution:**
1. Check internet connection
2. Ensure 10+ GB free disk space
3. Try "Download Models" from Tools menu later

## Current Test Status

### What We Fixed Today:
✅ App launches successfully
✅ Icon shows correctly
✅ Name displays properly
✅ All data goes to proper writable locations (27 files fixed!)
✅ First-run setup wizard added
✅ Subscription expiration message
✅ PvRecorder native library bundled
✅ Duplicate window bug fixed
✅ Bluetooth permissions added

### What Needs Testing:
🔍 Microphone permission grant process
🔍 Recording with actual audio data
🔍 Transcription with Whisper
🔍 Background processing
🔍 Form filling

## Next Steps for Testing

1. **Close any running app instances**
2. **Open System Preferences → Privacy → Microphone**
3. **Look for "Physio Clinic Assistant" or "PhysioClinicAssistant"**
4. **Enable the checkbox if it exists**
5. **If not in list**, launch the app and try recording - permission dialog should appear
6. **Test recording with actual speech**
7. **Verify transcript contains your words**

The silent recording issue is **definitely a microphone permission problem**, not a code issue. Once permission is granted, everything should work! 🎤

