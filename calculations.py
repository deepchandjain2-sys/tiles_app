import math

def calculate_boxes(sqft, box_sqft):
    """
    सटीक फॉर्मूला: 
    Required Boxes = math.ceil( Manual Area / (Con Factor * Packing Unit) )
    यहाँ box_sqft असल में (Con Factor * Packing Unit) है।
    """
    try:
        sqft_val = float(sqft)
        box_val = float(box_sqft)
        if box_val <= 0:
            return 0
        return math.ceil(sqft_val / box_val)
    except:
        return 0

def calculate_box_sqft(con_factor, packing_unit):
    """
    Con Factor * Packing Unit से प्रति बॉक्स कवरेज (SqFt) निकालता है।
    """
    try:
        cf = float(con_factor)
        pu = float(packing_unit)
        result = cf * pu
        return round(result, 2) if result > 0 else 16.0
    except:
        return 16.0
