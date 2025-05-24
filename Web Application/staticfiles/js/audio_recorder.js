document.addEventListener('DOMContentLoaded', function() {
    const recordButton = document.getElementById('recordButton');
    const recordingStatus = document.getElementById('recordingStatus');
    const spectrogramImage = document.getElementById('spectrogramImage');
    const analysisResults = document.getElementById('analysisResults');

    recordButton.addEventListener('click', function() {
        // Disable button during recording
        recordButton.disabled = true;
        recordingStatus.innerHTML = '<div class="alert alert-info">Recording in progress...</div>';

        // Send request to start recording
        fetch('/record/', {
            method: 'POST'
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                recordingStatus.innerHTML = '<div class="alert alert-success">Recording completed!</div>';
                
                // Generate Spectrogram
                return fetch('/spectrogram/');
            } else {
                throw new Error(data.message);
            }
        })
        .then(response => response.json())
        .then(spectrogramData => {
            if (spectrogramData.status === 'success') {
                // Display spectrogram
                spectrogramImage.src = `/media/${spectrogramData.spectrogram_path}`;
                spectrogramImage.style.display = 'block';

                // Analyze Audio
                return fetch('/analyze/');
            } else {
                throw new Error(spectrogramData.message);
            }
        })
        .then(response => response.json())
        .then(analysisData => {
            if (analysisData.status === 'success') {
                // Display analysis results
                let resultsHTML = '<ul class="list-group">';
                for (const [key, value] of Object.entries(analysisData.analysis_results)) {
                    resultsHTML += `
                        <li class="list-group-item d-flex justify-content-between align-items-center">
                            ${key.replace('_', ' ')}
                            <span class="badge bg-primary rounded-pill">${(value * 100).toFixed(2)}%</span>
                        </li>
                    `;
                }
                resultsHTML += '</ul>';
                analysisResults.innerHTML = resultsHTML;
            } else {
                throw new Error(analysisData.message);
            }
        })
        .catch(error => {
            recordingStatus.innerHTML = `<div class="alert alert-danger">Error: ${error.message}</div>`;
        })
        .finally(() => {
            // Re-enable button
            recordButton.disabled = false;
        });
    });
});
