// Multi-Channel Audio Interface JavaScript

// Global variables
let currentAudio = null;
let currentVideo = null;
let currentSegments = [];
let currentSpeakers = [];
let currentFilter = 'all';
let progressModalTimeout = null;
let audioChannels = [];
let selectedChannels = [];

// Initialize the application
document.addEventListener('DOMContentLoaded', function() {
    loadSpeakers();
    setupEventListeners();
});

function setupEventListeners() {
    // Enter key in audio path input
    document.getElementById('audioPath').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            loadAudio();
        }
    });

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

    // Range slider event listeners
    document.getElementById('denoiseProp').addEventListener('input', function(e) {
        document.getElementById('denoisePropValue').textContent = e.target.value;
    });

    document.getElementById('verificationThreshold').addEventListener('input', function(e) {
        document.getElementById('verificationThresholdValue').textContent = e.target.value;
    });
}

// Audio loading functions
function loadAudio() {
    const audioPath = document.getElementById('audioPath').value.trim();
    if (!audioPath) {
        showStatus('Please enter an audio file path', 'error');
        return;
    }

    showStatus('Loading audio...', 'info');
    document.getElementById('loadAudioBtn').disabled = true;

    // Send audio path to backend
    fetch('/load_audio', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ audio_path: audioPath })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            currentAudio = data;
            audioChannels = data.channels;
            document.getElementById('loadVideoBtn').disabled = false;
            document.getElementById('transcribeBtn').disabled = false;
            showStatus('Audio loaded successfully!', 'success');
            displayAudio(data.audio_url, data.filename);
            setupChannelControls(data.num_channels, data.channels);
        } else {
            showStatus('Error loading audio: ' + data.error, 'error');
        }
        document.getElementById('loadAudioBtn').disabled = false;
    })
    .catch(error => {
        showStatus('Error loading audio: ' + error.message, 'error');
        document.getElementById('loadAudioBtn').disabled = false;
    });
}

function loadVideo() {
    const videoPath = document.getElementById('videoPath').value.trim();
    if (!videoPath) {
        showStatus('Please enter a video file path', 'error');
        return;
    }

    showStatus('Loading video...', 'info');
    document.getElementById('loadVideoBtn').disabled = true;

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
            showStatus('Video loaded successfully!', 'success');
            displayVideo(data.video_url, data.filename);
        } else {
            showStatus('Error loading video: ' + data.error, 'error');
        }
        document.getElementById('loadVideoBtn').disabled = false;
    })
    .catch(error => {
        showStatus('Error loading video: ' + error.message, 'error');
        document.getElementById('loadVideoBtn').disabled = false;
    });
}

function displayAudio(audioUrl, filename) {
    const container = document.getElementById('audioContainer');
    container.innerHTML = `
        <div class="text-center">
            <audio id="audioPlayer" controls class="w-100">
                <source src="${audioUrl}" type="audio/wav">
                Your browser does not support the audio tag.
            </audio>
            <p class="mt-2 text-muted">${filename}</p>
            <div class="audio-visualization">
                <div class="audio-waveform"></div>
            </div>
        </div>
    `;
    
    // Show audio controls and set up time update
    document.getElementById('audioControls').style.display = 'block';
    setupAudioTimeUpdate();
}

function displayVideo(videoUrl, filename) {
    // Determine MIME type based on file extension
    const ext = filename.toLowerCase().split('.').pop();
    const mimeTypes = {
        'mp4': 'video/mp4',
        'mov': 'video/quicktime',
        'avi': 'video/x-msvideo',
        'wmv': 'video/x-ms-wmv',
        'webm': 'video/webm',
        'mkv': 'video/x-matroska'
    };
    const mimeType = mimeTypes[ext] || 'video/mp4';

    const container = document.getElementById('videoContainer');
    container.innerHTML = `
        <div class="text-center">
            <video id="videoPlayer" controls class="w-100" style="max-height: 400px;">
                <source src="${videoUrl}" type="${mimeType}">
                Your browser does not support the video tag.
            </video>
            <p class="mt-2 text-muted">${filename}</p>
        </div>
    `;

    // Show video player card
    document.getElementById('videoPlayerCard').style.display = 'block';
    setupVideoTimeUpdate();
}

