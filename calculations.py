import math

def calculate_boxes(length, width, sqft_per_box=16.0, wastage=0.0):
    try:
        length = float(length)
        width = float(width)
        sqft_per_box = float(sqft_per_box) if float(sqft_per_box) > 0 else 16.0
        wastage = float(wastage)
    except Exception:
        length, width, sqft_per_box, wastage = 0.0, 0.0, 16.0, 0.0

    # Base Area
    base_sqft = length * width
    
    # Area including Wastage
    total_sqft = base_sqft * (1.0 + (wastage / 100.0))
    
    # Accurate Box Calculation
    boxes_required = round(total_sqft / sqft_per_box, 2)
    
    return round(total_sqft, 2), boxes_required
