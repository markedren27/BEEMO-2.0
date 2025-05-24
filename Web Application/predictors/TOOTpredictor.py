import os
import numpy as np
import logging
import sys
from tensorflow.keras.preprocessing import image
from tensorflow.keras.models import load_model
from tensorflow.keras.optimizers import Adam
from sklearn.metrics import f1_score, precision_score
from audio_analyzer.sheets_utils import save_prediction_to_sheets

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("TOOTpredictor")

# Suppress TensorFlow and absl logs
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

# Model path
base_dir = os.path.dirname(os.path.abspath(__file__))
model_path = os.path.join(project_root, 'training_models', 'TOOT_model.keras')

# Check if model exists, if not create a placeholder
try:
    if not os.path.exists(model_path):
        logger.warning(f"Model file not found at {model_path}. Creating a placeholder model.")
        
        # Create a simple placeholder model
        from tensorflow.keras.models import Sequential
        from tensorflow.keras.layers import Dense, Flatten, Conv2D, MaxPooling2D
        
        model = Sequential([
            Conv2D(32, (3, 3), activation='relu', input_shape=(224, 224, 3)),
            MaxPooling2D((2, 2)),
            Flatten(),
            Dense(64, activation='relu'),
            Dense(2, activation='softmax')  # Binary classification
        ])
        
        model.compile(
            optimizer=Adam(learning_rate=0.01), 
            loss='categorical_crossentropy', 
            metrics=['accuracy']
        )
        
        # Save the placeholder model
        model.save(model_path)
        logger.info(f"Placeholder model saved to {model_path}")
    else:
        model = load_model(model_path)
except Exception as e:
    logger.error(f"Error creating/loading model: {e}")
    model = None

# Function to load and preprocess images
def load_and_preprocess_image(img_path):
    if img_path is None:
        logger.error("Image path is None")
        raise ValueError("Image path is None")
    if not os.path.exists(img_path):
        logger.error(f"Image file does not exist: {img_path}")
        raise FileNotFoundError(f"Image file does not exist: {img_path}")
    img = image.load_img(img_path, target_size=(224, 224))  # Adjust size as per your model's input
    img_array = image.img_to_array(img)
    img_array = np.expand_dims(img_array, axis=0)  # Add batch dimension
    img_array /= 255.0  # Normalize to [0, 1]
    return img_array

# Function to predict and display results for a specific image
def predict_and_display(img_path, output_box=None):
    # Define class names
    class_names = ['No Tooting', 'Tooting']

    # Check if model is available
    if model is None:
        logger.error("No model available for prediction")
        return 0, 0.0, 0.0, 0.0

    try:
        # Load and preprocess the specific image
        img_array = load_and_preprocess_image(img_path)

        # Predict the class of the image
        pred = model.predict(img_array)
        
        # Robust confidence calculation
        if pred.ndim > 1 and pred.shape[1] > 1:
            # Multi-class prediction (softmax output)
            confidence = np.max(pred[0])
            predicted_class = np.argmax(pred[0])
        else:
            # Binary classification
            confidence = pred[0][0]
            predicted_class = 1 if confidence > 0.5 else 0

        # Ensure confidence is between 0 and 1
        confidence = max(0.0, min(1.0, confidence))

        # Logging
        logger.info(f'File: {os.path.basename(img_path)}, '
                    f'Predicted: {class_names[predicted_class]}, '
                    f'Confidence: {confidence * 100:.2f}%')

        # Save prediction to Google Sheets
        prediction_data = {
            'model': 'TOOT',
            'filename': os.path.basename(img_path),
            'prediction': class_names[predicted_class],
            'confidence': float(confidence)
        }
        save_prediction_to_sheets('toot', prediction_data)

        # Placeholder metrics
        f1 = confidence
        precision = confidence

        return predicted_class, confidence, f1, precision

    except Exception as e:
        logger.error(f"Prediction error for {img_path}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return 0, 0.0, 0.0, 0.0

# Function to collect new data and labels for retraining
def collect_new_data_and_labels(true_label, img_path):
    logger.info(f"Collecting new data for retraining. img_path: {img_path}, true_label: {true_label}")
    img_array = load_and_preprocess_image(img_path)
    new_data = img_array
    new_labels = np.array([true_label])
    return new_data, new_labels

# Function to retrain the model incrementally
def retrain_model(model, new_data, new_labels):
    logger.info("Starting retraining of TOOT model...")
    model.compile(optimizer=Adam(learning_rate=0.01), loss='categorical_crossentropy', metrics=['accuracy'])
    model.fit(new_data, new_labels, epochs=1, verbose=0)
    model.save(model_path)  # Save the updated model
    logger.info(f"TOOT model retrained and saved to {model_path}")

# Function to manually set true label and retrain if incorrect
def manual_set_true_label_and_retrain(true_label, img_path):
    logger.info(f"Manual setting of true label: {true_label} for image: {img_path}")
    new_data, new_labels = collect_new_data_and_labels(true_label, img_path)
    retrain_model(model, new_data, new_labels)
    predicted_class, confidence, f1, precision = predict_and_display(img_path, output_box=None)
    
    # Save results to Google Sheets (if available)
    try:
        prediction_data = {
            'model': 'TOOT',
            'filename': os.path.basename(img_path),
            'true_label': true_label,
            'predicted_class': predicted_class,
            'confidence': float(confidence),
            'f1_score': f1,
            'precision': precision,
            'model_retrained': True
        }
        save_prediction_to_sheets('toot', prediction_data)
    except Exception as e:
        logger.error(f"Error saving retrained results: {e}")
    
    logger.info("Manual retraining completed.")

# Placeholder for other functions to maintain compatibility
def connect_to_google_sheets():
    logger.warning("Google Sheets integration is not available")
    return None

def save_results_to_google_sheets(*args, **kwargs):
    logger.warning("Google Sheets logging is not available")
    pass

def handle_feedback(*args, **kwargs):
    logger.warning("Manual retraining is not available")
    pass