import yaml
from pathlib import Path
from typing import Dict, Any
import os

class DrawerDissectConfig:
    def __init__(self, config_path: str = "config.yaml"):
        """Initialize config from YAML file."""
        self.config_path = Path(config_path)
        self._config = self._load_config()
        self._setup_directories()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load and parse the YAML configuration file."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found at {self.config_path}")
        
        with open(self.config_path) as f:
            return yaml.safe_load(f)
    
    def _setup_directories(self):
        """Create all directories defined in config."""
        for directory in self.directories.values():
            Path(directory).mkdir(parents=True, exist_ok=True)
            print(f"Verified directory: {directory}")
    
    @property
    def api_keys(self) -> Dict[str, str]:
        """Get API keys from config."""
        return self._config['api_keys']
    
    @property
    def roboflow_models(self) -> Dict[str, Dict[str, Any]]:
        """Get Roboflow model configurations."""
        return self._config['roboflow']['models']
    
    @property
    def workspace(self) -> str:
        """Get Roboflow workspace name."""
        return self._config['roboflow']['workspace']
    
    @property
    def processing_flags(self) -> Dict[str, bool]:
        """Get processing toggle flags."""
        return self._config['processing']
    
    @property
    def directories(self) -> Dict[str, str]:
        """Get directory paths, prefixed with base_directory if specified."""
        base_dir = self._config.get('base_directory', '')
        dirs = self._config['directories']
        return {k: os.path.join(base_dir, v) for k, v in dirs.items()}

    @property
    def prompts(self) -> Dict[str, Dict[str, str]]:
        """Get prompt configurations."""
        return self._config.get('prompts', {})

