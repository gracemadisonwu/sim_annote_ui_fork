// Global variables
let currentVideo = null;
let currentSegments = [];
let currentSpeakers = [];
let currentFilter = 'all';

// Initialize the application
document.addEventListener('DOMContentLoaded', function() {
    loadSpeakers();
    setupEventListeners();
});

function setupEventListeners() {
    // Enter key in video path input
    document.getElementById('videoPath').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            loadVideo();
        }
    });

    // Enter key in new speaker input
    document.getElementById('newSpeaker').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            addSpeaker();
        }
    });
}

// Video loading functions
function loadVideo() {
    const videoPath = document.getElementById('videoPath').value.trim();
    if (!videoPath) {
        showStatus('Please enter a video file path', 'error');
        return;
    }

    showStatus('Loading video...', 'info');
    document.getElementById('loadBtn').disabled = true;

    // Send video path to backend
    fetch('/load_video', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ video_path: videoPath })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            currentVideo = data;
            document.getElementById('transcribeBtn').disabled = false;
            showStatus('Video loaded successfully!', 'success');
            displayVideo(data.video_url, data.filename);
        } else {
            showStatus('Error loading video: ' + data.error, 'error');
        }
        document.getElementById('loadBtn').disabled = false;
    })
    .catch(error => {
        showStatus('Error loading video: ' + error.message, 'error');
        document.getElementById('loadBtn').disabled = false;
    });
}

function displayVideo(videoUrl, filename) {
    const container = document.getElementById('videoContainer');
    container.innerHTML = `
        <div class="text-center">
            <video id="videoPlayer" controls class="w-100" style="max-height: 400px;">
                <source src="${videoUrl}" type="video/mp4">
                Your browser does not support the video tag.
            </video>
            <p class="mt-2 text-muted">${filename}</p>
        </div>
    `;
    
    // Show video controls and set up time update
    document.getElementById('videoControls').style.display = 'block';
    setupVideoTimeUpdate();
}

function seekToSegment(timeInSeconds) {
    const videoPlayer = document.getElementById('videoPlayer');
    if (videoPlayer) {
        videoPlayer.currentTime = timeInSeconds;
        videoPlayer.play();
    }
}

function setupVideoTimeUpdate() {
    const videoPlayer = document.getElementById('videoPlayer');
    if (videoPlayer) {
        videoPlayer.addEventListener('timeupdate', function() {
            const currentTime = document.getElementById('currentTime');
            if (currentTime) {
                currentTime.textContent = formatTime(videoPlayer.currentTime);
            }
        });
    }
}

function changePlaybackSpeed() {
    const videoPlayer = document.getElementById('videoPlayer');
    const speedSelect = document.getElementById('playbackSpeed');
    if (videoPlayer && speedSelect) {
        videoPlayer.playbackRate = parseFloat(speedSelect.value);
    }
}

function browseVideo() {
    // This would typically open a file dialog
    // For now, we'll just show a message
    showStatus('File browser not implemented in this demo. Please enter the path manually.', 'info');
}

// Transcription functions
function transcribeVideo() {
    if (!currentVideo) {
        showStatus('Please load a video first', 'error');
        return;
    }

    showProgressModal('Transcribing video with Whisper...', 'This may take several minutes depending on video length.');
    
    fetch('/whisper_transcribe', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({})
    })
    .then(response => response.json())
    .then(data => {
        hideProgressModal();
        if (data.success) {
            showStatus('Transcription completed successfully!', 'success');
            document.getElementById('speakerIdBtn').disabled = false;
            document.getElementById('exportBtn').disabled = false;
            loadSegments();
        } else {
            showStatus('Transcription failed: ' + data.error, 'error');
        }
    })
    .catch(error => {
        hideProgressModal();
        showStatus('Error during transcription: ' + error.message, 'error');
    });
}

