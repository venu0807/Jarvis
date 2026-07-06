import random
from database import get_products_df, save_products_df

def run_viral_repinner(num_to_repin=5):
    """
    Selects older, already 'pinned' products and recycles them back into the pending queue 
    with a brand new aesthetic template and board, giving them a second wind for algorithm reach.
    """
    print(f"♻️  Starting Viral Repinner... Looking for {num_to_repin} old pins to recycle.")
    
    df = get_products_df().fillna("")
    if df.empty:
        print("  ❌ Database is empty.")
        return
        
    # Find all products that have already been pinned
    pinned_df = df[df["Status"].astype(str).str.strip().str.lower() == "pinned"]
    
    if len(pinned_df) < num_to_repin:
        print(f"  ⚠️ Not enough pinned products yet. Found {len(pinned_df)}. Need more data to repin.")
        return
        
    # Pick a random sample to repin
    sample = pinned_df.sample(n=num_to_repin)
    
    templates = ["auto", "product_overlay", "comparison", "big_number", "review_quote"]
    
    repin_count = 0
    for idx, row in sample.iterrows():
        # 1. Reset status back to pending
        df.at[idx, "Status"] = "pending"
        
        # 2. Assign a completely random new template so it looks like a brand new pin!
        old_template = row.get("Pin_Template", "auto")
        new_template = random.choice([t for t in templates if t != old_template])
        df.at[idx, "Pin_Template"] = new_template
        
        # 3. Add an extra tag to SEO
        df.at[idx, "Tags"] = str(row.get("Tags", "")) + " #trending #musthave"
        
        print(f"  ➡️  Recycling '{row.get('Product Name')[:30]}...' -> New Template: {new_template}")
        repin_count += 1
        
    # Save the database
    if save_products_df(df):
        print(f"✅ Successfully queued {repin_count} old pins for viral reposting!")
    else:
        print("❌ Failed to update database.")

if __name__ == "__main__":
    run_viral_repinner(5)
