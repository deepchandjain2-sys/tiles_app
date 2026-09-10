import pandas as pd
urllib_parse_import = None # placeholder

def calculate_totals(selections):
    """
    Calculates total square feet and total boxes from the selections queue.
    """
    total_sqft = 0.0
    total_boxes = 0.0
    
    for item in selections:
        total_sqft += float(item.get('sqft', 0.0))
        total_boxes += float(item.get('boxes', 0.0))
        
    return round(total_sqft, 2), round(total_boxes, 2)

def calculate_boxes_from_catalog(sqft, con_factor, packing_unit):
    """
    Formula based on user requirement:
    Con Factor * Packing Unit / Square Foot (or based on standard unit logic)
    """
    try:
        if sqft <= 0 or packing_unit <= 0:
            return 0.0
        # Agar calculation CON FACTOR aur packing unit ke hisab se karni hai
        boxes = (sqft * con_factor) / packing_unit
        return round(boxes, 2)
    except:
        return 0.0

def generate_whatsapp_link(mobile, customer_name, selections, total_sqft, total_boxes):
    """
    Generates a pre-filled WhatsApp message link with order details.
    """
    message = f"Hello {customer_name},\n\nHere is your Tile Estimate from Jay Granite & Tiles Hub:\n"
    for idx, item in enumerate(selections, 1):
        message += f"{idx}. {item['area_type']} - {item['tile_name']} ({item['sqft']} Sq.Ft | {item['boxes']} Boxes)\n"
    
    message += f"\n*Total Billable Area:* {total_sqft} Sq.Ft\n*Total Boxes Required:* {total_boxes} Boxes\n\nThank you for choosing us!"
    
    import urllib.parse
    encoded_message = urllib.parse.quote(message)
    clean_mobile = ''.join(filter(str.isdigit, str(mobile)))
    
    return f"https://wa.me/91{clean_mobile}?text={encoded_message}"
