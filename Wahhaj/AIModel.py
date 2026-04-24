from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Union


import cv2
import numpy as np
from ultralytics import YOLO

from .UAVImage import UAVImage
from .models import Raster


class AIModel:
    """
    AIModel for WAHHAJ
    -----------------
    مسؤول عن:
    - تحميل مودل YOLOv8s segmentation المعتمد
    - تشغيل inference على صور UAV
    - إرجاع detections منظمة
    - تحويل نتيجة segmentation إلى Raster usable
    """

    DEFAULT_CLASS_NAMES: Dict[int, str] = {
        0: "building",
        1: "vegetation",
        2: "water",
    }

    def __init__(
        self,
        modelPath: str = "weights/wahhaj_yolov8s_seg_baseline_v4_best.pt",
        confidenceThreshold: float = 0.25,
        imageSize: int = 640,
        device: str = "cpu",
        classNames: Optional[Dict[int, str]] = None,
    ) -> None:
        self.modelPath = modelPath
        self.confidenceThreshold = confidenceThreshold
        self.imageSize = imageSize
        self.device = device
        self.classNames = classNames or self.DEFAULT_CLASS_NAMES
        self._model: Optional[YOLO] = None

    def _load_model(self) -> YOLO:
        if self._model is None:
            model_path = Path(self.modelPath)
            if not model_path.exists():
                raise FileNotFoundError(
                    f"Model weights not found: {model_path}"
                )
            self._model = YOLO(str(model_path))
        return self._model

    def _resolve_image_path(self, image: Union[UAVImage, str, Path]) -> str:
        if isinstance(image, UAVImage):
            return image.filePath
        if isinstance(image, Path):
            return str(image)
        if isinstance(image, str):
            return image
        raise TypeError("image must be UAVImage, str, or Path")


    def _preprocess_image(self, image_path: str) -> np.ndarray:
        """
        Minimal pass-through preprocessing.

        This only reads the image into memory without changing colors,
        resizing, denoising, cropping, or normalization.
        YOLO will still handle its own internal preprocessing.
        """
        img = cv2.imread(image_path)

        if img is None:
            raise ValueError(f"Unable to read image file: {image_path}")

        return img




    def _run_inference(self, image: Union[UAVImage, str, Path]):
        image_path = self._resolve_image_path(image)

        if not Path(image_path).exists():
            raise FileNotFoundError(f"Image file not found: {image_path}")

        preprocessed_image = self._preprocess_image(image_path)

        model = self._load_model()
        results = model.predict(
            source=preprocessed_image,
            imgsz=self.imageSize,
            conf=self.confidenceThreshold,
            retina_masks=True,
            verbose=False,
            device=self.device,
        )

        if not results:
            raise RuntimeError("YOLO returned no results.")

        return results[0]

    def detectObjects(self, image: Union[UAVImage, str, Path]) -> Dict[str, Any]:
        """
        UML method:
        detectObjects(image: UAVImage): VectorLayer

        مؤقتًا نرجعه كـ dict منظم
        """
        image_path = self._resolve_image_path(image)
        result = self._run_inference(image)

        detections: List[Dict[str, Any]] = []

        boxes = result.boxes
        masks = result.masks

        if boxes is None or boxes.cls is None:
            return {
                "image_path": image_path,
                "detections": [],
                "summary": {
                    "count": 0,
                    "counts_by_class": {
                        name: 0 for name in self.classNames.values()
                    },
                },
            }

        cls_ids = boxes.cls.cpu().numpy().astype(int)
        confs = boxes.conf.cpu().numpy()
        xyxy = boxes.xyxy.cpu().numpy()

        polygons = None
        if masks is not None and masks.xy is not None:
            polygons = masks.xy

        counts_by_class = {name: 0 for name in self.classNames.values()}

        for i, class_id in enumerate(cls_ids):
            class_name = self.classNames.get(class_id, f"class_{class_id}")

            polygon = None
            if polygons is not None and i < len(polygons):
                polygon = polygons[i].tolist()

            detections.append({
                "class_id": int(class_id),
                "class_name": class_name,
                "confidence": float(confs[i]),
                "bbox": xyxy[i].tolist(),
                "polygon": polygon,
            })

            counts_by_class[class_name] += 1

        return {
            "image_path": image_path,
            "detections": detections,
            "summary": {
                "count": len(detections),
                "counts_by_class": counts_by_class,
            },
        }

    def classifyArea(self, image: Union[UAVImage, str, Path]) -> Raster:
        """
        UML method:
        classifyArea(): Raster

        يرجع class raster:
            0 = building
            1 = vegetation
            2 = water
           -1 = background/nodata
        """
        image_path = self._resolve_image_path(image)
        result = self._run_inference(image)

        if result.orig_shape is None:
            raise RuntimeError("Inference result missing original image shape.")

        height, width = result.orig_shape[:2]
        class_map = np.full((height, width), -1, dtype=np.float32)

        boxes = result.boxes
        masks = result.masks

        if boxes is None or masks is None or masks.data is None:
            return Raster(
                data=class_map,
                nodata=-1.0,
                metadata={
                    "layer": "lulc_from_ai",
                    "source": "AIModel",
                    "image_path": image_path,
                    "class_names": self.classNames,
                },
            )

        cls_ids = boxes.cls.cpu().numpy().astype(int)
        confs = boxes.conf.cpu().numpy()
        mask_arrays = masks.data.cpu().numpy()

        order = np.argsort(confs)

        for idx in order:
            class_id = int(cls_ids[idx])
            mask = mask_arrays[idx] > 0.5
            class_map[mask] = float(class_id)

        return Raster(
            data=class_map,
            nodata=-1.0,
            metadata={
                "layer": "lulc_from_ai",
                "source": "AIModel",
                "image_path": image_path,
                "model_path": self.modelPath,
                "confidence_threshold": self.confidenceThreshold,
                "class_names": self.classNames,
            },
        )
