import os
from typing import Dict, Any

class Config:
    # Base configuration
    UPLOAD_DIR = os.getenv("UPLOAD_DIR", "./uploads")
    MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://mongo:27017")
    MONGODB_DB = os.getenv("MONGODB_DB", "kleinanzeigen")
    
    # CORS settings
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")
    
    # API settings
    API_PREFIX = os.getenv("API_PREFIX", "/api")
    
    @classmethod
    def get_config(cls) -> Dict[str, Any]:
        return {
            "upload_dir": cls.UPLOAD_DIR,
            "mongodb_url": cls.MONGODB_URL,
            "mongodb_db": cls.MONGODB_DB,
            "cors_origins": cls.CORS_ORIGINS,
            "api_prefix": cls.API_PREFIX
        }

# Environment-specific configurations
class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False
    # Add production-specific settings here
    CORS_ORIGINS = ["https://turboinserat.kartenmitwirkung.de"]

# Configuration dictionary
config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig
}

# Get the current environment
ENV = os.getenv("FLASK_ENV", "development")
CurrentConfig = config.get(ENV, config["default"]) 