// Speaker identification functions
function runSpeakerIdentification() {
    if (!currentVideo) {
        showStatus('Please load a video and transcribe first', 'error');
        return;
    }

    showProgressModal('Running speaker identification...', 'This process will analyze audio patterns to identify speakers.');
    
    fetch('/speaker_identification', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            denoise: true,
            denoise_prop: 0.1,
            verification_threshold: 0.2
        })
    })
    .then(response => response.json())
    .then(data => {
        hideProgressModal();
        if (data.success) {
            showStatus('Speaker identification completed!', 'success');
            loadSegments(); // Reload segments with speaker assignments
        } else {
            showStatus('Speaker identification failed: ' + data.error, 'error');
        }
    })
    .catch(error => {
        hideProgressModal();
        showStatus('Error during speaker identification: ' + error.message, 'error');
    });
}

// Segment management functions
function loadSegments() {
    // Load segments from the backend
    fetch('/get_segments')
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                showStatus('Error loading segments: ' + data.error, 'error');
                return;
            }
            currentSegments = data;
            renderSegments();
        })
        .catch(error => {
            showStatus('Error loading segments: ' + error.message, 'error');
            // Fallback to demo segments for testing
            loadDemoSegments();
        });
}

function loadDemoSegments() {
    // Demo segments for testing when backend is not available
    currentSegments = [
        {
            id: 0,
            start: 0.0,
            end: 2.04,
            text: " make sure that if we forget anything or...",
            speaker: ""
        },
        {
            id: 1,
            start: 2.04,
            end: 2.68,
            text: " Patient has arrived.",
            speaker: ""
        },
        {
            id: 2,
            start: 4.12,
            end: 4.72,
            text: " Patient's here.",
            speaker: ""
        },
        {
            id: 3,
            start: 6.38,
            end: 9.54,
            text: " Let's dry off and stimulate the patient if that hasn't been done.",
            speaker: ""
        }
    ];
    renderSegments();
}

function renderSegments() {
    const container = document.getElementById('segmentsContainer');
    
    if (currentSegments.length === 0) {
        container.innerHTML = `
            <div class="text-center text-muted py-5">
                <i class="fas fa-microphone fa-3x mb-3"></i>
                <p>No segments found</p>
            </div>
        `;
        return;
    }

    const filteredSegments = filterSegments(currentSegments, currentFilter);
    
    container.innerHTML = filteredSegments.map(segment => `
        <div class="segment-item ${segment.speaker ? 'labeled' : 'unlabeled'} fade-in">
            <div class="segment-header d-flex justify-content-between align-items-center">
                <span class="segment-time" style="cursor: pointer;" onclick="seekToSegment(${segment.start})" title="Click to seek to this time">
                    ${formatTime(segment.start)} - ${formatTime(segment.end)}
                </span>
                <button class="btn btn-sm btn-outline-primary" onclick="selectSpeaker(${segment.id})">
                    ${segment.speaker ? 'Change Speaker' : 'Assign Speaker'}
                </button>
            </div>
            <div class="segment-text">${segment.text}</div>
            <div class="segment-speaker">
                <span class="speaker-badge ${segment.speaker ? '' : 'unassigned'}">
                    ${segment.speaker || 'Unassigned'}
                </span>
            </div>
        </div>
    `).join('');
}

function filterSegments(segments, filter) {
    switch (filter) {
        case 'unlabeled':
            return segments.filter(s => !s.speaker);
        case 'labeled':
            return segments.filter(s => s.speaker);
        default:
            return segments;
    }
}

function showAllSegments() {
    currentFilter = 'all';
    renderSegments();
}

function showUnlabeledSegments() {
    currentFilter = 'unlabeled';
    renderSegments();
}

function showLabeledSegments() {
    currentFilter = 'labeled';
    renderSegments();
}

// Speaker management functions
function loadSpeakers() {
    // For demo purposes, we'll create some default speakers
    currentSpeakers = [
        { name: 'Doctor', description: 'Medical professional' },
        { name: 'Nurse', description: 'Nursing staff' },
        { name: 'Patient', description: 'Patient or family member' }
    ];
    
    renderSpeakerList();
}

