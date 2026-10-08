"""Application configuration."""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "SoilDCRA — AI-Driven Soil Degradation & Crop Rotation MVP"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = True

    # Database
    DATABASE_URL: str = "sqlite:///./soildcra.db"

    # Soil health thresholds
    # NOTE: These are rule-based MVP thresholds requiring regional calibration
    # and agricultural expert validation. They are NOT universally validated.
    PH_LOW_MAX: float = 5.5
    PH_HIGH_MIN: float = 7.5
    SOC_LOW_MAX: float = 0.5       # % concentration
    SOC_MODERATE_MAX: float = 1.0
    N_LOW_MAX: float = 0.05        # g/kg equivalent
    N_MODERATE_MAX: float = 0.15
    P_LOW_MAX: float = 10.0        # mg/kg
    P_MODERATE_MAX: float = 25.0
    K_LOW_MAX: float = 100.0       # mg/kg
    K_MODERATE_MAX: float = 200.0
    EC_MODERATE_MIN: float = 2.0   # dS/m — above this = moderate salinity
    EC_HIGH_MIN: float = 4.0       # dS/m — above this = high salinity

    # Soil health score weights (sum to 1.0)
    W_PH: float = 0.20
    W_SOC: float = 0.25
    W_N: float = 0.20
    W_P: float = 0.15
    W_K: float = 0.10
    W_EC: float = 0.10

    # Crop suitability weights (sum to 1.0)
    CS_W_SOIL: float = 0.25
    CS_W_CLIMATE: float = 0.20
    CS_W_WATER: float = 0.20
    CS_W_SEASON: float = 0.15
    CS_W_ROTATION: float = 0.10
    CS_W_ECONOMIC: float = 0.10

    # Rotation penalties / bonuses (0-100 scale)
    SAME_CROP_PENALTY: float = 40.0
    SAME_FAMILY_PENALTY: float = 15.0
    LEGUME_BONUS: float = 20.0

    # Optimization objective weights
    OPT_W_ECONOMIC: float = 0.40
    OPT_W_SOIL: float = 0.30
    OPT_W_DIVERSITY: float = 0.20
    OPT_W_DISEASE: float = 0.10

    # Default planning horizon (seasons)
    DEFAULT_HORIZON: int = 4

    # Scale factor for CP-SAT (scores are floats → multiply before int cast)
    CPSAT_SCALE: int = 100

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
