import yaml
import os
from pathlib import Path
from typing import Dict, Any, List
from logging_utils import log


class DrawerDissectConfig:
    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = Path(config_path)
        self._config = self._load_config()
        self._roboflow_cache = None
        self._api_keys_cache = None
        self._runner_cache: Dict[str, Any] = {}
        self._setup_base_directories()

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def _load_config(self) -> Dict[str, Any]:
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found at {self.config_path}")
        with open(self.config_path) as f:
            return yaml.safe_load(f)

    def _setup_base_directories(self):
        """Create the unsorted directory on first run."""
        base_dir = self._config.get("base_directory", "")
        Path(os.path.join(base_dir, self._config["directories"]["unsorted"])).mkdir(
            parents=True, exist_ok=True
        )

    # ------------------------------------------------------------------
    # Deployment
    # ------------------------------------------------------------------

    @property
    def deployment(self) -> str:
        """Active deployment mode: 'roboflow' or 'local'. Defaults to 'roboflow'."""
        return self._config.get("deployment", "roboflow")

    # ------------------------------------------------------------------
    # Model runner cache (keyed by model_key)
    # ------------------------------------------------------------------

    def get_cached_runner(self, model_key: str):
        """Return a cached model runner, or None if not yet built."""
        return self._runner_cache.get(model_key)

    def set_cached_runner(self, model_key: str, runner):
        """Store a built model runner in the cache."""
        self._runner_cache[model_key] = runner

    # ------------------------------------------------------------------
    # Local inference
    # ------------------------------------------------------------------

    @property
    def local_device(self) -> str:
        """Device for local inference: 'auto', 'cpu', 'cuda', 'mps', etc."""
        return self._config.get("local", {}).get("device", "auto")

    def get_local_weights_path(self, model_key: str) -> str:
        """
        Resolve the .pt weights path for a given model key.

        If config.yaml specifies a filename under local.models, that is used.
        Otherwise the model's subfolder is scanned: if exactly one .pt file is
        found it is used automatically. If there are multiple, the user is asked
        to specify which one in config.yaml.
        """
        local_cfg = self._config.get("local", {})
        weights_dir = Path(local_cfg.get("weights_dir", "weights"))
        model_dir = weights_dir / model_key
        specified = local_cfg.get("models", {}).get(model_key)

        if specified:
            full_path = model_dir / specified
            if not full_path.exists():
                raise FileNotFoundError(
                    f"Weights file not found: {full_path.resolve()}\n"
                    f"Place the .pt file there or update local.models.{model_key} in config.yaml."
                )
            return str(full_path)

        # No filename specified — scan the folder
        if not model_dir.exists():
            raise FileNotFoundError(
                f"Weights folder not found: {model_dir.resolve()}\n"
                f"Create the folder and place a .pt file inside it."
            )

        pt_files = list(model_dir.glob("*.pt"))

        if len(pt_files) == 1:
            log(f"Auto-detected weights for '{model_key}': {pt_files[0].name}")
            return str(pt_files[0])

        if len(pt_files) == 0:
            raise FileNotFoundError(
                f"No .pt weights file found in: {model_dir.resolve()}\n"
                f"Place a .pt file there."
            )

        # Multiple files — can't guess, ask the user to be specific
        names = ", ".join(f.name for f in pt_files)
        raise ValueError(
            f"Multiple .pt files found in {model_dir}: {names}\n"
            f"Specify which to use under local.models.{model_key} in config.yaml."
        )

    # ------------------------------------------------------------------
    # Roboflow
    # ------------------------------------------------------------------

    def get_roboflow_instance(self):
        """Lazily initialise and cache the Roboflow API connection."""
        if self._roboflow_cache is not None:
            return self._roboflow_cache

        try:
            import roboflow as rf_lib
        except ImportError:
            raise ImportError(
                "roboflow package is required for Roboflow deployment. "
                "Install it with: pip install roboflow"
            )

        log("Initializing Roboflow API connection")
        rf = rf_lib.Roboflow(api_key=self.api_keys["roboflow"])
        ws = rf.workspace(self.workspace)
        self._roboflow_cache = (rf, ws)
        return self._roboflow_cache

    @property
    def roboflow_models(self) -> Dict[str, Dict[str, Any]]:
        return self._config["roboflow"]["models"]

    @property
    def workspace(self) -> str:
        return self._config["roboflow"]["workspace"]

    # ------------------------------------------------------------------
    # API keys  (cached to avoid repeated env-var lookups and log spam)
    # ------------------------------------------------------------------

    @property
    def api_keys(self) -> Dict[str, str]:
        if self._api_keys_cache is not None:
            return self._api_keys_cache

        resolved = {}
        for key_name, config_value in self._config["api_keys"].items():
            env_value = os.getenv(config_value)
            if env_value:
                resolved[key_name] = env_value
                log(f"API key '{key_name}' loaded from environment variable '{config_value}'")
            else:
                resolved[key_name] = config_value
                log(f"API key '{key_name}' loaded from config file")

        self._api_keys_cache = resolved
        return self._api_keys_cache

    # ------------------------------------------------------------------
    # Drawer discovery / management
    # ------------------------------------------------------------------

    def get_existing_drawers(self) -> List[str]:
        """List existing drawer folders (excludes 'unsorted')."""
        drawers_base = os.path.dirname(self.unsorted_directory)
        if not os.path.exists(drawers_base):
            return []
        return sorted(
            item for item in os.listdir(drawers_base)
            if os.path.isdir(os.path.join(drawers_base, item)) and item != "unsorted"
        )

    def setup_drawer_directories(self, drawer_id: str):
        """Create all subdirectories for a specific drawer."""
        drawer_base = self.get_drawer_path(drawer_id)
        Path(drawer_base).mkdir(parents=True, exist_ok=True)
        for subdir in self._config["directories"]["drawer_subdirs"].values():
            Path(os.path.join(drawer_base, subdir)).mkdir(parents=True, exist_ok=True)

    def get_drawer_path(self, drawer_id: str) -> str:
        base_dir = self._config.get("base_directory", "")
        drawers_base = os.path.dirname(
            os.path.join(base_dir, self._config["directories"]["unsorted"])
        )
        return os.path.join(drawers_base, drawer_id)

    def get_drawer_directory(self, drawer_id: str, subdir_key: str) -> str:
        subdir = self._config["directories"]["drawer_subdirs"][subdir_key]
        return os.path.join(self.get_drawer_path(drawer_id), subdir)

    def move_image_to_drawer(self, drawer_id: str, filename: str) -> bool:
        """Move an image from unsorted to the drawer's fullsize folder."""
        src = os.path.join(self.unsorted_directory, filename)
        if not os.path.exists(src):
            return False
        self.setup_drawer_directories(drawer_id)
        os.rename(src, os.path.join(self.get_drawer_directory(drawer_id, "fullsize"), filename))
        return True

    @property
    def unsorted_directory(self) -> str:
        base_dir = self._config.get("base_directory", "")
        return os.path.join(base_dir, self._config["directories"]["unsorted"])

    # ------------------------------------------------------------------
    # LLM / processing config
    # ------------------------------------------------------------------

    @property
    def claude_config(self) -> Dict[str, Any]:
        defaults = {"model": "claude-sonnet-4-20250514", "max_tokens": 600}
        return {**defaults, **self._config.get("claude", {})}

    @property
    def processing_flags(self) -> Dict[str, Any]:
        return self._config["processing"]

    @property
    def prompts(self) -> Dict[str, Any]:
        return self._config.get("prompts", {})

    def get_memory_config(self, step: str) -> Dict[str, Any]:
        memory = self._config.get("resources", {}).get("memory", {})
        override = memory.get("step_overrides", {}).get(step, {})
        if override:
            return override
        return {k: v for k, v in memory.items() if k != "step_overrides"}