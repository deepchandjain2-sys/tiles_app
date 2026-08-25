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
        return 9.0  # 12x18 या अन्य के लिए सुरक्षित डिफ़ॉल्ट

def calculate_boxes(sqft, con_factor, packing_unit):
    """
    आवश्यक बॉक्स = math.ceil(कुल स्क्वायर फीट / (Con Factor * Packing Unit))
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
