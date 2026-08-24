import math

def calculate_boxes(sqft, box_sqft):
    """
    सटीक बॉक्स कैलकुलेशन: (Total SqFt / Box Coverage) 
    और math.ceil से ऊपर की तरफ सही बक्से निकालना।
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
    नया और सटीक फॉर्मूला: Con Factor को Packing Unit से गुणा करके 
    प्रत्येक टाइल की वास्तविक Box Coverage (SqFt) निकालता है।
    """
    try:
        cf = float(con_factor)
        pu = float(packing_unit)
        result = cf * pu
        return round(result, 2) if result > 0 else 16.0
    except:
        return 16.0
