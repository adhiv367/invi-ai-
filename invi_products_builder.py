import csv
import json
import re

# ── Step 1: Read CSV, build handle → meta + image ──────────────────────────────
handle_meta  = {}   # handle → product fields
handle_image = {}   # handle → image URL (only on first row)
sku_to_handle = {}  # EVERY variant SKU → handle

with open('products_export_1.csv', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        handle = row.get('Handle', '').strip()
        if not handle:
            continue

        # Image only exists on the first row per product
        if handle not in handle_image:
            handle_image[handle] = row.get('Image Src', '').strip()
            handle_meta[handle] = {
                'title':    row.get('Title', '').strip(),
                'type':     row.get('Type', '').strip(),
                'tags':     row.get('Tags', '').strip(),
                'price':    row.get('Variant Price', '').strip(),
                'fabric':   row.get('Fabric (product.metafields.shopify.fabric)', '').strip(),
                'sizes':    row.get('Size (product.metafields.shopify.size)', '').strip(),
                'sleeve':   row.get('Sleeve length type (product.metafields.shopify.sleeve-length-type)', '').strip(),
                'neckline': row.get('Neckline (product.metafields.shopify.neckline)', '').strip(),
                'care':     row.get('Care instructions (product.metafields.shopify.care-instructions)', '').strip(),
                'status':   row.get('Status', '').strip(),
            }

        # Map EVERY variant SKU → this handle (so any size SKU resolves to product+image)
        sku = row.get('Variant SKU', '').strip().upper()
        if sku:
            sku_to_handle[sku] = handle


# ── Step 2: Build documents list (same format as before) ──────────────────────
documents = []

for handle, p in handle_meta.items():
    if p['status'] != 'active':
        continue

    title = p['title'].split('-PI')[0].strip()
    # Base SKU from title e.g. "Botanical Black Kurthi-PI : ICK00104"
    sku = p['title'].split('PI :')[-1].strip() if 'PI :' in p['title'] else ''

    # Get all variant SKUs that belong to this product
    variant_skus = [s for s, h in sku_to_handle.items() if h == handle]
    all_skus_str = ', '.join(sorted(variant_skus))

    sizes_clean    = p['sizes'].replace(';', ',')    if p['sizes']    else 'XS,S,M,L,XL,2XL,3XL,4XL,5XL'
    sleeve_clean   = p['sleeve'].replace(';', ',')   if p['sleeve']   else 'short,long,sleeveless'
    neckline_clean = p['neckline'].replace(';', ',') if p['neckline'] else 'round,v-neck'
    care_clean     = p['care'].replace(';', ',').replace('-', ' ') if p['care'] else 'hand wash'
    image          = handle_image.get(handle, '')

    doc = f"""Product: {title}
SKU: {sku}
All SKUs: {all_skus_str}
Type: {p['type']}
Price: Rs.{p['price']}
Fabric: {p['fabric'] if p['fabric'] else 'cotton'}
Available Sizes: {sizes_clean}
Sleeve Options: {sleeve_clean}
Neckline Options: {neckline_clean}
Care Instructions: {care_clean}
Tags: {p['tags']}
Image: {image}
Status: Available"""

    documents.append({'id': handle, 'text': doc})

with open('invi_products.json', 'w', encoding='utf-8') as f:
    json.dump(documents, f, ensure_ascii=False, indent=2)

print(f"Done! {len(documents)} products saved to invi_products.json")