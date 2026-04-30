# -*- coding: utf-8 -*-
"""
Update ERP Excel with English names extracted from product images.
Maps album_id -> english_name and updates column C (副标题).
"""

import json
from pathlib import Path

# English names extracted from product images via OCR
# Format: album_id -> english_name
ENGLISH_NAMES_MAPPING = {
    # Louis Vuitton
    "234120090": "Louis Vuitton 26SS LV Checkered Snakes and Ladders Print T-Shirt",
    "234116311": "Louis Vuitton Red Label Letter Embroidered T-Shirt",
    "234116167": "Louis Vuitton Line Equestrian Print T-Shirt",
    "234112398": "Louis Vuitton Dashed Embroidered T-Shirt",
    "234112409": "Louis Vuitton Graffiti Large Logo Print T-Shirt",
    "234112414": "Louis Vuitton Graffiti Large Logo Print T-Shirt",
    "234112418": "Louis Vuitton Monogram Shadow Jacquard Knit T-Shirt",
    "234112426": "Louis Vuitton Full Monogram Jacquard Shorts",
    "234112482": "Louis Vuitton 26SS Woven Letter Embroidered T-Shirt",
    "234112497": "Louis Vuitton Worn Gradient Jacquard Denim Shirt",
    "234112502": "Louis Vuitton Full Print Jacquard Denim Shorts",
    "234113663": "Louis Vuitton 26SS Bone Logo T-Shirt",
    "234113690": "Louis Vuitton 26SS Bone Logo T-Shirt",
    "234114129": "Louis Vuitton 26SS Dashed Triple Flower T-Shirt",
    "234114162": "Louis Vuitton 26SS Dashed Triple Flower T-Shirt",
    "233873051": "Louis Vuitton 26SS Monogram Reversible Hooded Jacket",
    "233873080": "Louis Vuitton 26SS Monogram Reversible Hooded Jacket",
    # Burberry
    "234116658": "Burberry Embroidered Chest Plaid Patch Letter T-Shirt",
    "234116627": "Burberry Embroidered Chest Plaid Patch Letter T-Shirt",
    "234115884": "Burberry 26SS Knight Equestrian Stamp Round Neck T-Shirt",
    "234115841": "Burberry 26SS Knight Equestrian Stamp Round Neck T-Shirt",
    "234114217": "Burberry 26SS Small Equestrian Knight T-Shirt",
    "234114832": "Burberry 26SS Small Equestrian Knight T-Shirt",
    "233872965": "Burberry 26SS Silicone Equestrian Knight Collar Thin Jacket",
    "233872980": "Burberry 26SS Embroidered Equestrian Knight Hooded Thin Jacket",
    "234111621": "Burberry 26SS Functional Style Embroidered Equestrian Knight Collar Jacket",
    "234111639": "Burberry 26SS Functional Style Embroidered Equestrian Knight Collar Jacket",
    "234113833": "Burberry Classic Plaid Shorts",
    "234113863": "Burberry Classic Plaid Shorts",
    "234113879": "Burberry Plaid Knit Shorts",
    "234113887": "Burberry Plaid Knit Shorts",
    "234113896": "Burberry Large Plaid Knit Shorts",
    "234113906": "Burberry Large Plaid Knit Shorts",
    # Loewe
    "234116587": "Loewe 26SS Colorful Logo Embroidered T-Shirt",
    "234116530": "Loewe 26SS Colorful Logo Embroidered T-Shirt",
    "234115319": "Loewe 26SS Shadow Logo Woven Embroidered T-Shirt",
    "234115321": "Loewe 26SS Shadow Logo Woven Embroidered T-Shirt",
    # MIU MIU
    "234116488": "MIU MIU Classic Embroidered Badge Letter T-Shirt",
    "234116464": "MIU MIU Classic Embroidered Badge Letter T-Shirt",
    # GUCCI
    "234116423": "GUCCI Interlocking Small Logo Embroidered T-Shirt",
    "234116406": "GUCCI Interlocking Small Logo Embroidered T-Shirt",
    "234116413": "GUCCI Minimal Letter Embroidered Logo T-Shirt",
    "234116325": "GUCCI Minimal Letter Embroidered Logo T-Shirt",
    "234116347": "GUCCI Minimal Letter Embroidered Logo T-Shirt",
    "234116368": "GUCCI Minimal Letter Embroidered Logo T-Shirt",
    "234114593": "GUCCI Stripe Letter Jacquard Short Sleeve Knit Polo",
    # Moncler
    "234116372": "Moncler Double Logo Embroidered T-Shirt",
    "234112846": "Moncler Large Chest Logo Embroidered T-Shirt",
    "234112852": "Moncler Large Chest Logo Embroidered T-Shirt",
    # Balenciaga
    "234116272": "Balenciaga Blue Circle Print Letter T-Shirt",
    "234116218": "Balenciaga Blue Circle Print Letter T-Shirt",
    "234116097": "Balenciaga 24SS Blurred Cola Print T-Shirt",
    "234116063": "Balenciaga Multi-Label Print T-Shirt",
    "234116048": "Balenciaga Multi-Label Print T-Shirt",
    "234116034": "Balenciaga Front and Back Letter Print T-Shirt",
    "234116013": "Balenciaga Front and Back Letter Print T-Shirt",
    "234115989": "Balenciaga Double B Graffiti Splash Letter T-Shirt",
    "234115967": "Balenciaga Double B Graffiti Splash Letter T-Shirt",
    "234114951": "Balenciaga 26SS 3M Embroidered Manchester United Badge T-Shirt",
    "234114958": "Balenciaga 26SS 3M Embroidered Manchester United Badge T-Shirt",
    "234114964": "Balenciaga 26SS Full BB Monogram Jacquard T-Shirt",
    "234114966": "Balenciaga 26SS Full BB Monogram Jacquard T-Shirt",
    "234114973": "Balenciaga 26SS Full BB Monogram Jacquard T-Shirt",
    "234114979": "Balenciaga Heavy Patch Embroidered T-Shirt",
    # Givenchy
    "234116108": "Givenchy Eye Pattern Print T-Shirt",
    # Celine
    "234116062": "Celine Hand-Drawn Puppy Print T-Shirt",
    # Dior
    "234115995": "Dior Patch Embroidered T-Shirt",
    "234115934": "Dior Patch Embroidered T-Shirt",
    "234115730": "Dior CD Monogram Webbing Drawstring Shorts",
    "234115626": "Dior CD Monogram Webbing Drawstring Shorts",
    "234115680": "Dior CD Monogram Webbing Drawstring Shorts",
    "234115777": "Dior CD Monogram Webbing Drawstring Shorts",
    "234115166": "Dior Year of the Horse Embroidered Pony T-Shirt",
    "234115433": "Dior Curved Letter Logo Print T-Shirt",
    "234115459": "Dior Curved Letter Logo Print T-Shirt",
    # Ami Paris
    "234111824": "Ami Paris 26SS Color-Block Spliced T-Shirt",
    "234111865": "Ami Paris 26SS Color-Block Spliced T-Shirt",
    "234111903": "Ami Paris 26SS Color-Block Spliced T-Shirt",
    # Alexander Wang
    "234112975": "Alexander Wang 26SS Rhinestone Letter T-Shirt",
    "234113026": "Alexander Wang 26SS Red Letter T-Shirt",
    "234113063": "Alexander Wang 26SS Rhinestone Letter T-Shirt",
    "234113102": "Alexander Wang 26SS Red Letter T-Shirt",
    "234113158": "Alexander Wang 26SS Red Letter T-Shirt",
    # PRADA
    "234113521": "PRADA Headphone Letter Pattern Digital Print T-Shirt",
    "234113523": "PRADA Headphone Letter Pattern Digital Print T-Shirt",
    # Off-White
    "234113689": "Off-White 24SS Classic Eye Letter Logo T-Shirt",
    "234113729": "Off-White 20SS Band Portrait Back Spray Arrow Print T-Shirt",
    "234114176": "Off-White Airport Tape Arrow Print T-Shirt",
    "234114185": "Off-White Airport Tape Arrow Print T-Shirt",
    "234115466": "Off-White Blurred Oil Painting Arrow Cotton T-Shirt",
    "234115523": "Off-White Blurred Oil Painting Arrow Cotton T-Shirt",
    # Thom Browne
    "234114410": "Thom Browne Classic Four-Bar Knit Shorts",
    "234114416": "Thom Browne Classic Four-Bar Knit Shorts",
    "234114421": "Thom Browne Water Ripple Waffle Knit T-Shirt",
}


