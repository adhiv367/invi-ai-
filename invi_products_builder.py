import csv
import json

products = {}
with open('products_export_1.csv', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        if row['Title']:
            handle = row['Handle']
            title = row['Title'].split('-PI')[0].strip()
            sku = row['Title'].split('PI :')[-1].strip() if 'PI :' in row['Title'] else ''
            products[handle] = {
                'title': title,
                'sku': sku,
                'type': row['Type'],
                'tags': row['Tags'],
                'price': row['Variant Price'],
                'fabric': row.get('Fabric (product.metafields.shopify.fabric)', ''),
                'sizes': row.get('Size (product.metafields.shopify.size)', ''),
                'sleeve': row.get('Sleeve length type (product.metafields.shopify.sleeve-length-type)', ''),
                'neckline': row.get('Neckline (product.metafields.shopify.neckline)', ''),
                'care': row.get('Care instructions (product.metafields.shopify.care-instructions)', ''),
                'image': row.get('Image Src', ''),
                'status': row.get('Status', ''),
            }

documents = []
for handle, p in products.items():
    if p['status'] != 'active':
        continue
    sizes_clean = p['sizes'].replace(';', ',') if p['sizes'] else 'XS,S,M,L,XL,2XL,3XL,4XL,5XL'
    sleeve_clean = p['sleeve'].replace(';', ',') if p['sleeve'] else 'short,long,sleeveless'
    neckline_clean = p['neckline'].replace(';', ',') if p['neckline'] else 'round,v-neck'
    care_clean = p['care'].replace(';', ',').replace('-', ' ') if p['care'] else 'hand wash'

    doc = f"""Product: {p['title']}
SKU: {p['sku']}
Type: {p['type']}
Price: Rs.{p['price']}
Fabric: {p['fabric'] if p['fabric'] else 'cotton'}
Available Sizes: {sizes_clean}
Sleeve Options: {sleeve_clean}
Neckline Options: {neckline_clean}
Care Instructions: {care_clean}
Tags: {p['tags']}
Image: {p['image']}
Status: Available"""

    documents.append({'id': handle, 'text': doc})

with open('invi_products.json', 'w', encoding='utf-8') as f:
    json.dump(documents, f, ensure_ascii=False, indent=2)

print(f"Done! {len(documents)} products saved to invi_products.json")