import math

def calculate_box_sqft(conv_factor, packing_unit):
    # boxes ka kul kshetraphal (Sq.Ft) = Conv Factor * Packing Unit
    try:
        cf = float(conv_factor)
        pu = float(packing_unit)
        return cf * pu
    except Exception:
        return 0.0

def calculate_boxes(sqft, conv_factor, packing_unit):
    # aavshyak boxes = Sq.Ft / (Conv Factor * Packing Unit)
    try:
        sqft_val = float(sqft)
        box_sqft = calculate_box_sqft(conv_factor, packing_unit)
        if box_sqft > 0:
            # math.ceil se boxes hamesha agle poore number par round up honge
            return math.ceil(sqft_val / box_sqft)
        return 0
    except Exception:
        return 0
