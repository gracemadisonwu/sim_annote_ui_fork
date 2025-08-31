# Video Transcription & Speaker Labeling Interface

A web-based interface for transcribing videos using Whisper and labeling speakers in the transcription segments.

## Features

- **Video Upload**: Load videos by providing the full file path
- **Whisper Transcription**: Automatic speech-to-text transcription using OpenAI's Whisper
- **Speaker Labeling**: Manually assign speakers to transcription segments
- **Speaker Identification**: Automated speaker identification using audio analysis
- **Export**: Export labeled segments in JSON format
- **Responsive Interface**: Modern, mobile-friendly web interface

## Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd inspire_revamp
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Ensure data directories exist**:
   ```bash
   mkdir -p data uploads
   ```

## Usage

1. **Start the application**:
   ```bash
   python app.py
   ```

2. **Open your browser** and navigate to `http://localhost:5000`

3. **Load a video**:
   - Enter the full path to your video file
   - Click "Load Video"

4. **Transcribe with Whisper**:
   - Click "Transcribe with Whisper"
   - Wait for the transcription to complete

5. **Label speakers**:
   - Click "Assign Speaker" on any segment
   - Select a speaker from the list or add new speakers
   - Continue labeling segments as needed

6. **Run speaker identification** (optional):
   - After labeling some segments, click "Run Speaker Identification"
   - This will attempt to automatically assign speakers to remaining segments

7. **Export labels**:
   - Click "Export Labels" to download the labeled segments as JSON

## File Structure

```
inspire_revamp/
├── app.py                      # Flask application
├── whisper_transcribe.py       # Whisper transcription module
├── speaker_identification.py   # Speaker identification module
├── templates/
│   └── index.html             # Main HTML template
├── static/
│   ├── css/
│   │   └── style.css          # Custom styles
│   └── js/
│       └── app.js             # Frontend JavaScript
├── data/                       # Data storage directory
├── uploads/                    # Upload directory
├── requirements.txt            # Python dependencies
└── README.md                   # This file
```

## API Endpoints

- `GET /` - Main interface
- `POST /whisper_transcribe` - Transcribe video with Whisper
- `POST /speaker_identification` - Run speaker identification
- `GET /get_segments` - Get transcription segments
- `POST /update_segment_speaker` - Update speaker for a segment
- `GET /export_labels` - Export labeled segments

## Configuration

The application uses the following default settings:
- **Port**: 5000
- **Host**: 0.0.0.0 (accessible from any network)
- **Upload folder**: `uploads/`
- **Data folder**: `data/`

## Dependencies

- **Flask**: Web framework
- **OpenAI Whisper**: Speech recognition
- **PyTorch/TorchAudio**: Audio processing
- **MoviePy**: Video processing
- **scikit-learn**: Machine learning utilities
- **librosa**: Audio analysis

## Troubleshooting

1. **Import errors**: Ensure all dependencies are installed with `pip install -r requirements.txt`

2. **Video loading issues**: Verify the video file path is correct and accessible

3. **Transcription failures**: Check that the video file is in a supported format (MP4, AVI, MOV, etc.)

4. **Memory issues**: Large video files may require significant RAM for processing

## License

This project is provided as-is for educational and research purposes.

## Contributing

Feel free to submit issues, feature requests, or pull requests to improve the application.
