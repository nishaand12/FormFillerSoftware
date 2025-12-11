#!/bin/bash

# ==============================================================================
# CONFIGURATION
# ==============================================================================
APP_NAME="PhysioClinicAssistant"
APP_PATH="./dist/${APP_NAME}.app"
DMG_NAME="${APP_NAME}_Installer.dmg"
ENTITLEMENTS_FILE="entitlements.plist"

# Your Signing Identity (Copied from your previous output)
SIGNING_IDENTITY="Developer ID Application: CETEA Consulting Inc. (RHF4H2NNW7)"

# Your NotaryTool Credentials Profile Name
# (The name you used with 'xcrun notarytool store-credentials')
NOTARY_PROFILE="AC_PASSWORD" 

# ==============================================================================
# 0. PRE-FLIGHT CHECKS
# ==============================================================================
set -e # Exit immediately if a command exits with a non-zero status

echo "🚀 Starting Distribution Pipeline for $APP_NAME..."

if [ ! -d "$APP_PATH" ]; then
    echo "❌ Error: App not found at $APP_PATH. Please build your app first."
    exit 1
fi

# Clean up previous artifacts
rm -f "$DMG_NAME"
rm -f "$ENTITLEMENTS_FILE"

# ==============================================================================
# 1. GENERATE ENTITLEMENTS (Including Microphone & Hardened Runtime)
# ==============================================================================
echo "📜 Creating Entitlements file..."

cat <<EOF > "$ENTITLEMENTS_FILE"
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <!-- Essential: Disable library validation for Python and ML libraries -->
    <key>com.apple.security.cs.disable-library-validation</key>
    <true/>
    
    <!-- Essential: Allow unsigned executable memory (required for Python C extensions) -->
    <key>com.apple.security.cs.allow-unsigned-executable-memory</key>
    <true/>
    
    <!-- Essential: Allow JIT compilation (required for ML/AI libraries) -->
    <key>com.apple.security.cs.allow-jit</key>
    <true/>

    <!-- Essential: Allow dyld environment variables (required for Python) -->
    <key>com.apple.security.cs.allow-dyld-environment-variables</key>
    <true/>
    
    <!-- Hardened Runtime: Disable debugger attachment -->
    <key>com.apple.security.cs.debugger</key>
    <false/>
    
    <!-- Application Features: Network access (Supabase, model downloads) -->
    <key>com.apple.security.network.client</key>
    <true/>
    
    <!-- Application Features: File access (save forms/appointments) -->
    <key>com.apple.security.files.user-selected.read-write</key>
    <true/>
    
    <!-- Application Features: Microphone access (audio recording) -->
    <key>com.apple.security.device.audio-input</key>
    <true/>
</dict>
</plist>
EOF

# ==============================================================================
# 2. CODE SIGN THE APPLICATION
# ==============================================================================
echo "🔏 Signing Application with Hardened Runtime..."

# --force: Overwrite existing signatures
# --deep: Recursively sign nested binaries (needed for PyInstaller bundles)
# --options runtime: Enable Hardened Runtime (Required for Notarization)
# --entitlements: Apply the permissions created above
codesign --force --deep --options runtime --timestamp \
    --entitlements "$ENTITLEMENTS_FILE" \
    --sign "$SIGNING_IDENTITY" \
    "$APP_PATH"

echo "✅ App Signed successfully."

# ==============================================================================
# 3. CREATE DMG
# ==============================================================================
echo "📦 Packaging into DMG..."

# Create a temporary DMG
hdiutil create -volname "$APP_NAME Installer" \
    -srcfolder "$APP_PATH" \
    -ov -format UDZO \
    "$DMG_NAME"

echo "✅ DMG Created: $DMG_NAME"

# ==============================================================================
# 4. SIGN THE DMG
# ==============================================================================
echo "🔏 Signing the DMG file..."

codesign --force --timestamp \
    --sign "$SIGNING_IDENTITY" \
    "$DMG_NAME"

# ==============================================================================
# 5. NOTARIZE
# ==============================================================================
echo "uploading to Apple for Notarization (This may take a few minutes)..."

xcrun notarytool submit "$DMG_NAME" \
    --keychain-profile "$NOTARY_PROFILE" \
    --wait

echo "✅ Notarization Accepted."

# ==============================================================================
# 6. STAPLE
# ==============================================================================
echo "stapling the ticket to the DMG..."

xcrun stapler staple "$DMG_NAME"

echo "✅ Stapling Complete."

# ==============================================================================
# 7. FINAL VERIFICATION
# ==============================================================================
echo "🔍 Verifying Gatekeeper status..."

spctl -a -t open --context context:primary-signature -v "$DMG_NAME"

echo "🎉 SUCCESS! $DMG_NAME is ready for distribution."