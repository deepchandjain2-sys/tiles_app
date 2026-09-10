import math
import urllib.parse

def calculate_box_sqft(conv_factor, packing_unit):
    try:
        return float(conv_factor) * float(packing_unit)
    except Exception:
        return 0.0

def calculate_boxes(sqft, conv_factor, packing_unit):
    try:
        sqft_val = float(sqft)
        box_sqft = calculate_box_sqft(conv_factor, packing_unit)
        if box_sqft > 0:
            return math.ceil(sqft_val / box_sqft)
        return 0
    except Exception:
        return 0

def calculate_totals(selections_list):
    total_sqft = sum([item.get('sqft', 0.0) for item in selections_list])
    total_boxes = sum([item.get('boxes', 0.0) for item in selections_list])
    return total_sqft, total_boxes

def generate_whatsapp_link(mobile_number, customer_name, selections, total_sqft, total_boxes):
    message = f"*JAY GRANITE & TILES HUB - HIRIYUR*\n"
    message += f"Customer Estimate Summary\n\n"
    message += f"Name: {customer_name}\n"
    message += f"----------------------------------\n"
    
    for item in selections:
        message += f"• Area: {item.get('area_type')} - {item.get('tile_name')}\n"
        message += f"  Coverage: {item.get('sqft')} Sq.Ft | Boxes: {item.get('boxes')}\n"
    
    message += f"----------------------------------\n"
    message += f"*Total Area:* {total_sqft} Sq.Ft\n"
    message += f"*Total Boxes:* {total_boxes}\n\n"
    message += f"Thank you for choosing us!"
    
    encoded_msg = urllib.parse.quote(message)
    wa_url = f"https://wa.me/91{mobile_number}?text={encoded_msg}"
    return wa_url
