from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="ASIS_", env_file=".env", extra="ignore")

    snap_tolerance_px: float = 10.0
    canny_low: int = 50
    canny_high: int = 150
    hough_threshold: int = 50
    min_line_length: int = 30
    max_line_gap: int = 10
    min_room_area_ratio: float = 0.002
    max_room_area_ratio: float = 0.45

    @property
    def materials_path(self) -> Path:
        root = Path(__file__).resolve().parent.parent
        return root / "data" / "materials.json"


settings = Settings()
