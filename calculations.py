import math

def calculate_boxes(sqft, box_sqft):
    """
    यूज़र के दिए गए Area (SqFt) को Box Coverage से भाग देकर 
    math.ceil (ऊपर की तरफ राउंड ऑफ) करके सही बक्से निकालता है।
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
    Con factor x packing unit का सटीक फॉर्मूला।
    """
    try:
        cf = float(con_factor)
        pu = float(packing_unit)
        result = cf * pu
        return round(result, 2) if result > 0 else 16.0
    except:
        return 16.0
