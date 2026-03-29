from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="ASIS_", env_file=".env", extra="ignore")

    # Feature toggles
    use_enhanced_detection: bool = False
    enable_ocr_labels: bool = True

    # Coordinate snapping tolerance
    snap_tolerance_px: float = 12.0
    
    # Canny edge detection thresholds
    canny_low: int = 50
    canny_high: int = 150
    
    # Hough line detection - increased threshold for cleaner lines
    hough_threshold: int = 60
    min_line_length: int = 40  # Increased for cleaner detection
    max_line_gap: int = 8      # Reduced gap for fewer merged lines
    
    # Room detection ratios
    min_room_area_ratio: float = 0.003  # Slightly increased
    max_room_area_ratio: float = 0.40
    
    # Wall filtering
    min_wall_length_px: float = 25.0  # Minimum wall length
    axis_alignment_tolerance: float = 0.15  # 15% tolerance for axis alignment

    @property
    def materials_path(self) -> Path:
        root = Path(__file__).resolve().parent.parent
        return root / "data" / "materials.json"


settings = Settings()
