"""
src/ocr/opencv_preprocessor.py
Pré-processador de imagem com suporte nativo e fallback gracioso.
"""

import numpy as np

try:
    import cv2
    HAS_CV2 = True
except Exception:
    HAS_CV2 = False

class OpenCVDocumentPreprocessor:
    """
    Técnicas de pré-processamento para maximizar o reconhecimento do OCR em páginas degradadas.
    """

    @staticmethod
    def deskew(image: np.ndarray) -> np.ndarray:
        if not HAS_CV2 or image is None:
            return image

        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image

        thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)[1]
        coords = np.column_stack(np.where(thresh > 0))
        
        if len(coords) == 0:
            return image

        angle = cv2.minAreaRect(coords)[-1]
        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle

        if abs(angle) > 0.5 and abs(angle) < 45.0:
            (h, w) = image.shape[:2]
            center = (w // 2, h // 2)
            M = cv2.getRotationMatrix2D(center, angle, 1.0)
            rotated = cv2.warpAffine(image, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
            return rotated

        return image

    @staticmethod
    def enhance_contrast_clahe(image: np.ndarray) -> np.ndarray:
        if not HAS_CV2 or image is None:
            return image

        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image

        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        return clahe.apply(gray)

    @staticmethod
    def adaptive_binarize(image: np.ndarray) -> np.ndarray:
        if not HAS_CV2 or image is None:
            return image

        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image

        return cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 21, 10
        )

    @classmethod
    def process_degraded_page(cls, img_bytes: bytes) -> bytes:
        if not HAS_CV2:
            return img_bytes

        img_np = cv2.imdecode(np.frombuffer(img_bytes, np.uint8), cv2.IMREAD_COLOR)
        if img_np is None:
            return img_bytes

        deskewed = cls.deskew(img_np)
        enhanced = cls.enhance_contrast_clahe(deskewed)
        denoised = cv2.fastNlMeansDenoising(enhanced, h=10)
        
        success, encoded_img = cv2.imencode('.png', denoised)
        return encoded_img.tobytes() if success else img_bytes
