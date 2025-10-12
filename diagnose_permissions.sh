#!/bin/bash
# Diagnose microphone permission issues for PhysioClinicAssistant
# Run this to check what's preventing microphone access

set -e

APP_PATH="${1:-dist/PhysioClinicAssistant.app}"
BUNDLE_ID="com.physioclinic.assistant"

echo "🔍 PhysioClinicAssistant - Microphone Permission Diagnostics"
echo "==========================================================="
echo ""
echo "Checking: $APP_PATH"
echo ""

# Function to print check results
print_check() {
    local status=$1
    local message=$2
    if [ "$status" == "ok" ]; then
        echo "✅ $message"
    elif [ "$status" == "warning" ]; then
        echo "⚠️  $message"
    else
        echo "❌ $message"
    fi
}

# Check 1: Does app exist?
echo "📁 App Existence Check"
echo "-----------------------------------------------------------"
if [ -d "$APP_PATH" ]; then
    print_check "ok" "App found at: $APP_PATH"
    APP_SIZE=$(du -sh "$APP_PATH" | cut -f1)
    echo "   Size: $APP_SIZE"
else
    print_check "error" "App not found at: $APP_PATH"
    echo ""
    echo "💡 Solution: Build the app first with: python3 build_mac.py"
    exit 1
fi
echo ""

# Check 2: Code signing status
echo "🔐 Code Signing Check"
echo "-----------------------------------------------------------"
if codesign --verify --verbose "$APP_PATH" 2>&1 | grep -q "valid on disk"; then
    print_check "ok" "App is code-signed"
    SIGNING_INFO=$(codesign -dvvv "$APP_PATH" 2>&1 | grep "Authority" | head -1)
    echo "   $SIGNING_INFO"
    
    # Check if ad-hoc signed
    if codesign -dvvv "$APP_PATH" 2>&1 | grep -q "Signature=adhoc"; then
        print_check "warning" "Using ad-hoc signature (self-signed)"
        echo "   This is OK for testing but not for distribution"
    fi
else
    print_check "error" "App is NOT code-signed"
    echo ""
    echo "💡 Solution: Run ./sign_app.sh $APP_PATH"
fi
echo ""

# Check 3: Entitlements
echo "🎫 Entitlements Check"
echo "-----------------------------------------------------------"
ENTITLEMENTS=$(codesign -d --entitlements :- "$APP_PATH" 2>/dev/null)
if echo "$ENTITLEMENTS" | grep -q "com.apple.security.device.audio-input"; then
    print_check "ok" "Microphone entitlement present"
else
    print_check "error" "Microphone entitlement MISSING"
    echo ""
    echo "💡 Solution: Run ./sign_app.sh $APP_PATH"
fi

if echo "$ENTITLEMENTS" | grep -q "com.apple.security.cs.disable-library-validation"; then
    print_check "ok" "Library validation disabled (needed for Python)"
else
    print_check "warning" "Library validation entitlement missing"
fi
echo ""

# Check 4: Quarantine attributes
echo "🚧 Quarantine Attribute Check"
echo "-----------------------------------------------------------"
XATTR=$(xattr "$APP_PATH" 2>/dev/null)
if echo "$XATTR" | grep -q "com.apple.quarantine"; then
    print_check "error" "Quarantine attribute present (blocks permissions)"
    echo ""
    echo "💡 Solution: Run: xattr -cr $APP_PATH"
elif [ -z "$XATTR" ]; then
    print_check "ok" "No quarantine attributes"
else
    print_check "ok" "Quarantine attributes cleared"
    echo "   Remaining attributes: $XATTR"
fi
echo ""

# Check 5: Info.plist permissions
echo "📋 Info.plist Check"
echo "-----------------------------------------------------------"
PLIST_PATH="$APP_PATH/Contents/Info.plist"
if [ -f "$PLIST_PATH" ]; then
    print_check "ok" "Info.plist found"
    
    if plutil -p "$PLIST_PATH" | grep -q "NSMicrophoneUsageDescription"; then
        print_check "ok" "NSMicrophoneUsageDescription present"
        DESCRIPTION=$(plutil -p "$PLIST_PATH" | grep "NSMicrophoneUsageDescription" | cut -d'"' -f4)
        echo "   Message: \"$DESCRIPTION\""
    else
        print_check "error" "NSMicrophoneUsageDescription MISSING"
    fi
    
    BUNDLE_ID_ACTUAL=$(plutil -p "$PLIST_PATH" | grep "CFBundleIdentifier" | cut -d'"' -f4)
    if [ "$BUNDLE_ID_ACTUAL" == "$BUNDLE_ID" ]; then
        print_check "ok" "Bundle identifier matches: $BUNDLE_ID"
    else
        print_check "warning" "Bundle identifier: $BUNDLE_ID_ACTUAL (expected: $BUNDLE_ID)"
    fi
