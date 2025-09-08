from flask import Flask, render_template, request, jsonify
import os
import json
import uuid
from datetime import datetime
from pathlib import Path

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['UPLOAD_FOLDER'] = 'uploads'

# Ensure upload directory exists for saving labels
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs('data', exist_ok=True)

# Global variables to store current session data
current_video = None
current_segments = []
current_speakers = []
current_file_processor = None
current_whisper_results = None

@app.route('/')
def index():
    """Main page with video transcription and labeling interface"""
    return render_template('index.html')

@app.route('/whisper_transcribe', methods=['POST'])
def whisper_transcribe():
    """Demo transcription function"""
    global current_video, current_whisper_results
    
    if not current_video:
        return jsonify({'error': 'No video loaded. Please load a video first.'}), 400
    
    # Create demo whisper results
    current_whisper_results = {
        "text": "Demo transcription text for testing purposes.",
        "segments": [
            {
                "id": 0,
                "start": 0.0,
                "end": 2.04,
                "text": " make sure that if we forget anything or...",
                "speaker": ""
            },
            {
                "id": 1,
                "start": 2.04,
                "end": 2.68,
                "text": " Patient has arrived.",
                "speaker": ""
            },
            {
                "id": 2,
                "start": 4.12,
                "end": 4.72,
                "text": " Patient's here.",
                "speaker": ""
            },
            {
                "id": 3,
                "start": 6.38,
                "end": 9.54,
                "text": " Let's dry off and stimulate the patient if that hasn't been done.",
                "speaker": ""
            },
            {
                "id": 4,
                "start": 13.18,
                "end": 15.32,
                "text": " Is there a timer on the warmer?",
                "speaker": ""
            },
            {
                "id": 5,
                "start": 18.76,
                "end": 21.78,
                "text": " Any response to the stimulation?",
                "speaker": ""
            }
        ]
    }
    
    return jsonify({'success': True, 'result': current_whisper_results})

@app.route('/speaker_identification', methods=['POST'])
def speaker_identification():
    """Demo speaker identification function"""
    global current_whisper_results
    
    if not current_whisper_results:
        return jsonify({'error': 'No transcription results available'}), 400
    
    # Demo: assign some speakers automatically
    if 'segments' in current_whisper_results:
        for i, segment in enumerate(current_whisper_results['segments']):
            if i % 3 == 0:
                segment['speaker'] = 'Doctor'
            elif i % 3 == 1:
                segment['speaker'] = 'Nurse'
            else:
                segment['speaker'] = 'Patient'
    
    return jsonify({
        'success': True, 
        'message': 'Speaker identification completed successfully', 
        'results': current_whisper_results
    })

@app.route('/get_segments')
def get_segments():
    """Get all current segments"""
    global current_whisper_results
    
    if not current_whisper_results:
        return jsonify({'error': 'No transcription results available'}), 400
    
    # Extract segments from whisper results
    segments = []
    if 'segments' in current_whisper_results:
        for segment in current_whisper_results['segments']:
            segments.append({
                'id': segment.get('id', 0),
                'start': segment.get('start', 0.0),
                'end': segment.get('end', 0.0),
                'text': segment.get('text', ''),
                'speaker': segment.get('speaker', '')
            })
    
    return jsonify(segments)

@app.route('/update_segment_speaker', methods=['POST'])
def update_segment_speaker():
    """Update the speaker for a segment"""
    data = request.get_json()
    segment_id = data.get('segment_id')
    speaker = data.get('speaker')

    if not segment_id or not speaker:
        return jsonify({'error': 'Missing segment_id or speaker'}), 400
    
    global current_whisper_results
    if not current_whisper_results:
        return jsonify({'error': 'No transcription results available'}), 400
    
    # Update the speaker for the segment
    if 'segments' in current_whisper_results:
        for segment in current_whisper_results['segments']:
            if segment.get('id') == segment_id:
                segment['speaker'] = speaker
                break
    
    return jsonify({'success': True, 'message': 'Speaker updated successfully'})

@app.route('/export_labels')
def export_labels():
    """Export labels in the required format for evaluation"""
    global current_whisper_results
    
    if not current_whisper_results or 'segments' not in current_whisper_results:
        return jsonify({'error': 'No segments to export'}), 400
    
    # Sort segments by start time
    sorted_segments = sorted(current_whisper_results['segments'], key=lambda x: x.get('start', 0))
    
    export_data = []
    for segment in sorted_segments:
        if segment.get('speaker'):  # Only export labeled segments
            export_data.append({
                'speaker': segment['speaker'],
                'start': segment['start'],
                'end': segment['end'],
                'text': segment.get('text', '')
            })
        else:
            export_data.append({
                'speaker': '',
                'start': segment['start'],
                'end': segment['end'],
                'text': segment.get('text', '')
            })
    
    return jsonify(export_data)

if __name__ == '__main__':
    print("Starting Video Transcription & Speaker Labeling Interface...")
    print("Open your browser and navigate to: http://localhost:5000")
    print("This is a demo version that simulates the transcription process.")
    print("Press Ctrl+C to stop the server.")
    app.run(debug=True, host='0.0.0.0', port=5000)
