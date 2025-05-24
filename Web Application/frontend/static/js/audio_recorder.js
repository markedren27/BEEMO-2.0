document.addEventListener('DOMContentLoaded', function() {
    // Get all necessary DOM elements once, at script initialization
    const recordButton = document.getElementById('recordButton');
    const recordDuration = document.getElementById('recordDuration');
    const audioDeviceSelect = document.getElementById('audioDeviceSelect');
    const recordingStatus = document.getElementById('recordingStatus');

    // Validate that all critical elements exist
    const criticalElements = [
        { name: 'recordButton', element: recordButton },
        { name: 'recordDuration', element: recordDuration },
        { name: 'audioDeviceSelect', element: audioDeviceSelect },
        { name: 'recordingStatus', element: recordingStatus }
    ];

    const missingElements = criticalElements.filter(item => !item.element);
    if (missingElements.length > 0) {
        console.error('Missing critical DOM elements:', 
            missingElements.map(item => item.name).join(', ')
        );
        return;
    }

    // Predictors configuration
    const predictors = ['BNQ', 'QNQ', 'TOOT'];

    // Validate spectrogram elements before any processing
    function validateSpectrogramElements() {
        const missingSpectrogramElements = [];
        
        predictors.forEach(predictor => {
            const imgElement = document.getElementById(`spectrogramImage-${predictor}-1`);
            const debugElement = document.getElementById(`spectrogramDebug-${predictor}-1`);
            const analysisContainer = document.getElementById(`analysisResults-${predictor}`);

            if (!imgElement) missingSpectrogramElements.push(`spectrogramImage-${predictor}-1`);
            if (!debugElement) missingSpectrogramElements.push(`spectrogramDebug-${predictor}-1`);
            if (!analysisContainer) missingSpectrogramElements.push(`analysisResults-${predictor}`);
        });

        return missingSpectrogramElements;
    }

    // Audio device selection
    const spectrogramContainers = {
        'BNQ': document.getElementById('spectrogramContainer-BNQ'),
        'QNQ': document.getElementById('spectrogramContainer-QNQ'),
        'TOOT': document.getElementById('spectrogramContainer-TOOT')
    };

    const spectrogramImages = {
        'BNQ': [
            document.getElementById('spectrogramImage-BNQ-1'),
            document.getElementById('spectrogramImage-BNQ-2'),
            document.getElementById('spectrogramImage-BNQ-3')
        ],
        'QNQ': [
            document.getElementById('spectrogramImage-QNQ-1'),
            document.getElementById('spectrogramImage-QNQ-2'),
            document.getElementById('spectrogramImage-QNQ-3')
        ],
        'TOOT': [
            document.getElementById('spectrogramImage-TOOT-1'),
            document.getElementById('spectrogramImage-TOOT-2'),
            document.getElementById('spectrogramImage-TOOT-3')
        ]
    };

    const analysisResultsContainers = {
        'BNQ': document.getElementById('analysisResults-BNQ'),
        'QNQ': document.getElementById('analysisResults-QNQ'),
        'TOOT': document.getElementById('analysisResults-TOOT')
    };

    // Utility function to get CSRF token from cookies
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                // Does this cookie string begin with the name we want?
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    // Utility function to check if CSRF token exists
    function csrfSafeMethod(method) {
        // these HTTP methods do not require CSRF protection
        return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
    }

    // Setup AJAX to include CSRF token for Django
    $.ajaxSetup({
        beforeSend: function(xhr, settings) {
            if (!csrfSafeMethod(settings.type) && !this.crossDomain) {
                xhr.setRequestHeader("X-CSRFToken", getCookie('csrftoken'));
            }
        }
    });

    // Fetch audio devices on page load
    function fetchAudioDevices() {
        const audioDevicesUrl = '/devices/';
        
        // Log the full URL being fetched for debugging
        console.log('Fetching audio devices from:', window.location.origin + audioDevicesUrl);

        fetch(audioDevicesUrl)
            .then(response => {
                // Log the full response for debugging
                console.log('Response status:', response.status);
                console.log('Response headers:', Object.fromEntries(response.headers.entries()));

                // Check if the response is OK (status in the range 200-299)
                if (!response.ok) {
                    // If not OK, throw an error with status and statusText
                    throw new Error(`HTTP error! status: ${response.status}, message: ${response.statusText}`);
                }
                return response.json();
            })
            .then(data => {
                // Handle successful device listing
                const audioDeviceSelect = document.getElementById('audioDeviceSelect');
                const recordingStatus = document.getElementById('recordingStatus');

                // Create a detailed system info display
                const createSystemInfoDisplay = (systemInfo) => {
                    if (!systemInfo) return '';
                    return `
                        <div class="system-info">
                            <h5>System Diagnostics</h5>
                            <ul>
                                <li><strong>Python Version:</strong> ${systemInfo.python_version}</li>
                                <li><strong>Platform:</strong> ${systemInfo.platform}</li>
                                <li><strong>Machine:</strong> ${systemInfo.machine}</li>
                                <li><strong>Processor:</strong> ${systemInfo.processor}</li>
                                <li><strong>System:</strong> ${systemInfo.system}</li>
                                <li><strong>Release:</strong> ${systemInfo.release}</li>
                                <li><strong>RDP Session:</strong> ${systemInfo.is_rdp_session ? 'Yes' : 'No'}</li>
                            </ul>
                        </div>
                    `;
                };

                // Create a device list display
                const createDeviceListDisplay = (devices, title) => {
                    return '';
                };

                // Handle different response scenarios
                switch(data.status) {
                    case 'success':
                        // Physical input devices found
                        audioDeviceSelect.innerHTML = ''; // Clear existing options
                        
                        data.devices.forEach(device => {
                            const option = document.createElement('option');
                            option.value = device.index;
                            option.textContent = `${device.name} (${device.max_input_channels} channels)`;
                            option.title = `Sample Rate: ${device.default_samplerate}, Host API: ${device.hostapi}`;
                            if (device.is_default_input) {
                                option.selected = true;
                            }
                            audioDeviceSelect.appendChild(option);
                        });

                        recordingStatus.innerHTML = '';
                        break;

                    case 'warning':
                        // RDP virtual devices or only system audio interfaces
                        audioDeviceSelect.innerHTML = ''; // Clear existing options
                        const option = document.createElement('option');
                        
                        if (data.rdp_virtual_devices && data.rdp_virtual_devices.length > 0) {
                            // RDP virtual devices detected
                            option.textContent = 'RDP Virtual Audio Devices';
                            option.disabled = true;
                            
                            recordingStatus.innerHTML = '';
                        } else {
                            // Only system audio interfaces
                            option.textContent = 'No physical input devices';
                            option.disabled = true;
                            
                            recordingStatus.innerHTML = '';
                        }
                        
                        audioDeviceSelect.appendChild(option);
                        break;

                    case 'error':
                        // No input devices at all
                        audioDeviceSelect.innerHTML = ''; // Clear existing options
                        const errorOption = document.createElement('option');
                        errorOption.textContent = 'No audio devices';
                        errorOption.disabled = true;
                        audioDeviceSelect.appendChild(errorOption);
                        
                        recordingStatus.innerHTML = '';
                        break;

                    default:
                        throw new Error('Unexpected server response');
                }

                // Additional RDP warning if detected
                if (data.system_info && data.system_info.is_rdp_session) {
                    const rdpWarningElement = document.createElement('div');
                    rdpWarningElement.className = 'alert alert-info';
                    rdpWarningElement.innerHTML = `
                        <strong>RDP Session Detected</strong>
                        <br>
                        Audio device detection may be limited due to Remote Desktop connection.
                        Physical audio devices might be redirected or unavailable.
                    `;
                    recordingStatus.appendChild(rdpWarningElement);
                }
            })
            .catch(error => {
                console.error('Audio devices fetch error:', error);
                
                const audioDeviceSelect = document.getElementById('audioDeviceSelect');
                const recordingStatus = document.getElementById('recordingStatus');
                
                audioDeviceSelect.innerHTML = ''; // Clear existing options
                const option = document.createElement('option');
                option.textContent = 'Error loading devices';
                option.disabled = true;
                audioDeviceSelect.appendChild(option);
                
                // Detailed error messaging
                recordingStatus.innerHTML = `
                    <div class="alert alert-danger">
                        <strong>Error fetching audio devices:</strong> 
                        ${error.message}
                        <br>
                        Please check your audio setup and browser permissions.
                        <br>
                        <small>Debug Info: Attempted to fetch from /devices/</small>
                    </div>
                `;
            });
    }

    // Debugging function to log all spectrogram image elements
    function logSpectrogramElements() {
        const predictors = ['BNQ', 'QNQ', 'TOOT'];
        console.log('Spectrogram Image Elements:');
        predictors.forEach(predictor => {
            console.log(`${predictor} Images:`);
            spectrogramImages[predictor].forEach((img, index) => {
                console.log(`  Image ${index}:`, {
                    element: img,
                    src: img.src,
                    display: img.style.display,
                    naturalWidth: img.naturalWidth,
                    naturalHeight: img.naturalHeight
                });
            });
        });
    }

    // Diagnostic function to log all element details
    function logElementDetails() {
        const predictors = ['BNQ', 'QNQ', 'TOOT'];
        console.log('--- ELEMENT DIAGNOSTIC ---');
        predictors.forEach(predictor => {
            const imgElement = document.getElementById(`spectrogramImage-${predictor}-1`);
            const debugElement = document.getElementById(`spectrogramDebug-${predictor}-1`);
            const analysisContainer = document.getElementById(`analysisResults-${predictor}`);
            
            console.log(`Predictor: ${predictor}`, {
                imgElement: {
                    exists: !!imgElement,
                    id: imgElement ? imgElement.id : 'NOT FOUND',
                    parentElement: imgElement ? imgElement.parentElement : 'NOT FOUND'
                },
                debugElement: {
                    exists: !!debugElement,
                    id: debugElement ? debugElement.id : 'NOT FOUND'
                },
                analysisContainer: {
                    exists: !!analysisContainer,
                    id: analysisContainer ? analysisContainer.id : 'NOT FOUND'
                }
            });
        });
    }

    // Comprehensive diagnostic function
    function logAllElementsInDocument() {
        console.log('--- COMPLETE DOCUMENT ELEMENT DIAGNOSTIC ---');
        
        // Log all elements with IDs matching our patterns
        const patterns = [
            /spectrogramImage-[A-Z]+-\d+/,
            /spectrogramDebug-[A-Z]+-\d+/,
            /analysisResults-[A-Z]+/
        ];

        patterns.forEach(pattern => {
            const matchingElements = Array.from(document.querySelectorAll('*'))
                .filter(el => el.id && pattern.test(el.id));
            
            console.log(`Elements matching ${pattern}:`, 
                matchingElements.map(el => ({
                    id: el.id,
                    tagName: el.tagName,
                    parentId: el.parentElement ? el.parentElement.id : 'NO PARENT'
                }))
            );
        });
    }

    function recordAudioForPredictors() {
        // First, validate spectrogram elements
        const missingElements = validateSpectrogramElements();
        if (missingElements.length > 0) {
            console.error('Missing spectrogram elements:', missingElements);
            recordingStatus.innerHTML = '';
            return;
        }

        // Detailed logging of ALL elements
        console.log('--- FULL ELEMENT DIAGNOSTIC ---');
        const predictors = ['BNQ', 'QNQ', 'TOOT'];
        predictors.forEach(predictor => {
            const imgElement = document.getElementById(`spectrogramImage-${predictor}-1`);
            const debugElement = document.getElementById(`spectrogramDebug-${predictor}-1`);
            const analysisContainer = document.getElementById(`analysisResults-${predictor}`);

            console.log(`Predictor: ${predictor}`, {
                imgElement: {
                    exists: !!imgElement,
                    id: imgElement ? imgElement.id : 'NULL',
                    parentId: imgElement && imgElement.parentElement ? imgElement.parentElement.id : 'NO PARENT'
                },
                debugElement: {
                    exists: !!debugElement,
                    id: debugElement ? debugElement.id : 'NULL'
                },
                analysisContainer: {
                    exists: !!analysisContainer,
                    id: analysisContainer ? analysisContainer.id : 'NULL'
                }
            });
        });

        // Get recording duration and selected device
        const duration = parseFloat(recordDuration.value);
        const deviceIndex = parseInt(audioDeviceSelect.value);

        // Validate inputs
        if (isNaN(duration) || duration <= 0) {
            recordingStatus.innerHTML = '';
            return;
        }

        // Defensive programming: use safe element access
        const safeGetElement = (id) => {
            const element = document.getElementById(id);
            if (!element) {
                console.error(`CRITICAL: Element with ID ${id} not found!`);
                throw new Error(`Missing element: ${id}`);
            }
            return element;
        };

        try {
            // Reset previous spectrograms and results
            predictors.forEach(predictor => {
                const imgElement = safeGetElement(`spectrogramImage-${predictor}-1`);
                const debugElement = safeGetElement(`spectrogramDebug-${predictor}-1`);
                const analysisContainer = safeGetElement(`analysisResults-${predictor}`);
                
                // Clear previous state
                imgElement.src = ''; 
                imgElement.style.display = 'none';
                debugElement.innerHTML = 'Waiting for spectrogram...';
                analysisContainer.innerHTML = '';
            });
        } catch (error) {
            console.error('Fatal error during element preparation:', error);
            recordingStatus.innerHTML = '';
            return;
        }

        // Update UI to show recording in progress
        recordingStatus.innerHTML = '';
        recordButton.disabled = true;

        // Fetch multi-record endpoint
        fetch('/audio_analyzer/multi-record/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ 
                duration: duration, 
                device_index: deviceIndex 
            })
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}, message: ${response.statusText}`);
            }
            return response.json();
        })
        .then(data => {
            // Extensive logging of response data
            console.log('Full response data:', JSON.stringify(data, null, 2));

            // Check if the response contains the expected data
            if (data.status === 'success') {
                // Log spectrogram URLs for debugging
                console.log('Spectrogram URLs:', JSON.stringify(data.spectrograms, null, 2));

                // Update spectrograms for each predictor
                predictors.forEach(predictor => {
                    // Get the first (and only) spectrogram path
                    const spectrogramPath = data.spectrograms[predictor][0];
                    
                    // Get the image and debug elements with additional error checking
                    const imgElement = document.getElementById(`spectrogramImage-${predictor}-1`);
                    const debugElement = document.getElementById(`spectrogramDebug-${predictor}-1`);
                    const analysisContainer = document.getElementById(`analysisResults-${predictor}`);

                    // Comprehensive null checks
                    if (!imgElement || !debugElement) {
                        console.error(`Missing elements for predictor: ${predictor}`);
                        return;
                    }
                    
                    // Detailed logging before setting image
                    console.log(`Attempting to set ${predictor} image:`, {
                        path: spectrogramPath,
                        element: imgElement,
                        parentElement: imgElement.parentElement
                    });

                    // Update debug info
                    debugElement.innerHTML = `Attempting to load: ${spectrogramPath}`;

                    // Set source and make visible with error handling
                    imgElement.onload = function() {
                        console.log(`Successfully loaded ${predictor} image`);
                        imgElement.style.display = 'block';
                        imgElement.style.maxWidth = '100%';
                        imgElement.style.height = 'auto';
                        debugElement.innerHTML = `Loaded successfully: ${spectrogramPath}`;
                    };
                    
                    imgElement.onerror = function() {
                        console.error(`Failed to load ${predictor} image:`, {
                            src: spectrogramPath,
                            element: imgElement
                        });
                        imgElement.style.display = 'none';
                        debugElement.innerHTML = `Failed to load image: ${spectrogramPath}`;
                    };

                    // Actually set the source
                    // Ensure the path starts with a forward slash
                    imgElement.src = spectrogramPath.startsWith('/') ? spectrogramPath : `/${spectrogramPath}`;

                    // Update analysis results if available
                    if (analysisContainer && data.analysis_results) {
                        console.log('Full Analysis Results:', JSON.stringify(data.analysis_results, null, 2));
                        
                        // Predictors to process
                        const predictors = ['BNQ', 'QNQ', 'TOOT'];
                        
                        predictors.forEach(predictor => {
                            try {
                                // Check if results exist for this predictor
                                let results = data.analysis_results[predictor];
                                
                                console.log(`Processing ${predictor} Results:`, JSON.stringify(results, null, 2));
                                
                                // Validate results object
                                if (!results) {
                                    console.warn(`No results found for ${predictor}`);
                                    return;
                                }
                                
                                // Extract confidence using helper function
                                const confidence = extractConfidence(results);
                                
                                // Prepare analysis HTML
                                let analysisHtml = `<h4>Analysis Results for ${predictor}</h4>`;
                                
                                // Detailed analysis display
                                analysisHtml += `
                                    <div class="analysis-details">
                                        <div class="row">
                                            <div class="col-md-6">
                                                <h5>Prediction Details</h5>
                                                <table class="table table-bordered">
                                                    <tr>
                                                        <th>Prediction</th>
                                                        <td>${results.label || 'Unknown'}</td>
                                                    </tr>
                                                    <tr>
                                                        <th>Confidence</th>
                                                        <td>${formatConfidence(confidence)}</td>
                                                    </tr>
                                                </table>
                                            </div>
                                            <div class="col-md-6">
                                                <h5>Recommended Actions</h5>
                                                <div class="alert ${getAlertClass(predictor, results)}">
                                                    ${getRecommendedAction(predictor, results)}
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                `;
                                
                                // Find the specific analysis container for this predictor
                                const specificAnalysisContainer = document.getElementById(`analysisResults-${predictor}`);
                                if (specificAnalysisContainer) {
                                    specificAnalysisContainer.innerHTML = analysisHtml;
                                } else {
                                    console.warn(`No container found for ${predictor} analysis results`);
                                }
                            } catch (error) {
                                console.error(`Error processing ${predictor} results:`, error);
                            }
                        });
                    } else {
                        console.warn('No analysis results found in response', data);
                    }
                });

                // Update recording status
                recordingStatus.innerHTML = '';
            } else {
                // Handle server-side error
                throw new Error(data.message || 'Failed to record and analyze audio');
            }
        })
        .catch(error => {
            console.error('Error recording audio:', error);
            
            // Update UI with error message
            recordingStatus.innerHTML = '';
        })
        .finally(() => {
            // Re-enable record button
            recordButton.disabled = false;
        });
    }

    // Model Retraining Function
    function retrainModel(modelType, trueLabel, spectrogramPath) {
        // Validate inputs with more comprehensive checks
        if (!modelType || trueLabel === undefined) {
            console.error('Invalid retraining parameters');
            alert('Invalid retraining parameters. Please select a model and label.');
            return;
        }

        // Validate modelType
        const validModelTypes = ['bnq', 'qnq', 'toot'];
        if (!validModelTypes.includes(modelType.toLowerCase())) {
            console.error(`Invalid model type: ${modelType}. Must be one of: ${validModelTypes.join(', ')}`);
            alert(`Invalid model type: ${modelType}. Must be one of: ${validModelTypes.join(', ')}`);
            return;
        }

        // Validate trueLabel
        if (trueLabel !== 0 && trueLabel !== 1) {
            console.error(`Invalid true label: ${trueLabel}. Must be 0 or 1.`);
            alert('Invalid true label. Must be 0 or 1.');
            return;
        }

        // Dynamically find the most recent spectrogram for the given model type
        function findMostRecentSpectrogram(modelType) {
            // Map model types to their respective image IDs
            const spectrogramMap = {
                'bnq': 'spectrogramImage-BNQ-1',
                'qnq': 'spectrogramImage-QNQ-1',
                'toot': 'spectrogramImage-TOOT-1'
            };

            const imageId = spectrogramMap[modelType.toLowerCase()];
            if (!imageId) {
                console.warn(`No spectrogram found for model type: ${modelType}`);
                return null;
            }

            const imageElement = document.getElementById(imageId);
            return imageElement ? imageElement.src : null;
        }

        // Prepare request payload
        const payload = {
            model_type: modelType.toLowerCase(),
            true_label: trueLabel
        };

        // Use provided spectrogram path or dynamically find one
        const dynamicSpectrogramPath = spectrogramPath || findMostRecentSpectrogram(modelType);
        
        // Only add spectrogram_path if it's provided and not empty
        if (dynamicSpectrogramPath && dynamicSpectrogramPath.trim() !== '') {
            payload.spectrogram_path = dynamicSpectrogramPath.trim();
        }

        // Debug logging
        console.group('Model Retraining Request');
        console.log('Model Type:', payload.model_type);
        console.log('True Label:', payload.true_label);
        console.log('Spectrogram Path:', payload.spectrogram_path || 'Not provided');
        console.log('Full URL:', `${window.location.origin}/audio_analyzer/retrain-model/`);
        console.groupEnd();

        // Send retraining request
        $.ajax({
            url: `${window.location.origin}/audio_analyzer/retrain-model/`,
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify(payload),
            beforeSend: function(xhr) {
                // Manually set CSRF token
                xhr.setRequestHeader('X-CSRFToken', getCookie('csrftoken'));
            },
            success: function(data) {
                console.group('Model Retraining Response');
                console.log('Status:', data.status);
                console.log('Message:', data.message);
                console.log('Details:', data.details);
                console.groupEnd();

                if (data.status === 'success') {
                    console.log(`${modelType.toUpperCase()} model retrained successfully`);
                    alert(`${modelType.toUpperCase()} model retrained successfully`);
                } else {
                    console.error(`Model retraining failed: ${data.message}`);
                    // Display details if available
                    const errorDetails = data.details ? 
                        `\n\nDetails: ${JSON.stringify(data.details)}` : '';
                    alert(`Model retraining failed: ${data.message}${errorDetails}`);
                }
            },
            error: function(xhr, status, error) {
                console.group('Model Retraining Error');
                console.error('Status:', status);
                console.error('Error:', error);
                console.error('Response Text:', xhr.responseText);
                console.error('Response Status:', xhr.status);
                console.error('Response Headers:', xhr.getAllResponseHeaders());
                console.groupEnd();
                
                let errorMessage = 'Failed to retrain model.';
                try {
                    const responseJson = JSON.parse(xhr.responseText);
                    errorMessage += ` ${responseJson.message || ''}`;
                    
                    // Add details if available
                    if (responseJson.details) {
                        errorMessage += `\n\nDetails: ${JSON.stringify(responseJson.details)}`;
                    }
                } catch (e) {
                    errorMessage += ` Server returned status ${xhr.status}.`;
                }
                
                alert(errorMessage);
            }
        });
    }

    // Manual Model Retraining Interaction
    function showModelRetrainingModal(predictor, spectrogramPath, currentPrediction, currentConfidence) {
        // Create a button to trigger retraining modal
        const retrainingButtonHtml = `
            <button id="openRetrainingModalBtn" class="btn btn-warning" data-toggle="modal" data-target="#modelRetrainingModal">
                Retrain Model
            </button>
        `;

        // Create modal HTML
        const modalHtml = `
            <div id="modelRetrainingModal" class="modal fade" tabindex="-1" role="dialog">
                <div class="modal-dialog" role="document">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">Model Retraining</h5>
                            <button type="button" class="close" data-dismiss="modal" aria-label="Close">
                                <span aria-hidden="true">&times;</span>
                            </button>
                        </div>
                        <div class="modal-body">
                            <p>Current Prediction for ${predictor}: ${currentPrediction}</p>
                            <p>Confidence: ${currentConfidence}%</p>
                            <div class="form-group">
                                <label>Select the true label:</label>
                                <div class="btn-group btn-group-toggle" data-toggle="buttons">
                                    <label class="btn btn-outline-primary">
                                        <input type="radio" name="trueLabel" value="0" autocomplete="off"> False
                                    </label>
                                    <label class="btn btn-outline-primary">
                                        <input type="radio" name="trueLabel" value="1" autocomplete="off"> True
                                    </label>
                                </div>
                            </div>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-dismiss="modal">Cancel</button>
                            <button type="button" id="submitRetrainingBtn" class="btn btn-primary" disabled>Retrain Model</button>
                        </div>
                    </div>
                </div>
            </div>
        `;

        // Append modal to body
        $('body').append(modalHtml);
        const $modal = $('#modelRetrainingModal');
        const $submitBtn = $('#submitRetrainingBtn');

        // Enable submit button only when a label is selected
        $('input[name="trueLabel"]').on('change', function() {
            $submitBtn.prop('disabled', false);
        });

        // Submit retraining
        $submitBtn.on('click', function() {
            const trueLabel = parseInt($('input[name="trueLabel"]:checked').val());
            
            // Validate true label
            if (isNaN(trueLabel)) {
                alert('Please select a true label');
                return;
            }

            // Call retraining function
            retrainModel(
                predictor.toLowerCase(), 
                trueLabel, 
                spectrogramPath
            );

            // Close modal
            $modal.modal('hide');
        });

        // Clean up modal after closing
        $modal.on('hidden.bs.modal', function () {
            $(this).remove();
        });

        // Return the retraining button HTML for insertion
        return retrainingButtonHtml;
    }

    // Method to add retraining option to prediction results
    function addRetrainingOption(predictor, spectrogramPath, currentPrediction, currentConfidence) {
        console.group('Add Retraining Option Debug');
        console.log('Predictor:', predictor);
        console.log('Spectrogram Path:', spectrogramPath);
        console.log('Current Prediction:', currentPrediction);
        console.log('Current Confidence:', currentConfidence);

        // Validate inputs
        if (!predictor || !spectrogramPath) {
            console.error('Invalid inputs for retraining option');
            console.groupEnd();
            return;
        }

        // Create a container for the retraining button
        const $retrainingContainer = $('<div class="retraining-container"></div>');
        
        // Generate retraining modal button
        const retrainingButtonHtml = `
            <div class="card mb-3 border-warning">
                <div class="card-body bg-light">
                    <h5 class="card-title text-warning">${predictor} Model Retraining</h5>
                    <p class="card-text">
                        <strong>Current Prediction:</strong> ${currentPrediction}<br>
                        <strong>Confidence:</strong> ${currentConfidence}%
                    </p>
                    <button class="btn btn-outline-warning" data-toggle="modal" data-target="#${predictor}RetrainingModal">
                        Retrain ${predictor} Model
                    </button>
                </div>
            </div>

            <!-- Retraining Modal for ${predictor} -->
            <div class="modal fade" id="${predictor}RetrainingModal" tabindex="-1" role="dialog">
                <div class="modal-dialog" role="document">
                    <div class="modal-content">
                        <div class="modal-header bg-warning">
                            <h5 class="modal-title">${predictor} Model Retraining</h5>
                            <button type="button" class="close" data-dismiss="modal" aria-label="Close">
                                <span aria-hidden="true">&times;</span>
                            </button>
                        </div>
                        <div class="modal-body">
                            <div class="alert alert-info">
                                <strong>Current Prediction:</strong> ${currentPrediction}<br>
                                <strong>Confidence:</strong> ${currentConfidence}%
                            </div>
                            <div class="form-group">
                                <label class="d-block">Select the true label:</label>
                                <div class="btn-group btn-group-toggle w-100" data-toggle="buttons">
                                    <label class="btn btn-outline-primary w-50">
                                        <input type="radio" name="${predictor}TrueLabel" value="0" autocomplete="off"> False
                                    </label>
                                    <label class="btn btn-outline-primary w-50">
                                        <input type="radio" name="${predictor}TrueLabel" value="1" autocomplete="off"> True
                                    </label>
                                </div>
                            </div>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-dismiss="modal">Cancel</button>
                            <button type="button" class="btn btn-warning ${predictor}RetrainSubmit" disabled>Retrain Model</button>
                        </div>
                    </div>
                </div>
            </div>
        `;

        // Append button to container
        $retrainingContainer.html(retrainingButtonHtml);

        // Ensure prediction results area exists
        let $resultsArea = $('#predictionResultsArea');
        if ($resultsArea.length === 0) {
            console.warn('Prediction results area not found. Creating dynamically.');
            $resultsArea = $('<div id="predictionResultsArea" class="container mt-3"></div>');
            $('body').append($resultsArea);
        }

        // Append to results area
        $resultsArea.append($retrainingContainer);

        // Add event listeners for the specific modal
        $(`input[name="${predictor}TrueLabel"]`).on('change', function() {
            $(`.${predictor}RetrainSubmit`).prop('disabled', false);
        });

        // Add submit handler
        $(`.${predictor}RetrainSubmit`).on('click', function() {
            const trueLabel = parseInt($(`input[name="${predictor}TrueLabel"]:checked`).val());
            
            // Validate true label
            if (isNaN(trueLabel)) {
                alert('Please select a true label');
                return;
            }

            // Call retraining function
            retrainModel(
                predictor.toLowerCase(), 
                trueLabel, 
                spectrogramPath
            );

            // Close modal
            $(`#${predictor}RetrainingModal`).modal('hide');
        });

        console.log('Retraining button added for', predictor);
        console.groupEnd();
    }

    // Modify handlePredictionResults to ensure robust error handling
    function handlePredictionResults(results) {
        console.group('Handle Prediction Results');
        console.log('Raw Results:', JSON.stringify(results, null, 2));

        // Validate results
        if (!results || !results.analysis_results) {
            console.error('Invalid or empty prediction results');
            console.groupEnd();
            return;
        }

        // Ensure spectrogram path exists
        const spectrogramPath = results.spectrogram_path || '';
        
        const predictors = ['BNQ', 'QNQ', 'TOOT'];
        predictors.forEach(predictor => {
            try {
                // Safely extract prediction data
                const predictionData = results.analysis_results[predictor] || {};
                const predictionLabel = getPredictionLabel(predictor, results);
                
                // Safely extract confidence
                let confidence = 0;
                try {
                    confidence = formatConfidence(
                        extractConfidence(predictionData) || 0
                    );
                } catch (confError) {
                    console.warn(`Confidence extraction failed for ${predictor}:`, confError);
                }

                // Always add retraining option
                addRetrainingOption(
                    predictor, 
                    spectrogramPath, 
                    predictionLabel, 
                    parseFloat(confidence)
                );
            } catch (error) {
                console.error(`Error processing ${predictor} retraining:`, error);
            }
        });

        console.groupEnd();
    }

    // Detailed confidence extraction function
    function extractConfidence(results) {
        console.group('Confidence Extraction Debug');
        console.log('Input Results:', JSON.stringify(results, null, 2));

        let confidence;
        
        // Check if results is the correct object or if it's a metadata object
        if (results.analysis_results) {
            console.log('Found nested analysis_results, extracting from there');
            results = results.analysis_results;
        }

        // Try multiple methods to extract confidence
        if (results.confidence !== undefined) {
            confidence = results.confidence;
            console.log('Extracted from results.confidence');
        } else if (results.raw_result && results.raw_result[1] !== undefined) {
            confidence = results.raw_result[1];
            console.log('Extracted from raw_result[1]');
        } else if (results.predicted_class !== undefined) {
            // Fallback to prediction class if no direct confidence
            confidence = results.predicted_class === 1 ? 0.5 : 0.0;
            console.log('Fallback to prediction class');
        } else {
            confidence = undefined;
            console.warn('No confidence could be extracted');
        }

        console.log('Extracted Confidence:', confidence);
        console.log('Confidence Type:', typeof confidence);
        console.groupEnd();

        return confidence;
    }

    // Helper function to get prediction label
    function getPredictionLabel(predictor, results) {
        const predictionMap = {
            'BNQ': results.confidence > 0.5 ? 'Bees Detected' : 'No Bees Detected',
            'QNQ': results.confidence > 0.5 ? 'Queen Detected' : 'No Queen Detected',
            'TOOT': results.confidence > 0.5 ? 'Tooting Detected' : 'No Tooting'
        };
        return predictionMap[predictor] || 'Unknown';
    }

    // Helper function to format confidence level
    function formatConfidence(confidence) {
        console.log('Raw Confidence Input:', confidence);
        console.log('Typeof Confidence:', typeof confidence);

        // Check if confidence is a valid number
        if (confidence === undefined || confidence === null) {
            console.warn('Confidence is undefined or null');
            return 'N/A';
        }

        // Ensure confidence is a number and round to 2 decimal places
        const formattedConfidence = Number(confidence).toFixed(2);
        
        console.log('Formatted Confidence:', formattedConfidence);

        // Add percentage sign and color coding
        if (formattedConfidence > 50) {
            return `<span class="text-success">${formattedConfidence}%</span>`;
        } else if (formattedConfidence > 25) {
            return `<span class="text-warning">${formattedConfidence}%</span>`;
        } else {
            return `<span class="text-danger">${formattedConfidence}%</span>`;
        }
    }

    // Helper function to get alert class
    function getAlertClass(predictor, results) {
        return results.confidence > 0.5 
            ? 'alert-warning' 
            : 'alert-info';
    }

    // Helper function to get recommended action
    function getRecommendedAction(predictor, results) {
        const actionMap = {
            'BNQ': {
                positive: 'Hive Activity Confirmed. Continue regular monitoring.',
                negative: 'No buzzing detected. Inspect the hive for potential issues.'
            },
            'QNQ': {
                positive: 'Queen Bee Presence Confirmed. Hive appears stable.',
                negative: 'Queen Bee Might Be Absent. Prepare to introduce a new queen if necessary.'
            },
            'TOOT': {
                positive: 'Queen Tooting Detected. Potential queen emergence or competition.',
                negative: 'No queen tooting detected. Continue monitoring.'
            }
        };

        const actions = actionMap[predictor] || {};
        return results.confidence > 0.5 
            ? actions.positive || 'Positive detection' 
            : actions.negative || 'Negative detection';
    }

    // Helper function to render analysis results in a structured way
    function renderAnalysisResults(results) {
        if (typeof results !== 'object') {
            return `<p class="text-muted">No detailed analysis available</p>`;
        }

        let html = '<table class="table table-striped table-bordered">';
        html += '<thead><tr><th>Metric</th><th>Value</th></tr></thead>';
        html += '<tbody>';

        for (const [key, value] of Object.entries(results)) {
            let formattedValue = formatAnalysisValue(value);
            html += `
                <tr>
                    <td class="fw-bold">${formatKey(key)}</td>
                    <td>${formattedValue}</td>
                </tr>
            `;
        }

        html += '</tbody></table>';
        return html;
    }

    // Format keys to be more readable
    function formatKey(key) {
        return key
            .replace(/_/g, ' ')
            .replace(/\b\w/g, l => l.toUpperCase());
    }

    // Format values to be more readable
    function formatAnalysisValue(value) {
        if (value === null || value === undefined) {
            return '<span class="text-muted">N/A</span>';
        }

        if (typeof value === 'boolean') {
            return value 
                ? '<span class="text-success">Yes</span>' 
                : '<span class="text-danger">No</span>';
        }

        if (typeof value === 'number') {
            return value.toFixed(2);
        }

        if (Array.isArray(value)) {
            return value.join(', ');
        }

        return String(value);
    }

    // Add spectrogram zoom functionality
    function setupSpectrogramZoom() {
        const predictors = ['BNQ', 'QNQ', 'TOOT'];
        const enlargedSpectrogramImage = document.getElementById('enlargedSpectrogramImage');
        
        predictors.forEach(predictor => {
            const spectrogramImage = document.getElementById(`spectrogramImage-${predictor}-1`);
            
            if (spectrogramImage) {
                spectrogramImage.addEventListener('click', function() {
                    // Set the enlarged image source to the current spectrogram
                    enlargedSpectrogramImage.src = this.src;
                    
                    // Use Bootstrap's modal to show the enlarged image
                    $('#spectrogramModal').modal('show');
                });
            }
        });
    }

    // Persistent Model Retraining Section
    function createModelRetrainingSection() {
        // Create a container for all model retraining options
        const retrainingHtml = `
            <div id="modelRetrainingContainer" class="card mt-3">
                <div class="card-header">
                    <h5 class="card-title">Model Retraining</h5>
                </div>
                <div class="card-body">
                    <div class="row">
                        <div class="col-md-4">
                            <div id="bnqRetrainingArea" class="mb-3">
                                <h6>BNQ Model Retraining</h6>
                                <div class="form-inline">
                                    <select id="bnqTrueLabel" class="form-control mr-2">
                                        <option value="">Select Label</option>
                                        <option value="0">False (No Bees)</option>
                                        <option value="1">True (Bees Detected)</option>
                                    </select>
                                    <button id="bnqRetrainBtn" class="btn btn-warning btn-sm" data-model="bnq">
                                        Retrain
                                    </button>
                                </div>
                            </div>
                        </div>
                        <div class="col-md-4">
                            <div id="qnqRetrainingArea" class="mb-3">
                                <h6>QNQ Model Retraining</h6>
                                <div class="form-inline">
                                    <select id="qnqTrueLabel" class="form-control mr-2">
                                        <option value="">Select Label</option>
                                        <option value="0">False (No Queen)</option>
                                        <option value="1">True (Queen Detected)</option>
                                    </select>
                                    <button id="qnqRetrainBtn" class="btn btn-warning btn-sm" data-model="qnq">
                                        Retrain
                                    </button>
                                </div>
                            </div>
                        </div>
                        <div class="col-md-4">
                            <div id="tootRetrainingArea" class="mb-3">
                                <h6>TOOT Model Retraining</h6>
                                <div class="form-inline">
                                    <select id="tootTrueLabel" class="form-control mr-2">
                                        <option value="">Select Label</option>
                                        <option value="0">False (No Tooting)</option>
                                        <option value="1">True (Tooting)</option>
                                    </select>
                                    <button id="tootRetrainBtn" class="btn btn-warning btn-sm" data-model="toot">
                                        Retrain
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;

        // Create and append retraining section
        const $retrainingSection = $(retrainingHtml);
        $('#predictionResultsArea').append($retrainingSection);

        // Event listeners for retraining buttons
        $('#modelRetrainingContainer').on('click', '.btn-warning', function() {
            const modelType = $(this).data('model');
            const $labelSelect = $(`#${modelType}TrueLabel`);
            const trueLabel = $labelSelect.val();
            
            // Validate label selection
            if (!trueLabel) {
                alert(`Please select a label for ${modelType.toUpperCase()} model`);
                return;
            }

            // Call retraining function
            retrainModel(
                modelType, 
                parseInt(trueLabel), 
                null  // No spectrogram path for now
            );

            // Optional: Reset label selection
            $labelSelect.val('');
        });
    }

    // Initialize retraining section when page loads
    $(document).ready(function() {
        // Ensure prediction results area exists
        if ($('#predictionResultsArea').length === 0) {
            $('body').append('<div id="predictionResultsArea" class="container mt-3"></div>');
        }
        
        // Create retraining section
        createModelRetrainingSection();
    });

    // Initialize page
    fetchAudioDevices();

    // Attach event listener to record button
    recordButton.addEventListener('click', recordAudioForPredictors);

    // Call setup function after other initializations
    setupSpectrogramZoom();
});