else
    print_check "error" "Info.plist not found"
fi
echo ""

# Check 6: System permissions database
echo "🔒 System Permissions Check"
echo "-----------------------------------------------------------"
# Check if app has been granted microphone permission
# This requires checking TCC database which needs special permissions
if sudo -n true 2>/dev/null; then
    # Can use sudo without password
    TCC_CHECK=$(sudo sqlite3 /Library/Application\ Support/com.apple.TCC/TCC.db \
        "SELECT service, client, allowed FROM access WHERE service='kTCCServiceMicrophone' AND client LIKE '%$BUNDLE_ID%';" 2>/dev/null || echo "")
    
    if [ -n "$TCC_CHECK" ]; then
        print_check "ok" "App registered in TCC database"
        echo "   $TCC_CHECK"
    else
        print_check "warning" "App not yet in TCC database (permission not requested yet)"
        echo "   This is normal if you haven't launched the app yet"
    fi
else
    print_check "warning" "Cannot check TCC database (needs sudo)"
    echo "   Run 'sudo $0' to check system permission database"
fi
echo ""

# Check 7: Executable permissions
echo "⚡ Executable Permissions Check"
echo "-----------------------------------------------------------"
EXECUTABLE="$APP_PATH/Contents/MacOS/PhysioClinicAssistant"
if [ -f "$EXECUTABLE" ]; then
    if [ -x "$EXECUTABLE" ]; then
        print_check "ok" "Main executable has execute permission"
        PERMS=$(ls -l "$EXECUTABLE" | cut -d' ' -f1)
        echo "   Permissions: $PERMS"
    else
        print_check "error" "Main executable is NOT executable"
        echo ""
        echo "💡 Solution: Run: chmod +x $EXECUTABLE"
    fi
else
    print_check "error" "Main executable not found at: $EXECUTABLE"
fi
echo ""

# Check 8: pvrecorder library
echo "📚 Audio Library Check"
echo "-----------------------------------------------------------"
PVRECORDER_LIB=$(find "$APP_PATH" -name "*pvrecorder*" -o -name "*pv_recorder*" 2>/dev/null | head -1)
if [ -n "$PVRECORDER_LIB" ]; then
    print_check "ok" "pvrecorder library found"
    echo "   Location: $(basename "$PVRECORDER_LIB")"
else
    print_check "warning" "pvrecorder library not found (might be embedded differently)"
fi
echo ""

# Summary and recommendations
echo "📊 Summary & Recommendations"
echo "==========================================================="
echo ""

# Count issues
ERRORS=$(grep -c "❌" /tmp/diagnose_output.txt 2>/dev/null || echo "0")
WARNINGS=$(grep -c "⚠️" /tmp/diagnose_output.txt 2>/dev/null || echo "0")

if codesign --verify "$APP_PATH" 2>&1 | grep -q "valid on disk"; then
    if plutil -p "$PLIST_PATH" | grep -q "NSMicrophoneUsageDescription"; then
        echo "✅ App appears to be properly configured for microphone access!"
        echo ""
        echo "📝 Next steps:"
        echo "   1. Move app to /Applications (optional but recommended)"
        echo "   2. Right-click the app → Open (first time only)"
        echo "   3. Click 'Open' in security dialog"
        echo "   4. Launch the app and start recording"
        echo "   5. Allow microphone access when prompted"
        echo ""
        echo "If you don't see the permission dialog:"
        echo "   • Open System Preferences → Privacy & Security → Microphone"
        echo "   • Look for 'PhysioClinicAssistant' or add it manually"
        echo "   • Enable the checkbox"
        echo "   • Restart the app"
    else
        echo "⚠️  App is signed but missing NSMicrophoneUsageDescription"
        echo ""
        echo "💡 Solution: Rebuild with: python3 build_mac.py"
    fi
else
    echo "❌ App is NOT properly signed"
    echo ""
    echo "💡 Solution: Run this command:"
    echo "   ./sign_app.sh $APP_PATH"
    echo ""
    echo "Then test:"
    echo "   1. Right-click app → Open"
    echo "   2. Start recording"
    echo "   3. Allow microphone permission"
fi

echo ""
echo "📖 For detailed troubleshooting, see: MICROPHONE_PERMISSION_FIX.md"
echo ""