function setupChannelControls(numChannels, channels) {
    const channelCheckboxes = document.getElementById('channelCheckboxes');
    const audioChannelControls = document.getElementById('audioChannelControls');
    
    // Show channel controls
    audioChannelControls.style.display = 'block';
    
    // Create channel checkboxes
    channelCheckboxes.innerHTML = '';
    for (let i = 0; i < numChannels; i++) {
        const checkboxDiv = document.createElement('div');
        checkboxDiv.className = 'form-check';
        checkboxDiv.innerHTML = `
            <input class="form-check-input" type="checkbox" value="${i}" id="channel${i}" onchange="updateSelectedChannels()">
            <label class="form-check-label" for="channel${i}">
                <span class="channel-indicator inactive" id="indicator${i}"></span>
                ${channels[i]}
            </label>
        `;
        channelCheckboxes.appendChild(checkboxDiv);
    }
    
    // Initialize with first two channels selected for stereo
    if (numChannels >= 2) {
        document.getElementById('channel0').checked = true;
        document.getElementById('channel1').checked = true;
        updateSelectedChannels();
    }
}

function updateSelectedChannels() {
    selectedChannels = [];
    const checkboxes = document.querySelectorAll('#channelCheckboxes input[type="checkbox"]:checked');
    
    checkboxes.forEach(checkbox => {
        selectedChannels.push(parseInt(checkbox.value));
        document.getElementById(`indicator${checkbox.value}`).className = 'channel-indicator active';
    });
    
    // Update inactive indicators
    const allCheckboxes = document.querySelectorAll('#channelCheckboxes input[type="checkbox"]');
    allCheckboxes.forEach(checkbox => {
        if (!checkbox.checked) {
            document.getElementById(`indicator${checkbox.value}`).className = 'channel-indicator inactive';
        }
    });
    
    // Update custom weights if needed
    updateMixControls();
}

function updateMixControls() {
    const mixType = document.getElementById('mixType').value;
    const customWeightsContainer = document.getElementById('customWeightsContainer');
    const customWeights = document.getElementById('customWeights');
    
    if (mixType === 'custom') {
        customWeightsContainer.style.display = 'block';
        
        // Create custom weight sliders
        customWeights.innerHTML = '';
        selectedChannels.forEach((channel, index) => {
            const sliderDiv = document.createElement('div');
            sliderDiv.className = 'custom-weight-slider';
            sliderDiv.innerHTML = `
                <label for="weight${channel}">Channel ${channel + 1} Weight:</label>
                <input type="range" class="form-range" id="weight${channel}" min="0" max="1" step="0.1" value="1" onchange="updateWeightValue(${channel})">
                <div class="custom-weight-value" id="weightValue${channel}">1.0</div>
            `;
            customWeights.appendChild(sliderDiv);
        });
    } else {
        customWeightsContainer.style.display = 'none';
    }
}

function updateWeightValue(channel) {
    const slider = document.getElementById(`weight${channel}`);
    const valueDisplay = document.getElementById(`weightValue${channel}`);
    valueDisplay.textContent = parseFloat(slider.value).toFixed(1);
}

function mixAudioChannels() {
    if (selectedChannels.length === 0) {
        showStatus('Please select at least one channel to mix', 'error');
        return;
    }

    const mixType = document.getElementById('mixType').value;
    let customWeights = [];
    
    if (mixType === 'custom') {
        selectedChannels.forEach(channel => {
            const weight = parseFloat(document.getElementById(`weight${channel}`).value);
            customWeights.push(weight);
        });
    }

    showProgressModal('Mixing audio channels...', 'Processing selected channels and creating mixed audio.');

    fetch('/mix_audio_channels', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            channels: selectedChannels,
            mix_type: mixType,
            custom_weights: customWeights
        })
    })
    .then(response => response.json())
    .then(data => {
        hideProgressModal();
        if (data.success) {
            showStatus(`Successfully mixed ${data.channels_used.length} channels using ${data.mix_type} method!`, 'success');
            // Update audio player with mixed audio
            const audioPlayer = document.getElementById('audioPlayer');
            if (audioPlayer) {
                audioPlayer.src = data.mixed_audio_url;
                audioPlayer.load();
            }
        } else {
            showStatus('Error mixing channels: ' + data.error, 'error');
        }
    })
    .catch(error => {
        hideProgressModal();
        showStatus('Error mixing channels: ' + error.message, 'error');
    });
}

