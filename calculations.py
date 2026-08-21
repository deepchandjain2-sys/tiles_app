def calculate_boxes(length, width, con_factor, packing_unit, wastage_pct=0.0):
    total_sqft = (float(length) * float(width)) * (1.0 + (float(wastage_pct) / 100.0))
    box_sqft = float(con_factor) * float(packing_unit)
    
    if box_sqft <= 0:
        box_sqft = 16.0
        
    req_boxes = round(total_sqft / box_sqft, 2)
    return round(total_sqft, 2), box_sqft, req_boxes