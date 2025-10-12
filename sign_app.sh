#!/bin/bash
# Ad-hoc code signing script for macOS app
# This enables microphone permission dialogs without needing an Apple Developer account

set -e

APP_PATH="$1"

if [ -z "$APP_PATH" ]; then
    echo "Usage: $0 <path-to-app>"
    echo "Example: $0 dist/PhysioClinicAssistant.app"
    exit 1
fi

if [ ! -d "$APP_PATH" ]; then
    echo "Error: App not found at $APP_PATH"
    exit 1
fi

echo "🔐 Ad-hoc code signing: $APP_PATH"
echo "This will allow the app to request microphone permissions."
echo ""

# Remove quarantine attributes first
echo "1️⃣  Removing quarantine attributes..."
xattr -cr "$APP_PATH" || true

# Sign all dylibs and frameworks in the app bundle first
echo "2️⃣  Signing embedded libraries..."
find "$APP_PATH/Contents" -name "*.dylib" -o -name "*.so" | while read lib; do
    echo "   - Signing: $(basename "$lib")"
    codesign --force --deep --sign - \
        --entitlements entitlements.plist \
        --timestamp \
        --options runtime \
        "$lib" 2>/dev/null || true
done

# Sign frameworks
find "$APP_PATH/Contents/Frameworks" -name "*.framework" 2>/dev/null | while read framework; do
    echo "   - Signing framework: $(basename "$framework")"
    codesign --force --deep --sign - \
        --entitlements entitlements.plist \
        --timestamp \
        --options runtime \
        "$framework" 2>/dev/null || true
done

# Sign the main executable
echo "3️⃣  Signing main executable..."
EXECUTABLE="$APP_PATH/Contents/MacOS/$(basename "$APP_PATH" .app)"
if [ -f "$EXECUTABLE" ]; then
    codesign --force --sign - \
        --entitlements entitlements.plist \
        --timestamp \
        --options runtime \
        "$EXECUTABLE"
fi

# Sign the entire app bundle
echo "4️⃣  Signing app bundle..."
codesign --force --deep --sign - \
    --entitlements entitlements.plist \
    --timestamp \
    --options runtime \
    "$APP_PATH"

# Verify the signature
echo "5️⃣  Verifying signature..."
codesign --verify --verbose=4 "$APP_PATH"

echo ""
echo "✅ Ad-hoc signing complete!"
echo ""
echo "📋 Next steps:"
echo "   1. Move the app to /Applications (recommended)"
echo "   2. Right-click the app and select 'Open' (first time only)"
echo "   3. Click 'Open' in the security dialog"
echo "   4. When you start recording, allow microphone access"
echo ""
echo "🎤 The app will now be able to request microphone permissions!"

