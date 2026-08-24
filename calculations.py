import math

def calculate_boxes(sqft, box_sqft):
    """
    सटीक बॉक्स गणना: (Total SqFt / Box Coverage) करके 
    math.ceil से ऊपर की तरफ सही बक्से (Whole Boxes) निकालता है।
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
    con_factor और packing_unit को गुणा करके एक बॉक्स की कुल कवरेज (SqFt) निकालता है।
    """
    try:
        cf = float(con_factor)
        pu = float(packing_unit)
        result = cf * pu
        return round(result, 2) if result > 0 else 16.0
    except:
        return 16.0
