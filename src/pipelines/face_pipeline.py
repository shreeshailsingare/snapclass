

import dlib
import numpy as np
import face_recognition_models
from sklearn.svm import SVC
import streamlit as st

from src.database.db import get_all_students


@st.cache_resource
def load_dlib_models():
    detector = dlib.get_frontal_face_detector() 


    sp = dlib.shape_predictor(
        face_recognition_models.pose_predictor_model_location()
    )

    facerec = dlib.face_recognition_model_v1(
        face_recognition_models.face_recognition_model_location()
    )

    return detector, sp, facerec

def get_face_embeddings(image_np):
    detector, sp, facerec = load_dlib_models()
    faces = detector(image_np, 1)

    encodings= []

    for face in faces:
        shape = sp(image_np, face)
        face_descriptor = facerec.compute_face_descriptor(image_np, shape, 1) #128 embedding

        encodings.append(np.array(face_descriptor))
    return encodings


def get_trained_model():
    X = []
    y = []


    student_db = get_all_students()

    if not student_db:
        return None
    
    for student in student_db:
        embedding = student.get('face_embedding')
        if embedding:
            X.append(np.array(embedding))
            y.append(student.get('student_id'))

    if len(X) ==0:
        return 0
    
    clf = SVC(kernel='linear', probability=True, class_weight='balanced')

    try:
        clf.fit(X, y)
    except ValueError:
        pass

    return {'clf': clf, 'X':X, "y":y}


def train_classifier():
    return bool(get_trained_model())

def predict_attendance(class_image_np):
    encodings = get_face_embeddings(class_image_np)
    detected_student = {}

    model_data = get_trained_model()

    if not model_data or len(encodings) == 0:
        return detected_student, [], len(encodings)
    
    clf = model_data['clf']
    
    X_train = np.array(model_data['X'], dtype=np.float64)
    y_train = model_data['y']

    all_students = sorted(list(set(y_train)))

    
    RESEMBLED_THRESHOLD = 0.42

    for encoding in encodings:
        
        encoding_np = np.array(encoding, dtype=np.float64).reshape(1, -1)
        
        distances = np.linalg.norm(X_train - encoding_np, axis=1)
        best_match_idx = np.argmin(distances)
        min_distance = distances[best_match_idx]

        print("DISTANCES:", distances)
        print("MIN DIST:", min_distance)

        closest_student_id = int(y_train[best_match_idx])



        
        print(f"[DEBUG PIPELINE] Nearest ID: {closest_student_id} | Computed Distance: {min_distance:.4f}")

        
        if min_distance <= RESEMBLED_THRESHOLD:
            
            
            if clf is not None and len(all_students) >= 2:
                predicted_id = int(clf.predict(encoding_np)[0])
                
                
                if predicted_id == closest_student_id:
                    detected_student[predicted_id] = True
                else:
                    
                    detected_student[closest_student_id] = True
            else:
                
                detected_student[closest_student_id] = True
        else:
        
            print(f"[DEBUG PIPELINE] Unrecognized profile detected. Prompting registration flow.")

    return detected_student, all_students, len(encodings)