import math

def calculate_box_sqft(con_factor, packing_unit):
    """
    1 बॉक्स का कुल क्षेत्रफल (Sq.Ft) = Con Factor * Packing Unit
    """
    try:
        cf = float(con_factor)
        pu = float(packing_unit)
        return cf * pu
    except Exception:
        return 9.0

def calculate_boxes(sqft, con_factor, packing_unit):
    """
    सटीक फॉर्मूला: आवश्यक बॉक्स = Sq.Ft / (Con Factor * Packing Unit)
    """
    try:
        sqft_val = float(sqft)
        cf = float(con_factor)
        pu = float(packing_unit)
        
        box_coverage = cf * pu
        if box_coverage <= 0:
            return 0
            
        # सीधे फॉर्मूले के अनुसार सीलिंग (Math.ceil) करके सही बॉक्स निकालना
        return math.ceil(sqft_val / box_coverage)
    except Exception:
        return 0
