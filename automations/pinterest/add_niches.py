import pandas as pd
from database import get_products_df, save_products_df
import os

CSV_FILE = "data.csv"

def add_niche_products():
    print("Adding high-converting niche products to data.csv...")
    
    new_products = [
        {
            "Product Name": "Clear Acrylic Makeup Organizer, 4 Drawers",
            "Image URL": "https://m.media-amazon.com/images/I/71oD4Hk12rL._AC_SL1500_.jpg",
            "Affiliate Link": "https://amzn.to/example_makeup",
            "Status": "",
            "Category": "beauty",
            "Price": "$24",
            "Tags": "#makeup #vanity #organization #beautyroom #amazonfinds",
            "Description": "Transform your vanity with this aesthetic clear acrylic makeup organizer! Perfect for keeping your lipsticks, palettes, and brushes perfectly displayed. 💄✨",
            "Pin Type": "product",
            "Content Lines": "",
            "SEO Title": "Aesthetic Clear Acrylic Makeup Organizer for Vanity",
            "Pin_Template": "",
            "Board": "Beauty & Vanity"
        },
        {
            "Product Name": "Dimmable Neon Cloud Sign for Bedroom",
            "Image URL": "https://m.media-amazon.com/images/I/61WfQ8g4TML._AC_SL1500_.jpg",
            "Affiliate Link": "https://amzn.to/example_neon",
            "Status": "",
            "Category": "dorm_decor",
            "Price": "$18",
            "Tags": "#roomdecor #aesthetic #neonsign #dormroom #amazonfinds",
            "Description": "This dimmable neon cloud sign instantly changes the vibe of your entire room. The perfect aesthetic lighting for late-night study sessions or movie nights! ☁️✨",
            "Pin Type": "product",
            "Content Lines": "",
            "SEO Title": "Aesthetic Dimmable Neon Cloud Sign for Bedroom",
            "Pin_Template": "",
            "Board": "Aesthetic Room Decor"
        },
        {
            "Product Name": "Stanley Quencher H2.0 Tumbler",
            "Image URL": "https://m.media-amazon.com/images/I/611Z28f23UL._AC_SL1500_.jpg",
            "Affiliate Link": "https://amzn.to/example_stanley",
            "Status": "",
            "Category": "kitchen",
            "Price": "$35",
            "Tags": "#stanleycup #hydration #kitchenhacks #aesthetic #amazonfinds",
            "Description": "The viral Stanley Cup is the ultimate hydration hack. Keeps ice frozen for 2 days and fits perfectly in your car cupholder! 🧊🥤",
            "Pin Type": "product",
            "Content Lines": "",
            "SEO Title": "Viral Stanley Quencher Tumbler - Ultimate Hydration",
            "Pin_Template": "",
            "Board": "Kitchen Gadgets"
        }
    ]

    if not True:
        df = pd.DataFrame(new_products)
    else:
        df = get_products_df()
        if 'Board' not in df.columns:
            df['Board'] = ''
        new_df = pd.DataFrame(new_products)
        df = pd.concat([df, new_df], ignore_index=True)
        
    save_products_df(df)
    print(f"Successfully added {len(new_products)} products to the pipeline!")

if __name__ == "__main__":
    add_niche_products()
