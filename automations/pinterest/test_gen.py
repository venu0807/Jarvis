from generator import generate_product_pin

image_url = "https://m.media-amazon.com/images/I/61B5hIAmvdL._AC_SX679_.jpg"
generate_product_pin(
    product_name="boAt Rockerz Magnetic Bluetooth Earphones",
    image_url=image_url,
    output_filename="test_pin_hook.png",
    price="$19.99",
    tags="Earphones, Tech, Study"
)
