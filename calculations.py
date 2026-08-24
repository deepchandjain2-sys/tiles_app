import math

def calculate_boxes(sqft, con_factor, packing_unit):
    """
    सटीक फॉर्मूला: 
    Boxes = math.ceil( Manual Area / (Con Factor * Packing Unit) )
    """
    try:
        sqft_val = float(sqft)
        cf = float(con_factor)
        pu = float(packing_unit)
        
        box_coverage = cf * pu
        if box_coverage <= 0:
            return 0
            
        return math.ceil(sqft_val / box_coverage)
    except:
        return 0

def calculate_box_sqft(con_factor, packing_unit):
    try:
        return float(con_factor) * float(packing_unit)
    except:
        return 16.0
