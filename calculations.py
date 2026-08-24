import math

def calculate_boxes(sqft, box_sqft):
    try:
        sqft_val = float(sqft)
        box_val = float(box_sqft)
        if box_val <= 0:
            box_val = 16.0
        return math.ceil(sqft_val / box_val)
    except:
        return 0

def calculate_box_sqft(con_factor, packing_unit):
    try:
        cf = float(con_factor)
        pu = float(packing_unit)
        return round(cf * pu, 2)
    except:
        return 16.0
