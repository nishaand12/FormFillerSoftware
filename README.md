# Physiotherapy Clinic Assistant

A complete Python desktop application for physiotherapy clinics to record patient appointments, transcribe conversations, generate summaries, and automatically fill out medical forms with enterprise-grade security and audit capabilities.

## 💿 Download

**Ready-to-use macOS applications are available for download:**

- **Apple Silicon (M1/M2/M3/M4)**: [Download ARM version](https://github.com/nishaand12/FormFillerSoftware/releases/download/v1.0.0/PhysioClinicAssistant-2.0.0-macOS-ARM.dmg)
- **Intel x64**: [Download Intel version](https://github.com/nishaand12/FormFillerSoftware/releases/download/v1.0.0/PhysioClinicAssistant-2.0.0-macOS-Intel.dmg)

For full installation instructions and troubleshooting, see the [Installation section](#-installation) below.

## 🎯 Features

- **Audio Recording**: Record appointments with high-quality audio using PVRecorder
- **Offline Transcription**: Use Whisper AI for accurate speech-to-text conversion
- **Smart Summarization**: Generate physiotherapy-specific summaries using BART
- **Data Extraction**: Extract form-relevant data using Qwen3-4B-Instruct LLM for high accuracy
- **Form Filling**: Automatically fill WSIB FAF, OCF-18, and OCF-23 PDF forms
- **User Authentication**: Secure Supabase-based authentication with offline access
- **Data Encryption**: AES-256 encryption for all patient data
- **Audit Trail**: Complete audit logging for compliance and security
- **Background Processing**: Asynchronous processing for better performance
- **Appointment-Centric Storage**: Organized file structure by appointment date/time
- **Centralized Error Logging**: Remote error monitoring and local log viewer
- **Automatic Cleanup**: Intelligent cleanup of temporary files and old data

## 🖥️ System Requirements

- **OS**: macOS 10.15+ (Catalina or later)
  - Apple Silicon (M1/M2/M3/M4) - Recommended
  - Intel x64 - Supported
- **Python**: 3.8 or higher (for development builds)
- **RAM**: 8GB minimum, 16GB recommended
- **Storage**: 10GB free space + 4.3GB for AI models
- **Audio**: Microphone input capability (Bluetooth compatible)
- **Internet**: Required for initial setup and model download

## 🤖 AI Models Used

- **Whisper AI**: Speech-to-text transcription (small model)
- **BART**: Text summarization and analysis
- **Qwen3-4B-Instruct**: High-accuracy data extraction from transcripts (preferred)
- **Qwen3-1.7B**: Lightweight alternative for data extraction

## 📦 Installation

### For macOS Test Build Users

⚠️ **IMPORTANT: This is a test build (not yet Apple-signed)**

After downloading the DMG file, you may see a "damaged" error. Don't worry - the file is fine! Just follow these steps:

#### Quick Fix (Copy & Paste into Terminal)

Open Terminal (Applications → Utilities → Terminal) and paste:

```bash
xattr -cr ~/Downloads/PhysioClinicAssistant-*.dmg
```

Press Enter. Now open the DMG file normally!

#### Why This Happens

macOS blocks unsigned apps downloaded from the internet. The command above removes the security flag. This is safe - just make sure you trust the source! Production builds will be signed by Apple and won't need this.

#### Alternative: Right-Click Method

1. Right-click the DMG file
2. Click "Open"
3. Click "Open" again in the dialog

(If you still see "damaged", use the Terminal command instead)

#### Alternative: No Terminal Needed

To avoid this entirely, transfer the file via:
- AirDrop (Mac to Mac)
- USB drive
- Local network sharing

Files transferred these ways don't get the security flag!

---

### For Developers: Building from Source

### 1. Clone the Repository
```bash
git clone <repository-url>
cd Transcriber
```

### 2. Create Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Supabase (Optional)
```bash
# Edit config/supabase_config.json with your Supabase project details
# This enables user authentication and remote error logging
```

### 5. Download Models (First Run)
```bash
python model_downloader.py download
```

**Note**: Model download may take 15-30 minutes depending on your internet connection. The models will be cached locally for future use.

## 🚀 Usage

### Starting the Application
```bash
python main.py
```

### Workflow

1. **Authentication** (if Supabase configured)
   - Login with your clinic credentials
   - Application works offline after initial authentication

2. **Enter Patient Information**
   - Patient Name (required)
   - Appointment ID (auto-generated with timestamp)

3. **Start Recording**
   - Click "Start Recording" to begin audio capture
   - Timer shows recording duration
   - Recording automatically stops after 30 minutes

4. **Processing** (Background)
   - Audio is transcribed using Whisper AI
   - Summary is generated with physiotherapy focus
   - Data is extracted for form filling
   - PDF forms are automatically filled
   - All files are encrypted and stored in appointment-specific folders

5. **Results**
   - View transcript, summary, and filled forms
   - Forms are saved in `data/YYYY-MM-DD/HHMMSS/` directory structure
   - All data is encrypted for security

## 📁 File Structure

```
Transcriber/
├── main.py                        # Main application entry point
├── run_app.py                     # Application launcher
├── pvrecorder_recorder.py         # Audio recording component
├── transcriber.py                 # Speech-to-text transcription
├── summarizer.py                  # Text summarization
├── wsib_data_extractor.py         # WSIB data extraction
├── ocf18_data_extractor.py        # OCF-18 data extraction
├── ocf23_data_extractor.py        # OCF-23 data extraction
├── wsib_form_filler.py            # WSIB PDF form filling
├── ocf18_form_filler.py           # OCF-18 PDF form filling
├── ocf23_form_filler.py           # OCF-23 PDF form filling
├── model_downloader.py            # Model management
├── model_manager.py               # Model selection and management
├── background_processor.py        # Background processing
├── database_manager.py            # SQLite database management
├── encrypted_database_manager.py  # Encrypted database operations
├── encryption_manager.py          # AES-256 encryption
├── audit_manager.py               # Audit trail management
├── admin_log_viewer.py            # Administrative log viewer
├── remote_logger.py               # Remote error logging
├── requirements.txt               # Python dependencies
├── README.md                     # This file
├── config/
│   ├── supabase_config.json          # Supabase configuration
│   ├── field_map_wsib.json           # WSIB form field mappings
│   ├── field_map_ocf18.json          # OCF-18 form field mappings
│   ├── field_map_ocf23.json          # OCF-23 form field mappings
│   └── [various config files]        # Form-specific configurations
├── auth/                         # Authentication system
│   ├── auth_manager.py               # Supabase authentication
│   ├── session_manager.py            # Session management
│   ├── error_logger.py               # Security and error logging
│   └── [other auth components]       # Additional auth features
├── data/                         # Patient data (encrypted)
│   ├── YYYY-MM-DD/                   # Appointment date folders
│   │   └── HHMMSS/                   # Appointment time folders
│   │       ├── *.wav.enc             # Encrypted audio files
│   │       ├── *.txt.enc             # Encrypted transcripts
│   │       ├── *.json.enc            # Encrypted extractions
│   │       └── *.pdf                 # Filled forms
│   └── clinic_data.db                # SQLite database
├── logs/                         # Application logs
│   ├── auth.log                       # Authentication logs
│   ├── errors.log                     # Error logs
│   ├── security.log                   # Security logs
│   └── background_processor.log       # Background processing logs
├── models/                       # Downloaded AI models
├── forms/templates/              # PDF form templates
├── temp/                         # Temporary files
└── venv/                         # Virtual environment
```

## 🔧 Configuration

### Supabase Authentication (Optional)
Configure user authentication and remote error logging:
```json
{
  "supabase_url": "https://your-project.supabase.co",
  "supabase_anon_key": "your_anon_key",
  "supabase_service_key": "your_service_role_key"
}
```

### Field Mappings
The application uses JSON configuration files to map extracted data to PDF form fields:

- `config/field_map_wsib.json`: WSIB FAF form field mappings
- `config/field_map_ocf18.json`: OCF-18 form field mappings
- `config/field_map_ocf23.json`: OCF-23 form field mappings

### Model Settings
Models are automatically downloaded and cached locally:
- **Whisper**: `small` model with `int8` quantization
- **BART**: `sshleifer/distilbart-cnn-12-6` for summarization
- **Qwen3**: `Qwen3-4B-Instruct` for high-accuracy data extraction

## 🛠️ Troubleshooting

### Common Issues

1. **Audio Recording Fails**
   - Check microphone permissions
   - Ensure microphone is not in use by other applications
   - Try restarting the application

2. **Model Download Fails**
   - Check internet connection
   - Ensure sufficient disk space (10GB+)
   - Try running `python model_downloader.py download` manually

3. **Transcription Errors**
   - Ensure audio file is not corrupted
   - Check that audio is in WAV format
   - Verify Whisper model is downloaded

4. **Form Filling Issues**
   - Check PDF form templates exist in `forms/` directory
   - Verify field mappings in config files
   - Ensure extracted data contains required fields

### Performance Optimization

- **CPU Usage**: Models run on CPU by default for compatibility
- **Memory**: Close other applications to free up RAM
- **Storage**: Regularly clean up old recordings in `recordings/` directory

## 🔒 Privacy & Security

- **Local Processing**: All AI processing happens on your device
- **Data Encryption**: AES-256 encryption for all patient data
- **Secure Authentication**: Supabase-based user authentication with offline access
- **Audit Trail**: Complete audit logging for compliance and security
- **Encrypted Storage**: All files encrypted with unique keys per appointment
- **Background Processing**: Secure asynchronous processing with error handling
- **Centralized Logging**: Remote error monitoring with local log viewer
- **Data Retention**: Automatic cleanup of temporary files and old data

## 📋 Form Requirements

### WSIB FAF (Functional Abilities Form)
- Patient identification
- Injury details and mechanism
- Functional limitations assessment
- Work restrictions and return-to-work timeline
- Permanent impairment evaluation

### OCF-18 (Treatment and Assessment Plan)
- Patient and accident information
- Injury description and diagnosis
- Treatment plan and prognosis
- Functional limitations
- Return-to-work recommendations

### OCF-23 (Treatment Plan)
- Patient and accident information
- Injury description and diagnosis
- Treatment plan and prognosis
- Functional limitations
- Return-to-work recommendations

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For technical support or feature requests:
1. Check the troubleshooting section above
2. Review the error logs in the application
3. Create an issue in the repository
4. Contact the development team

## 🔄 Updates

The application will check for model updates on startup. To manually update models:
```bash
python model_downloader.py download
```

## 📊 System Monitoring

The application includes comprehensive monitoring:
- **Recording duration and quality** - Real-time audio monitoring
- **Processing time for each step** - Performance tracking
- **Error logging and recovery** - Automatic error handling
- **Audit trail** - Complete user activity logging
- **Background processing status** - Asynchronous task monitoring
- **Automatic cleanup** - Intelligent file management
- **Remote error reporting** - Centralized error monitoring
- **Local log viewer** - Administrative troubleshooting tools

## 🔧 Administrative Features

### Log Viewer
Access the administrative log viewer for troubleshooting:
```bash
python admin_log_viewer.py
```

### Remote Error Monitoring
Configure Supabase for centralized error tracking:
- System errors logged automatically
- User-specific errors tracked with user IDs
- Critical error alerts for administrators

### Database Management
- **SQLite database** for appointment tracking
- **Encrypted storage** for all patient data
- **Audit trail** for compliance requirements

---

**Note**: This application is designed for physiotherapy clinics and should be used in compliance with local healthcare regulations and privacy laws. All patient data is encrypted and stored securely with complete audit trails. 