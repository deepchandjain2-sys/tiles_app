import math

def calculate_box_sqft(con_factor, packing_unit):
    """
    1 बॉक्स का कुल क्षेत्रफल (Sq.Ft) निकालता है: Con Factor * Packing Unit
    """
    try:
        cf = float(con_factor)
        pu = float(packing_unit)
        return cf * pu
    except Exception:
        return 16.0

def calculate_boxes(sqft, con_factor, packing_unit):
    """
    ग्राहक के कुल क्षेत्रफल और बॉक्स कवरेज के आधार पर आवश्यक बॉक्स (सीलिंग के साथ) निकालता है।
    """
    try:
        sqft_val = float(sqft)
        cf = float(con_factor)
        pu = float(packing_unit)
        
        box_coverage = cf * pu
        if box_coverage <= 0:
            return 0
            
        return math.ceil(sqft_val / box_coverage)
    except Exception:
        return 0