function renderSpeakerList() {
    const container = document.getElementById('speakerList');
    container.innerHTML = currentSpeakers.map(speaker => `
        <div class="list-group-item d-flex justify-content-between align-items-center">
            <div>
                <strong>${speaker.name}</strong>
                <small class="text-muted d-block">${speaker.description}</small>
            </div>
            <button class="btn btn-sm btn-outline-danger" onclick="removeSpeaker('${speaker.name}')">
                <i class="fas fa-trash"></i>
            </button>
        </div>
    `).join('');
}

function addSpeaker() {
    const nameInput = document.getElementById('newSpeaker');
    const name = nameInput.value.trim();
    
    if (!name) {
        showStatus('Please enter a speaker name', 'error');
        return;
    }
    
    if (currentSpeakers.some(s => s.name === name)) {
        showStatus('Speaker already exists', 'error');
        return;
    }
    
    const newSpeaker = {
        name: name,
        description: `Custom speaker: ${name}`
    };
    
    currentSpeakers.push(newSpeaker);
    renderSpeakerList();
    nameInput.value = '';
    showStatus(`Speaker "${name}" added successfully`, 'success');
}

function removeSpeaker(name) {
    currentSpeakers = currentSpeakers.filter(s => s.name !== name);
    renderSpeakerList();
    showStatus(`Speaker "${name}" removed`, 'success');
}

function selectSpeaker(segmentId) {
    const segment = currentSegments.find(s => s.id === segmentId);
    if (!segment) return;
    
    const modal = document.getElementById('speakerModal');
    const optionsContainer = document.getElementById('speakerOptions');
    
    // Populate speaker options
    optionsContainer.innerHTML = currentSpeakers.map(speaker => `
        <div class="list-group-item" onclick="assignSpeaker(${segmentId}, '${speaker.name}')">
            <strong>${speaker.name}</strong>
            <small class="text-muted d-block">${speaker.description}</small>
        </div>
    `).join('');
    
    // Show modal
    const bsModal = new bootstrap.Modal(modal);
    bsModal.show();
}

function assignSpeaker(segmentId, speakerName) {
    const segment = currentSegments.find(s => s.id === segmentId);
    if (segment) {
        // Update locally first
        segment.speaker = speakerName;
        renderSegments();
        
        // Close modal
        const modal = document.getElementById('speakerModal');
        const bsModal = bootstrap.Modal.getInstance(modal);
        bsModal.hide();
        
        // Send update to backend
        fetch('/update_segment_speaker', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                segment_id: segmentId,
                speaker: speakerName
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showStatus(`Speaker "${speakerName}" assigned to segment`, 'success');
            } else {
                showStatus('Error updating speaker: ' + data.error, 'error');
            }
        })
        .catch(error => {
            showStatus('Error updating speaker: ' + error.message, 'error');
        });
    }
}

// Utility functions
function formatTime(seconds) {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
}

function showStatus(message, type) {
    const statusDiv = document.getElementById('status');
    statusDiv.textContent = message;
    statusDiv.className = `alert alert-${type === 'error' ? 'danger' : type}`;
    statusDiv.style.display = 'block';
    
    // Auto-hide after 5 seconds
    setTimeout(() => {
        statusDiv.style.display = 'none';
    }, 5000);
}

function showProgressModal(title, message) {
    document.getElementById('progressMessage').textContent = message;
    const modal = new bootstrap.Modal(document.getElementById('progressModal'));
    modal.show();
}

function hideProgressModal() {
    const modal = bootstrap.Modal.getInstance(document.getElementById('progressModal'));
    if (modal) {
        modal.hide();
    }
}

// Export functions
function exportLabels() {
    if (currentSegments.length === 0) {
        showStatus('No segments to export', 'error');
        return;
    }
    
    // Get export data from backend
    fetch('/export_labels')
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                showStatus('Error exporting labels: ' + data.error, 'error');
                return;
            }
            
            const dataStr = JSON.stringify(data, null, 2);
            const dataBlob = new Blob([dataStr], { type: 'application/json' });
            
            const link = document.createElement('a');
            link.href = URL.createObjectURL(dataBlob);
            link.download = 'speaker_labels.json';
            link.click();
            
            showStatus('Labels exported successfully', 'success');
        })
        .catch(error => {
            showStatus('Error exporting labels: ' + error.message, 'error');
        });
}
