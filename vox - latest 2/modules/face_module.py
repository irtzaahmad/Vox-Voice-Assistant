"""
Vox Face Recognition Module v3.0
Register and recognize faces. Optional — gracefully disabled if libs missing.
"""
import os, threading

class FaceModule:
    def __init__(self, db, faces_dir: str):
        self.db        = db
        self.faces_dir = faces_dir
        self.available = False
        self._check()

    def _check(self):
        try:
            import face_recognition, cv2
            self.available = True
            print("✅ Face recognition available")
        except ImportError:
            self.available = False
            print("ℹ️  Face recognition not installed (optional)")
            print("   Install: pip install face_recognition opencv-python")

    def capture(self, user_id: int, username: str) -> tuple:
        if not self.available:
            return False, "Install face_recognition:\npip install face_recognition opencv-python cmake dlib"
        try:
            import face_recognition, cv2, numpy as np
            cap = cv2.VideoCapture(0)
            if not cap.isOpened():
                return False, "Cannot access webcam."
            encoding = None
            for _ in range(40):
                ret, frame = cap.read()
                if not ret: continue
                rgb   = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                locs  = face_recognition.face_locations(rgb)
                encs  = face_recognition.face_encodings(rgb, locs)
                if encs:
                    encoding = encs[0]
                    break
            cap.release()
            if encoding is None:
                return False, "No face detected. Ensure good lighting and face the camera."
            ok = self.db.save_face(user_id, encoding)
            return (True, "Face registered!") if ok else (False, "Could not save face data.")
        except Exception as e:
            return False, f"Face capture error: {e}"

    def recognize(self, timeout=8.0) -> tuple:
        if not self.available:
            return False, {}
        try:
            import face_recognition, cv2, time
            known  = self.db.get_all_faces()
            if not known:
                return False, {}
            cap    = cv2.VideoCapture(0)
            if not cap.isOpened():
                return False, {}
            start  = time.time()
            result = None
            while time.time() - start < timeout:
                ret, frame = cap.read()
                if not ret: continue
                small  = cv2.resize(frame, (0,0), fx=0.5, fy=0.5)
                rgb    = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)
                locs   = face_recognition.face_locations(rgb)
                encs   = face_recognition.face_encodings(rgb, locs)
                for enc in encs:
                    for kf in known:
                        dist = face_recognition.face_distance([kf['encoding']], enc)[0]
                        if dist < 0.55:
                            result = kf
                            break
                if result:
                    break
            cap.release()
            if result:
                return True, {'user_id': result['user_id'],
                              'username': result['username'],
                              'full_name': result['full_name']}
            return False, {}
        except Exception as e:
            return False, {}

    def start_recognition_thread(self, callback, timeout=8.0):
        def run():
            ok, user = self.recognize(timeout)
            callback(ok, user)
        threading.Thread(target=run, daemon=True).start()


