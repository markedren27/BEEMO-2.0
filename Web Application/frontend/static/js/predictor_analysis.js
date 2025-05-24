document.addEventListener('DOMContentLoaded', function() {
    // Predictor types
    const predictors = ['BNQ', 'QNQ', 'TOOT'];

    // Function to handle multi-recording
    function recordMultiSamples() {
        fetch('/multi-record/', { method: 'POST' })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    // Process recordings for each predictor
                    predictors.forEach(predictor => {
                        const recordingsContainer = document.getElementById(`${predictor.toLowerCase()}-recordings`);
                        const resultsContainer = document.getElementById(`${predictor.toLowerCase()}-results`);
                        
                        // Clear previous content
                        recordingsContainer.innerHTML = '';
                        resultsContainer.innerHTML = '';

                        // Display recordings
                        data.recordings[predictor].forEach((recording, index) => {
                            // Create recording entry
                            const recordingEntry = document.createElement('div');
                            recordingEntry.classList.add('recording-entry', 'mb-2');
                            recordingEntry.innerHTML = `
                                <strong>Recording ${index + 1}:</strong>
                                <audio controls>
                                    <source src="/${recording.audio_path}" type="audio/wav">
                                    Your browser does not support the audio element.
                                </audio>
                                <img src="/${recording.spectrogram_path}" alt="Spectrogram" class="img-fluid mt-2">
                            `;
                            recordingsContainer.appendChild(recordingEntry);
                        });

                        // Analyze recordings
                        analyzeRecordings(predictor, data.recordings[predictor]);
                    });
                } else {
                    console.error('Recording failed:', data.message);
                }
            })
            .catch(error => {
                console.error('Error:', error);
            });
    }

    // Function to analyze recordings
    function analyzeRecordings(predictor, recordings) {
        const resultsContainer = document.getElementById(`${predictor.toLowerCase()}-results`);
        
        // Prepare data for analysis
        const spectrogramPaths = recordings.map(r => r.spectrogram_path);

        // Send analysis request
        fetch('/analyze/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ spectrograms: spectrogramPaths })
        })
        .then(response => response.json())
        .then(analysisData => {
            // Display analysis results
            const analysisResults = document.createElement('div');
            analysisResults.innerHTML = `
                <h4>Analysis Summary</h4>
                <pre>${JSON.stringify(analysisData, null, 2)}</pre>
            `;
            resultsContainer.appendChild(analysisResults);
        })
        .catch(error => {
            console.error(`Analysis error for ${predictor}:`, error);
            resultsContainer.innerHTML = `<p class="text-danger">Analysis failed: ${error.message}</p>`;
        });
    }

    // Add event listeners to record buttons
    predictors.forEach(predictor => {
        const recordButton = document.getElementById(`record-${predictor.toLowerCase()}`);
        if (recordButton) {
            recordButton.addEventListener('click', recordMultiSamples);
        }
    });
});
