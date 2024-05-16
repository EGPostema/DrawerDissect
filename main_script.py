from resize_drawer import resize_drawers
from crop_trays import crop_trays_from_coordinates
from infer_trays import infer_trays
from infer_beetles import infer_beetles
from resize_trays import resize_trays
from crop_beetles import crop_beetles_from_coordinates

def main():
    API_KEY = "YOUR_API_KEY"
    TRAY_MODEL_ENDPOINT = "og-trayfinder"
    TRAY_VERSION = "v3"
    SPEC_MODEL_ENDPOINT = "beetlefinder"
    SPEC_VERSION = "v7"

    resize_drawers()
    infer_trays('drawers/resized', 'drawers/resized/coordinates', API_KEY, TRAY_MODEL_ENDPOINT, TRAY_VERSION)
    crop_trays_from_coordinates()
    resize_trays()
    infer_beetles('drawers/resized_trays', 'drawers/resized_trays/coordinates', API_KEY, SPEC_MODEL_ENDPOINT, SPEC_VERSION)
    crop_beetles_from_coordinates()

if __name__ == "__main__":
    main()