def main():
    """Update ERP Excel with English names in column C."""

    # Load the existing mapping file
    mapping_path = Path("inputs/english_names_mapping.json")
    if mapping_path.exists():
        with open(mapping_path, "r", encoding="utf-8") as f:
            existing_mapping = json.load(f)
    else:
        existing_mapping = {}

    # Update with English names
    for album_id, english_name in ENGLISH_NAMES_MAPPING.items():
        if album_id in existing_mapping:
            existing_mapping[album_id]["english_name"] = english_name
            existing_mapping[album_id]["needs_review"] = False

    # Save updated mapping
    with open(mapping_path, "w", encoding="utf-8") as f:
        json.dump(existing_mapping, f, ensure_ascii=False, indent=2)

    print(f"Updated {len(ENGLISH_NAMES_MAPPING)} English names in mapping file")

    # Load products data
    products_path = Path("inputs/yesterday_products_final.json")
    with open(products_path, "r", encoding="utf-8") as f:
        products = json.load(f)

    # Build album_id -> row_index mapping
    # Each product has 4 rows (1 main + 3 SKU sub-rows)
    album_to_row = {}
    row_idx = 4  # Data starts from row 4 (1-indexed)

    for product in products:
        album_id = str(product.get("album_id", ""))
        if album_id:
            album_to_row[album_id] = row_idx
        row_idx += 4  # Each product occupies 4 rows

    # Create the update data for xlsx_pack
    updates = []
    for album_id, english_name in ENGLISH_NAMES_MAPPING.items():
        if album_id in album_to_row:
            row = album_to_row[album_id]
            updates.append(
                {
                    "sheet": "商品信息",
                    "cell": f"C{row}",  # Column C = 副标题
                    "value": english_name,
                }
            )

    # Save updates to JSON for xlsx_pack to process
    updates_path = Path("inputs/english_names_updates.json")
    with open(updates_path, "w", encoding="utf-8") as f:
        json.dump(updates, f, ensure_ascii=False, indent=2)

    print(f"Created {len(updates)} cell updates for ERP Excel")
    print(f"Updates saved to: {updates_path}")

    # Print summary
    print("\n=== English Names Summary ===")
    brands = {}
    for album_id, name in ENGLISH_NAMES_MAPPING.items():
        brand = name.split()[0] if name else "Unknown"
        brands[brand] = brands.get(brand, 0) + 1

    for brand, count in sorted(brands.items(), key=lambda x: -x[1]):
        print(f"  {brand}: {count} products")


if __name__ == "__main__":
    main()
