import pandas as pd
import math
import urllib.parse

def calculate_totals(selections):
    """
    Calculates total square feet and total boxes from selections queue.
    """
    total_sqft = 0.0
    total_boxes = 0.0
    
    for item in selections:
        total_sqft += float(item.get('sqft', 0.0))
        total_boxes += float(item.get('boxes', 0.0))
        
    return round(total_sqft, 2), math.ceil(total_boxes)

def calculate_boxes_dynamic(sqft, con_factor, packing_unit):
    """
    Formula: (Sq.Ft * Con Factor) / Packing Unit, rounded up to next full box.
    """
    try:
        if sqft <= 0 or packing_unit <= 0:
            return 0.0
        boxes = (sqft * float(con_factor)) / float(packing_unit)
        return math.ceil(boxes) # Ceiling to get next full box (e.g. 6.25 -> 7)
    except:
        return 0.0

def generate_whatsapp_link(mobile, customer_name, selections, total_sqft, total_boxes):
    message = f"Hello {customer_name},\n\nHere is your Tile Estimate from Jay Granite & Tiles Hub:\n"
    for idx, item in enumerate(selections, 1):
        message += f"{idx}. {item['area_type']} - {item['tile_name']} ({item['sqft']} Sq.Ft | {item['boxes']} Boxes)\n"
    
    message += f"\n*Total Billable Area:* {total_sqft} Sq.Ft\n*Total Boxes Required:* {total_boxes} Boxes\n\nThank you for choosing us!"
    
    encoded_message = urllib.parse.quote(message)
    clean_mobile = ''.join(filter(str.isdigit, str(mobile)))
    
    return f"https://wa.me/91{clean_mobile}?text={encoded_message}"