function seekToSegment(timeInSeconds) {
    const audioPlayer = document.getElementById('audioPlayer');
    const videoPlayer = document.getElementById('videoPlayer');
    
    if (audioPlayer) {
        audioPlayer.currentTime = timeInSeconds;
        audioPlayer.play();
    }
    
    if (videoPlayer) {
        videoPlayer.currentTime = timeInSeconds;
        videoPlayer.play();
    }
}

function setupAudioTimeUpdate() {
    const audioPlayer = document.getElementById('audioPlayer');
    if (audioPlayer) {
        audioPlayer.addEventListener('timeupdate', function() {
            const currentTime = document.getElementById('currentTime');
            if (currentTime) {
                currentTime.textContent = formatTime(audioPlayer.currentTime);
            }
        });
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
    const audioPlayer = document.getElementById('audioPlayer');
    const videoPlayer = document.getElementById('videoPlayer');
    const speedSelect = document.getElementById('playbackSpeed');
    
    if (audioPlayer && speedSelect) {
        audioPlayer.playbackRate = parseFloat(speedSelect.value);
    }
    
    if (videoPlayer && speedSelect) {
        videoPlayer.playbackRate = parseFloat(speedSelect.value);
    }
}

function browseAudio() {
    showStatus('File browser not implemented in this demo. Please enter the path manually.', 'info');
}

function browseVideo() {
    showStatus('File browser not implemented in this demo. Please enter the path manually.', 'info');
}

// Segments file upload functions
function handleSegmentsFileSelect() {
    const fileInput = document.getElementById('segmentsFile');
    const uploadBtn = document.getElementById('uploadSegmentsBtn');
    
    if (fileInput.files && fileInput.files.length > 0) {
        const file = fileInput.files[0];
        if (file.type === 'application/json' || file.name.toLowerCase().endsWith('.json')) {
            uploadBtn.disabled = false;
            showStatus(`Selected file: ${file.name}`, 'info');
        } else {
            uploadBtn.disabled = true;
            showStatus('Please select a JSON file', 'error');
        }
    } else {
        uploadBtn.disabled = true;
    }
}

function uploadSegmentsFile() {
    const fileInput = document.getElementById('segmentsFile');
    const uploadBtn = document.getElementById('uploadSegmentsBtn');
    
    if (!fileInput.files || fileInput.files.length === 0) {
        showStatus('Please select a file first', 'error');
        return;
    }
    
    const file = fileInput.files[0];
    const formData = new FormData();
    formData.append('file', file);
    
    showProgressModal('Uploading segments file...', 'Processing and validating the uploaded segments.');
    uploadBtn.disabled = true;
    
    fetch('/upload_segments', {
        method: 'POST',
        body: formData
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        hideProgressModal();
        uploadBtn.disabled = false;
        
        if (data.success) {
            showStatus(`Successfully uploaded ${data.segments_count} segments!`, 'success');
            document.getElementById('exportBtn').disabled = false;
            loadSegments();
        } else {
            showStatus('Upload failed: ' + data.error, 'error');
        }
    })
    .catch(error => {
        console.error('Upload error:', error);
        hideProgressModal();
        uploadBtn.disabled = false;
        showStatus('Error uploading file: ' + error.message, 'error');
    })
    .finally(() => {
        hideProgressModal();
        uploadBtn.disabled = false;
    });
}

// Transcription functions
function transcribeAudio() {
    if (!currentAudio) {
        showStatus('Please load an audio file first', 'error');
        return;
    }

    showProgressModal('Transcribing audio with Whisper...', 'This may take several minutes depending on audio length.');
    
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
    if (!currentAudio) {
        showStatus('Please load an audio file and transcribe first', 'error');
        return;
    }

    showProgressModal('Running speaker identification...', 'This process will analyze audio patterns to identify speakers.');
    
    const denoise = document.getElementById('denoiseSwitch').checked;
    const denoiseProp = parseFloat(document.getElementById('denoiseProp').value);
    const verificationThreshold = parseFloat(document.getElementById('verificationThreshold').value);

    fetch('/speaker_identification', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            denoise: denoise,
            denoise_prop: denoiseProp,
            verification_threshold: verificationThreshold
        })
    })
    .then(response => response.json())
    .then(data => {
        hideProgressModal();
        if (data.success) {
            showStatus('Speaker identification completed!', 'success');
            loadSegments();
            console.log(data);
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
            loadDemoSegments();
        });
}

