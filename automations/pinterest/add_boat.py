import pandas as pd

file_path = "D:\\Proposals\\Jarvis\\automations\\pinterest\\data.csv"
df = pd.read_csv(file_path)

new_row = {
    "Product Name": "boAt Rockerz Magnetic Bluetooth Earphones",
    "Image URL": "https://m.media-amazon.com/images/I/61B5hIAmvdL._AC_SX679_.jpg",
    "Affiliate Link": "https://amzn.to/3QRuIPh",
    "Status": "",
    "Category": "tech",
    "Price": "",
    "Tags": "#tech #earphones #boat #audio #amazonfinds",
    "Description": "Looking for the ultimate wireless audio experience? The boAt Rockerz Magnetic Bluetooth Earphones deliver deep bass, long-lasting battery life, and a secure magnetic fit that is perfect for gym workouts, running, or daily commutes. Designed for audiophiles who demand premium sound on a budget. Tap the link to check out the current Amazon deal and upgrade your music setup today! #boAtRockerz #WirelessEarphones #TechGadgets #AudioGear #WorkoutEssentials",
    "Pin Type": "product",
    "Content Lines": "",
    "SEO Title": "boAt Rockerz Magnetic Bluetooth Earphones | Best Wireless Earbuds for Workouts & Bass",
    "Pin_Template": "comparison"
}

df_new = pd.DataFrame([new_row])
df = pd.concat([df_new, df], ignore_index=True)
df.to_csv(file_path, index=False)
print("Added boAt earphones to data.csv!")
