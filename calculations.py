import math

def calculate_boxes(sqft, box_sqft):
    """
    कुल स्क्वायर फीट और प्रति बॉक्स कवरेज के आधार पर 
    जरूरी बॉक्स की संख्या (ceil करके) कैलकुलेट करता है।
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
    कन्वर्जन फैक्टर और पैकिंग यूनिट से एक बॉक्स की स्क्वायर फीट निकालता है।
    """
    try:
        cf = float(con_factor)
        pu = float(packing_unit)
        return round(cf * pu, 2)
    except:
        return 16.0
