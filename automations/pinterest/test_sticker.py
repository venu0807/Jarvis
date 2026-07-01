from image_builder import generate_pinterest_pin
import os

test_url = 'https://m.media-amazon.com/images/I/71axiGLkw1L._AC_SL1500_.jpg'
test_title = 'Dosmix Retro Bluetooth Speaker, Vintage Decor Mini...'
price = '$19.99'
out_dir = '/mnt/c/Users/Venu/.gemini/antigravity-ide/brain/4b852682-1a1a-435a-b1ed-d025b90d2ffe'
out_path = os.path.join(out_dir, 'demo_price_pin.png')

generate_pinterest_pin(test_url, test_title, 'aesthetic_room_decor', out_path, price=price)
print(f'Generated demo at {out_path}')
