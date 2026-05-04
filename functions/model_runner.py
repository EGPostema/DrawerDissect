"""
model_runner.py

Unified model abstraction layer for DrawerDissect.
Wraps both Roboflow (cloud) and local YOLO (ultralytics) backends
behind a single predict() interface, so all infer_*.py functions are
backend-agnostic.

Both backends return predictions in the same Roboflow-compatible JSON format:
{
    "predictions": [
        {
            "x": float,        # bbox center x
            "y": float,        # bbox center y
            "width": float,
            "height": float,
            "confidence": float,
            "class": str,
            "points": [        # segmentation models only
                {"x": float, "y": float}, ...
            ]
        }
    ],
    "image": {"width": int, "height": int}
}
"""

from pathlib import Path
from logging_utils import log


def get_device(device_setting: str = "auto") -> str:
    """
    Resolve the compute device for local inference.

    Args:
        device_setting: "auto", "cpu", "cuda", "cuda:0", "mps", etc.

    Returns:
        Device string suitable for ultralytics YOLO.
    """
    if device_setting != "auto":
        return device_setting

    try:
        import torch
        if torch.cuda.is_available():
            device = "cuda:0"
            log(f"Auto-detected GPU: {torch.cuda.get_device_name(0)} → using {device}")
            return device
        if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            log("Auto-detected Apple Silicon GPU → using mps")
            return "mps"
    except ImportError:
        pass

    log("No GPU detected → using cpu")
    return "cpu"


class RoboflowModelRunner:
    """Thin wrapper around a Roboflow model object."""

    def __init__(self, model):
        self._model = model

    def predict(self, image_path: str, confidence: float = 50, overlap: float = 50) -> dict:
        """
        Run inference and return the Roboflow SDK's native JSON output.
        Segmentation models do not accept the overlap parameter, and
        classification models accept neither confidence nor overlap,
        so we fall back progressively.
        """
        try:
            return self._model.predict(image_path, confidence=confidence, overlap=overlap).json()
        except TypeError:
            try:
                return self._model.predict(image_path, confidence=confidence).json()
            except TypeError:
                return self._model.predict(image_path).json()


class LocalModelRunner:
    """
    Wrapper around an ultralytics YOLO model that emits output in
    Roboflow-compatible JSON format so the rest of the pipeline is unchanged.
    """

    def __init__(self, weights_path: str, device: str = "auto"):
        if not Path(weights_path).exists():
            raise FileNotFoundError(
                f"Weights file not found: {weights_path}\n"
                f"Place the .pt file at that path or update local.models in config.yaml."
            )

        try:
            from ultralytics import YOLO
        except ImportError:
            raise ImportError(
                "ultralytics is required for local inference. "
                "Install it with: pip install ultralytics"
            )

        self._device = get_device(device)
        log(f"Loading local model: {weights_path} on device={self._device}")
        self._model = YOLO(weights_path)

    def predict(self, image_path: str, confidence: float = 50, overlap: float = 50) -> dict:
        """
        Run local YOLO inference and return a Roboflow-compatible dict.

        confidence and overlap follow the Roboflow 0-100 convention and are
        converted to 0-1 for ultralytics internally.
        """
        results = self._model.predict(
            source=image_path,
            conf=confidence / 100.0,
            iou=overlap / 100.0,
            device=self._device,
            verbose=False,
        )

        result = results[0]
        img_h, img_w = result.orig_shape
        predictions = []

        if result.boxes is not None and len(result.boxes):
            for i, box in enumerate(result.boxes):
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                cls_id = int(box.cls[0])

                pred = {
                    "x": round((x1 + x2) / 2, 2),
                    "y": round((y1 + y2) / 2, 2),
                    "width": round(x2 - x1, 2),
                    "height": round(y2 - y1, 2),
                    "confidence": round(float(box.conf[0]), 4),
                    "class": result.names[cls_id],
                    "class_id": cls_id,
                    "detection_id": str(i),
                }

                if result.masks is not None and i < len(result.masks):
                    pred["points"] = [
                        {"x": round(float(pt[0]), 2), "y": round(float(pt[1]), 2)}
                        for pt in result.masks.xy[i].tolist()
                    ]

                predictions.append(pred)

        return {
            "predictions": predictions,
            "image": {"width": img_w, "height": img_h},
        }


def build_model_runner(config, model_key: str):
    """
    Factory — returns the correct runner based on config.deployment.
    Results are cached on the config object so each model is only loaded once.

    For bugcleaner specifically:
    - If deployment is "local" but no weights are found, falls back to Roboflow
      (since no local bugcleaner weights are currently available).
    - If Roboflow is also unavailable, returns None so the caller can decide
      whether to skip filtering or abort.

    Args:
        config:    DrawerDissectConfig instance
        model_key: One of "drawer", "tray", "label", "mask", "pin", "bugcleaner"

    Returns:
        RoboflowModelRunner, LocalModelRunner, or None (bugcleaner only)
    """
    cached = config.get_cached_runner(model_key)
    if cached is not None:
        return cached

    if config.deployment == "roboflow":
        runner = _build_roboflow_runner(config, model_key)

    elif config.deployment == "local":
        # For bugcleaner, fall back to Roboflow if no local weights exist
        if model_key == "bugcleaner":
            try:
                config.get_local_weights_path(model_key)
                runner = _build_local_runner(config, model_key)
            except (FileNotFoundError, ValueError):
                log(f"[local] No bugcleaner weights found — falling back to Roboflow")
                runner = _build_roboflow_runner(config, model_key, allow_fail=True)
        else:
            runner = _build_local_runner(config, model_key)

    else:
        raise ValueError(
            f"Unknown deployment mode: '{config.deployment}'. "
            "Set deployment to 'roboflow' or 'local' in config.yaml."
        )

    if runner is not None:
        config.set_cached_runner(model_key, runner)
    return runner


def _build_roboflow_runner(config, model_key: str, allow_fail: bool = False):
    """Build a RoboflowModelRunner, optionally returning None on failure."""
    try:
        _, workspace_instance = config.get_roboflow_instance()
        model_cfg = config.roboflow_models[model_key]
        rf_model = (
            workspace_instance
            .project(model_cfg["endpoint"])
            .version(model_cfg["version"])
            .model
        )

        # Prevent the Roboflow SDK from double-resizing images
        if hasattr(rf_model, "preprocessing") and "resize" in rf_model.preprocessing:
            del rf_model.preprocessing["resize"]

        log(f"[roboflow] {model_key}: {model_cfg['endpoint']} v{model_cfg['version']}")
        return RoboflowModelRunner(rf_model)

    except Exception as e:
        if allow_fail:
            log(f"[roboflow] {model_key} unavailable: {e}")
            return None
        raise


def _build_local_runner(config, model_key: str):
    """Build a LocalModelRunner."""
    log(f"[local] {model_key}: {config.get_local_weights_path(model_key)}")
    return LocalModelRunner(
        config.get_local_weights_path(model_key),
        device=config.local_device,
    )
