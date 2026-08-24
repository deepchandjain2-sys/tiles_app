import math

def calculate_boxes(sqft, box_sqft):
    """
    कुल स्क्वायर फीट को प्रति बॉक्स कवरेज से भाग देकर 
    math.ceil (ऊपर की तरफ राउंड ऑफ) करके सही बक्से निकालता है।
    जैसे: 100 / 16 = 6.25 -> 7 Boxes
    """
    try:
        sqft_val = float(sqft)
        box_val = float(box_sqft)
        if box_val <= 0:
            box_val = 16.0
        return math.ceil(sqft_val / box_val)
    except:
        return 0

def calculate_box_sqft(con_factor, packing_unit):
    """
    कन्वर्जन फैक्टर और पैकिंग यूनिट को गुणा करके एक बॉक्स की कुल कवरेज (SqFt) निकालता है।
    जैसे: 8 sqft per tile * 2 pcs = 16.0 SqFt per box
    """
    try:
        cf = float(con_factor)
        pu = float(packing_unit)
        result = cf * pu
        return round(result, 2) if result > 0 else 16.0
    except:
        return 16.0