function loadDemoSegments() {
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
                <div class="btn-group" role="group">
                    <button class="btn btn-sm btn-outline-primary" onclick="selectSpeaker(${segment.id})">
                        ${segment.speaker ? 'Change Speaker' : 'Assign Speaker'}
                    </button>
                    <button class="btn btn-sm btn-outline-danger" onclick="deleteSegment(${segment.id})" title="Delete this segment">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
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
    currentSpeakers = [];
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
    
    optionsContainer.innerHTML = currentSpeakers.map(speaker => `
        <div class="list-group-item" onclick="assignSpeaker(${segmentId}, '${speaker.name}')">
            <strong>${speaker.name}</strong>
            <small class="text-muted d-block">${speaker.description}</small>
        </div>
    `).join('');
    
    const bsModal = new bootstrap.Modal(modal);
    bsModal.show();
}

function assignSpeaker(segmentId, speakerName) {
    const segment = currentSegments.find(s => s.id === segmentId);
    if (segment) {
        segment.speaker = speakerName;
        renderSegments();

        const modal = document.getElementById('speakerModal');
        const bsModal = bootstrap.Modal.getInstance(modal);
        bsModal.hide();

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

function deleteSegment(segmentId) {
    const segment = currentSegments.find(s => s.id === segmentId);
    if (!segment) return;

    // Confirm deletion
    if (!confirm(`Are you sure you want to delete this segment?\n\n"${segment.text}"\n\nThis action cannot be undone.`)) {
        return;
    }

    // Send delete request to backend
    fetch('/delete_segment', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            segment_id: segmentId
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showStatus('Segment deleted successfully', 'success');
            // Reload segments from backend to get updated IDs
            loadSegments();
        } else {
            showStatus('Error deleting segment: ' + data.error, 'error');
        }
    })
    .catch(error => {
        showStatus('Error deleting segment: ' + error.message, 'error');
    });
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
    
    setTimeout(() => {
        statusDiv.style.display = 'none';
    }, 5000);
}

function showProgressModal(title, message) {
    document.getElementById('progressMessage').textContent = message;
    const modalElement = document.getElementById('progressModal');

    if (progressModalTimeout) {
        clearTimeout(progressModalTimeout);
        progressModalTimeout = null;
    }

    const existingModal = bootstrap.Modal.getInstance(modalElement);
    if (existingModal) {
        existingModal.hide();
    }

    const modal = new bootstrap.Modal(modalElement, {
        backdrop: 'static',
        keyboard: false
    });
    modal.show();

    // Set a timeout to automatically hide the modal after 5 minutes as a safety measure
    progressModalTimeout = setTimeout(() => {
        console.warn('Progress modal timeout - forcing hide');
        hideProgressModal();
    }, 300000); // 5 minutes
}

function hideProgressModal() {
    if (progressModalTimeout) {
        clearTimeout(progressModalTimeout);
        progressModalTimeout = null;
    }

    const modalElement = document.getElementById('progressModal');
    const modal = bootstrap.Modal.getInstance(modalElement);
    if (modal) {
        modal.hide();
    } else {
        const newModal = new bootstrap.Modal(modalElement);
        newModal.hide();
    }
}

// Export functions
function exportLabels() {
    if (currentSegments.length === 0) {
        showStatus('No segments to export', 'error');
        return;
    }
    
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
