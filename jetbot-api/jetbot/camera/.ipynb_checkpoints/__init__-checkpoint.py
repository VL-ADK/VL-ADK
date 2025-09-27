import threading, time, cv2

class Camera:
    _inst = None
    def __init__(self, device=0, width=640, height=480, fps=30):
        self.cap = cv2.VideoCapture(device)
        if width:  self.cap.set(cv2.CAP_PROP_FRAME_WIDTH,  width)
        if height: self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        if fps:    self.cap.set(cv2.CAP_PROP_FPS, fps)
        ok, frame = self.cap.read()
        if not ok:
            raise RuntimeError('USB camera failed to deliver a frame')
        self.value = frame
        self._stop = False
        self._t = threading.Thread(target=self._loop, daemon=True)
        self._t.start()

    def _loop(self):
        while not self._stop:
            ok, frame = self.cap.read()
            if ok:
                self.value = frame
            else:
                time.sleep(0.01)

    def stop(self):
        self._stop = True
        try: self._t.join(timeout=1.0)
        except: pass
        try: self.cap.release()
        except: pass

    @staticmethod
    def instance(*args, **kwargs):
        if Camera._inst is None:
            Camera._inst = Camera(*args, **kwargs)
        return Camera._inst
