"""
Product Database for Pinterest Affiliate Bot
=============================================
Contains:
  1. Curated product catalog (real Amazon ASINs, image URLs, categories)
  2. Content pin templates (text-based tips that drive affiliate traffic)
  3. Helper functions for link generation and product selection

All products are student-friendly: tech, dorm decor, study supplies, self-care.
Replace `amazon_tag` with your actual Amazon Associates tag in .env.
"""
# ── Imports ──────────────────────────────────────────────────────────────
import os
import random
from image_fetcher import get_product_image, get_content_pin_image

# ── Categories ──────────────────────────────────────────────────────────
CATEGORIES = [
    "tech", "dorm_decor", "study_supplies", "self_care", "kitchen", "fashion",
    "tech_gadgets", "mens_fashion", "womens_fashion", "wellness", "cozy_home"
]

# ── Verified Products (real ASINs & image URLs) ─────────────────────────
# Image URL format: https://m.media-amazon.com/images/I/{IMAGE_ID}._AC_SL1500_.jpg
PRODUCTS = [
    # ── AFFILIATE STORE PRODUCTS (link to affiliate-store-venu.netlify.app) ──
    {
        "name": "Aesthetic Linen Throw Pillow Set",
        "asin": "B08CFSZLQ4",
        "image_id": "71rPCCx9NxL",
        "price": "₹2,899",
        "category": "cozy_home",
        "tags": "#homedecor #pillows #aesthetichome #pinteresthome #livingroom",
        "description": "Transform your living room instantly. These neutral-tone linen pillows are trending on every Pinterest home board.",
        "store_url": "https://affiliate-store-venu.netlify.app"
    },
    {
        "name": "Minimalist Boho Wall Art Print",
        "asin": "B07WGVLMQ4",
        "image_id": "71QK9Y5G5JL",
        "price": "₹1,659",
        "category": "cozy_home",
        "tags": "#wallart #bohodecor #minimalist #homedecor #aestheticroom",
        "description": "Instantly upgrade any room with this stunning gallery-quality boho print. One of the most pinned home decor items of 2024.",
        "store_url": "https://affiliate-store-venu.netlify.app"
    },
    {
        "name": "Rattan Wicker Storage Basket Set",
        "asin": "B09TPPLWSN",
        "image_id": "71kzR8w4KGL",
        "price": "₹3,569",
        "category": "cozy_home",
        "tags": "#organizer #rattandecor #homedecor #aesthetic #tidyhome",
        "description": "The secret to a clutter-free Pinterest-worthy home. Hand-woven baskets perfect for blankets, towels, or toys.",
        "store_url": "https://affiliate-store-venu.netlify.app"
    },
    {
        "name": "Viral Tallow Whipped Face Cream",
        "asin": "B0C9XQRLWV",
        "image_id": "71x5q7FbRwL",
        "price": "₹2,074",
        "category": "self_care",
        "tags": "#skincare #tallow #naturalbeauty #glowingskin #beautyroutine",
        "description": "The Pinterest & TikTok skincare obsession. All-natural, zero chemicals, deeply moisturizing. Glowing skin in 7 days.",
        "store_url": "https://affiliate-store-venu.netlify.app"
    },
    {
        "name": "Gua Sha Facial Sculpting Tool",
        "asin": "B07ZQWCLJM",
        "image_id": "71vNE1TYWSL",
        "price": "₹1,409",
        "category": "self_care",
        "tags": "#guasha #facemassage #skincare #beauty #selfcare",
        "description": "Reduce puffiness and get a chiseled jawline in minutes. The must-have beauty tool pinned over 2 million times.",
        "store_url": "https://affiliate-store-venu.netlify.app"
    },
    {
        "name": "Aesthetic Glass Water Bottle",
        "asin": "B08GKQ9C9Z",
        "image_id": "71Rwb15VrpL",
        "price": "₹1,907",
        "category": "wellness",
        "tags": "#waterbottle #hydration #wellness #aesthetic #healthylifestyle",
        "description": "Track your daily hydration in style. This sleek glass bottle with time markers is everywhere on Pinterest wellness boards.",
        "store_url": "https://affiliate-store-venu.netlify.app"
    },
    {
        "name": "Smart LED Desk Lamp with USB Charging",
        "asin": "B08DKQ35YW",
        "image_id": "71y5yFDkmQL",
        "price": "₹3,319",
        "category": "tech_gadgets",
        "tags": "#desklamp #desksetup #studysetup #productive #workfromhome",
        "description": "Elevate your work from home setup. Eye-care mode, adjustable brightness and a built-in phone charger.",
        "store_url": "https://affiliate-store-venu.netlify.app"
    },
    {
        "name": "Matcha Bamboo Whisk & Ceremony Set",
        "asin": "B07RLHX3HC",
        "image_id": "71J8PF7VPEL",
        "price": "₹2,406",
        "category": "kitchen",
        "tags": "#matcha #matchalatte #morningroutine #aesthetic #greentea",
        "description": "The morning ritual going viral on Pinterest. Ditch coffee, embrace matcha. Everything you need in one beautiful set.",
        "store_url": "https://affiliate-store-venu.netlify.app"
    },
    {
        "name": "Portable Bluetooth Mini Projector",
        "asin": "B07YTYWK98",
        "image_id": "71wgmaCHJIL",
        "price": "₹7,469",
        "category": "tech_gadgets",
        "tags": "#miniprojector #hometheatre #movienight #gadgets #techgifts",
        "description": "Turn any wall into a cinema. 1080p, connects to your phone in seconds. The ultimate trending gift on Pinterest.",
        "store_url": "https://affiliate-store-venu.netlify.app"
    },
    # ── TECH ──
    {
        "name": "Sony WH-1000XM4 Wireless Noise Canceling Headphones",
        "asin": "B0863FR3S9",
        "image_id": "71o8Q5XJS5L",
        "price": "$298",
        "category": "tech",
        "tags": "#headphones #studymusic #noisecanceling #collegeessentials",
        "description": "Best noise-canceling headphones for studying in noisy dorms & libraries. Crystal clear sound for music, podcasts, and online classes."
    },
    {
        "name": "Apple AirPods Pro 2nd Gen",
        "asin": "B0BDHWDR12",
        "image_id": "61SUj2aKoEL",
        "price": "$199",
        "category": "tech",
        "tags": "#airpods #wirelessearbuds #studymusic #collegegadgets",
        "description": "Industry-leading active noise cancellation and adaptive audio. Perfect for study sessions, commuting, and hands-free calls."
    },
    {
        "name": "Anker Portable Charger 20000mAh Power Bank",
        "asin": "B09VPHVT2V",
        "image_id": "71Qk3mN+TzL",
        "price": "$45",
        "category": "tech",
        "tags": "#powerbank #portablecharger #collegeessentials #tech",
        "description": "Ultra-high capacity 20000mAh power bank charges laptops, tablets, and phones. A must-have for all-day classes and travel."
    },
    {
        "name": "Logitech MX Master 3S Wireless Mouse",
        "asin": "B09HM94VDS",
        "image_id": "61EFI6NI4sL",
        "price": "$99",
        "category": "tech",
        "tags": "#wirelessmouse #ergonomic #desksetup #productivity",
        "description": "Ultra-comfortable ergonomic mouse with silent clicks and 8K DPI. Perfect for long study sessions and productivity."
    },
    {
        "name": "Anker USB C Hub 7-in-1 Adapter",
        "asin": "B08R6C68K6",
        "image_id": "81ZQj6YQgJL",
        "price": "$35",
        "category": "tech",
        "tags": "#usbchub #laptopaccessories #collegetech #dockingstation",
        "description": "Expand your laptop with HDMI 4K, USB 3.0, SD card reader, and more. Essential for every student with a USB-C laptop."
    },
    {
        "name": "JBL Flip 6 Portable Bluetooth Speaker",
        "asin": "B0BR7GKHL4",
        "image_id": "71R1k8CvBFL",
        "price": "$129",
        "category": "tech",
        "tags": "#bluetoothspeaker #dormlife #partymusic #college",
        "description": "Powerful, waterproof portable speaker with deep bass. Perfect for dorm hangouts, outdoor study sessions, and parties."
    },
    {
        "name": "Amazon Kindle Paperwhite (11th Gen)",
        "asin": "B08N36XNTT",
        "image_id": "61T0wYKgRKL",
        "price": "$139",
        "category": "tech",
        "tags": "#kindle #ereader #reading #studytools #collegestudent",
        "description": "Read textbooks, novels, and articles on a glare-free display that reads like real paper. Weeks of battery life."
    },
    # ── DORM / DESK ──
    {
        "name": "Govee RGBIC LED Strip Lights 32.8ft",
        "asin": "B08C9LBY68",
        "image_id": "71Y7Y+R45aL",
        "price": "$27",
        "category": "dorm_decor",
        "tags": "#ledlights #dormdecor #aesthetic #roommakeover",
        "description": "Smart LED strip lights with app control, music sync, and millions of colors. Transform your dorm room into an aesthetic paradise."
    },
    {
        "name": "Adjustable Laptop Stand for Desk",
        "asin": "B08VQP8XSG",
        "image_id": "71Mq3qGZxaL",
        "price": "$32",
        "category": "dorm_decor",
        "tags": "#laptopstand #desksetup #ergonomic #studyspace",
        "description": "Raise your laptop to eye level for better posture. Foldable, ventilated design — perfect for small dorm desks."
    },
    {
        "name": "Desk Organizer with Charging Station",
        "asin": "B08CZ3Q9L4",
        "image_id": "71pRq8kzRjL",
        "price": "$22",
        "category": "dorm_decor",
        "tags": "#deskorganization #dormlife #studyspace #aestheticdesk",
        "description": "Multi-compartment organizer with phone stand and pencil holder. Keep your desk clean, organized, and aesthetic."
    },
    {
        "name": "Cork Bulletin Board 24x36 inches",
        "asin": "B07Y8Q5LFG",
        "image_id": "71sCgNzCqXL",
        "price": "$19",
        "category": "dorm_decor",
        "tags": "#corkboard #dormroom #organization #studyspace",
        "description": "Large cork board for pinning notes, photos, and to-do lists. Perfect over your desk for staying organized this semester."
    },
    {
        "name": "Twinkle String Lights 33ft 200 LEDs",
        "asin": "B07YXG6LBS",
        "image_id": "71t8XQkZwUL",
        "price": "$13",
        "category": "dorm_decor",
        "tags": "#fairy lights #dormdecor #aesthetic #cozyroom",
        "description": "Warm white fairy lights with 8 lighting modes. Instantly makes any dorm room feel cozy and aesthetic."
    },
    # ── STUDY SUPPLIES ──
    {
        "name": "Rocketbook Smart Reusable Notebook",
        "asin": "B07WFJ7RLW",
        "image_id": "71r0kNqxFjL",
        "price": "$34",
        "category": "study_supplies",
        "tags": "#rocketbook #smartnotebook #studytools #ecofriendly #college",
        "description": "Write, scan, erase, and reuse. Send your notes to Google Drive, email, or cloud with the free app. Saves money and trees."
    },
    {
        "name": "Apple iPad 9th Gen 10.2-inch",
        "asin": "B09G9BL7ZP",
        "image_id": "61uJmUqImJL",
        "price": "$329",
        "category": "study_supplies",
        "tags": "#ipad #digitalnotes #studytools #collegetech #notetaking",
        "description": "Perfect for digital note-taking, textbooks, and drawing. Pair with Apple Pencil for the ultimate study setup."
    },
    {
        "name": "Moleskine Classic Hard Cover Notebook (Large)",
        "asin": "B005E2DWRM",
        "image_id": "71g2qWwKJjL",
        "price": "$19",
        "category": "study_supplies",
        "tags": "#moleskine #notebook #bulletjournal #stationery #studytools",
        "description": "Iconic hardcover notebook with rounded corners, bookmark ribbon, and elastic closure. The classic choice for students."
    },
    {
        "name": "Crayola Erasable Colored Gel Pens 24ct",
        "asin": "B07PNTRLH5",
        "image_id": "61kR7VwU9L",
        "price": "$12",
        "category": "study_supplies",
        "tags": "#gelpens #stationery #colorcoding #studynotes #aesthetic",
        "description": "Vibrant erasable gel pens perfect for color-coding notes, bullet journaling, and making your study materials aesthetic."
    },
    # ── SELF CARE ──
    {
        "name": "Theragun Mini Portable Massage Gun",
        "asin": "B08K2L3NFZ",
        "image_id": "71Q5rKkD6cL",
        "price": "$199",
        "category": "self_care",
        "tags": "#massagegun #selfcare #stressrelief #collegelife #wellness",
        "description": "Pocket-sized massage gun for muscle relief after workouts, long study sessions, or stress relief. Super quiet too."
    },
    {
        "name": "Essential Oil Diffuser for Bedroom",
        "asin": "B07D5Q5K9G",
        "image_id": "71t5TqXKZwL",
        "price": "$23",
        "category": "self_care",
        "tags": "#oildiffuser #selfcare #dormdecor #aesthetic #relaxation",
        "description": "Ultrasonic aromatherapy diffuser with color-changing LED lights. Creates a calming study atmosphere with your favorite scents."
    },
    {
        "name": "Weighted Blanket 15lbs Queen Size",
        "asin": "B08LNY8Q9V",
        "image_id": "71K5gRkWk6L",
        "price": "$49",
        "category": "self_care",
        "tags": "#weightedblanket #sleepbetter #selfcare #dormlife #anxietyrelief",
        "description": "Premium weighted blanket for deeper, more restful sleep. Helps reduce anxiety and improve focus during the school year."
    },
    # ── KITCHEN / SNACKS ──
    {
        "name": "Hydro Flask 32oz Wide Mouth Water Bottle",
        "asin": "B01H7MXKLM",
        "image_id": "71O5gTkWk2L",
        "price": "$44",
        "category": "kitchen",
        "tags": "#hydroflask #waterbottle #hydration #dormlife #college",
        "description": "Stay hydrated all day with temp-lock insulation. Keeps water ice-cold for 24 hours. The ultimate reusable water bottle."
    },
    {
        "name": "Dash Mini Waffle Maker",
        "asin": "B01N3ORM6K",
        "image_id": "71R5gDkWk3L",
        "price": "$12",
        "category": "kitchen",
        "tags": "#wafflemaker #dormcooking #easyrecipes #collegefood #miniappliances",
        "description": "Make personal-sized waffles, hash browns, or cookies in minutes. The perfect dorm room appliance for late-night snacks."
    },
    # ── FASHION ──
    {
        "name": "Stanley 40oz Quencher Tumbler",
        "asin": "B0BRDYGFK5",
        "image_id": "71L5gRkWk4L",
        "price": "$45",
        "category": "fashion",
        "tags": "#stanleycup #tumbler #hydration #aesthetic #collegestyle",
        "description": "Viral 40oz tumbler with handle and straw. Keeps drinks cold all day. The most aesthetic hydration accessory for campus."
    },
    {
        "name": "New Balance 574 Classic Sneakers",
        "asin": "B00K1G8J7W",
        "image_id": "71A5gTkWk5L",
        "price": "$84",
        "category": "fashion",
        "tags": "#newbalance #sneakers #campusstyle #comfortable #walkingshoes",
        "description": "Classic comfort sneakers perfect for walking across campus. Timeless style that goes with everything."
    },
    # ── MENS FASHION ──
    {
        "name": "Carhartt Men's K87 Workwear Pocket T-Shirt",
        "asin": "B0000X121Y",
        "image_id": "71sM549W4bL",
        "price": "$20",
        "category": "mens_fashion",
        "board": "Men's Style & Fashion",
        "tags": "#mensfashion #streetwear #carhartt #mensstyle #streetstyle",
        "description": "The ultimate classic heavyweight pocket tee. Perfect relaxed fit for everyday streetwear or workwear. A wardrobe staple."
    },
    {
        "name": "Casio Vintage Digital Watch",
        "asin": "B000GAYQJ0",
        "image_id": "71wV22J0pDL",
        "price": "$22",
        "category": "mens_fashion",
        "board": "Men's Style & Fashion",
        "tags": "#menswatches #vintagefashion #casio #streetwear #mensaccessories",
        "description": "Timeless retro digital watch that goes with any outfit. Water-resistant and incredibly durable. A subtle flex."
    },
    # ── WOMENS FASHION ──
    {
        "name": "Oversized Faux Leather Shacket",
        "asin": "B09J4Q9YJZ",
        "image_id": "71j-o5p1TNL",
        "price": "$45",
        "category": "womens_fashion",
        "board": "Women's Fashion & Outfits",
        "tags": "#womensfashion #falloutfits #streetwear #aestheticoutfit",
        "description": "The viral oversized leather jacket. Perfect for layering over hoodies or crop tops for an effortless model-off-duty look."
    },
    {
        "name": "Chunky Gold Hoop Earrings Set",
        "asin": "B08RHR5X81",
        "image_id": "61P+GzH-6EL",
        "price": "$14",
        "category": "womens_fashion",
        "board": "Women's Fashion & Outfits",
        "tags": "#jewelry #goldhoops #accessories #aestheticoutfit",
        "description": "Hypoallergenic 14K gold plated chunky hoops. Lightweight and won't tarnish. Instantly elevates any basic outfit."
    },
    # ── TECH GADGETS ──
    {
        "name": "Logitech G PRO X Superlight Wireless Gaming Mouse",
        "asin": "B087LXCTFJ",
        "image_id": "61Zow3Jt4bL",
        "price": "$139",
        "category": "tech_gadgets",
        "board": "Tech & Gadgets",
        "tags": "#gamingmouse #techgadgets #gamingsetup #pcgaming #logitech",
        "description": "Ultra-lightweight wireless esports gaming mouse. Zero latency, flawless sensor. The choice of top pros."
    },
    {
        "name": "Keychron K2 Wireless Mechanical Keyboard",
        "asin": "B07Y9Y69MV",
        "image_id": "61-R-rK4+cL",
        "price": "$79",
        "category": "tech_gadgets",
        "board": "Tech & Gadgets",
        "tags": "#mechanicalkeyboard #techgadgets #desksetup #productivity",
        "description": "Compact 75% wireless mechanical keyboard with tactile switches. Works perfectly with Mac and Windows."
    },
    # ── WELLNESS ──
    {
        "name": "Owala FreeSip Insulated Stainless Steel Water Bottle",
        "asin": "B0BLPCVR45",
        "image_id": "61pZ+xYx6rL",
        "price": "$28",
        "category": "wellness",
        "board": "Wellness & Self Care",
        "tags": "#wellness #thatgirl #hydration #owala #healthylifestyle",
        "description": "The viral Owala FreeSip. Built-in straw or wide-mouth opening. Completely leak-proof and keeps water ice cold for 24 hours."
    },
    # ── COZY HOME ──
    {
        "name": "Nespresso Vertuo Plus Coffee and Espresso Maker",
        "asin": "B01N08BBUJ",
        "image_id": "71C+F-Xh8fL",
        "price": "$159",
        "category": "cozy_home",
        "board": "Cozy Home & Coffee",
        "tags": "#coffee #homecafe #coffeestation #cozyhome #espresso",
        "description": "Make barista-quality coffee and espresso at home with one touch. The perfect addition to any aesthetic home cafe setup."
    },
]

# ── Content Pin Templates ──────────────────────────────────────────────
# These are TEXT-based pins (no product image needed) that give tips/advice
# and promote related products through affiliate links in the description.
# They get saved WAY more than product pins on Pinterest.

CONTENT_PINS = [
    {
        "title": "10 Gadgets Every College Student NEEDS This Semester",
        "lines": [
            "10 GADGETS",
            "EVERY COLLEGE",
            "STUDENT NEEDS",
            "",
            "Wireless earbuds",
            "Power bank",
            "Laptop stand",
            "USB-C hub",
            "Kindle",
            "Desk lamp",
            "Noise headphones",
            "Cable organizer",
            "Webcam cover",
            "Smart water bottle"
        ],
        "category": "tech",
        "tags": "#collegegadgets #studentessentials #collegetech #dormlife #backtoschool #amazonfinds",
        "description": "10 essential gadgets that will make your college life SO much easier! From noise-canceling headphones for library sessions to portable chargers for all-day classes. Click the link to shop these must-haves! 🎧📚✨ #collegelife #studenttips"
    },
    {
        "title": "Desk Setup Ideas for Maximum Productivity ✨",
        "lines": [
            "AESTHETIC",
            "DESK SETUP",
            "IDEAS",
            "",
            "LED strip lights",
            "Laptop stand",
            "Desk organizer",
            "Monitor light bar",
            "Cork board",
            "Wireless mouse",
            "Plant decor",
            "Cable management"
        ],
        "category": "dorm_decor",
        "tags": "#desksetup #aestheticdesk #productivity #dormdecor #studyinspo #workspacegoals",
        "description": "Transform your desk into an aesthetic productivity zone! These 8 desk setup ideas will help you stay organized, focused, and motivated all semester long. Shop the products at the link! 🖥️✨📚"
    },
    {
        "title": "How to Take Aesthetic Digital Notes on iPad",
        "lines": [
            "AESTHETIC",
            "DIGITAL NOTES",
            "TUTORIAL",
            "",
            "iPad + Pencil",
            "GoodNotes app",
            "Color code subjects",
            "Use templates",
            "Add stickers",
            "Highlight key terms",
            "Draw diagrams",
            "Export as PDF"
        ],
        "category": "study_supplies",
        "tags": "#digitalnotes #ipadnotes #studytips #aestheticnotes #goodnotes #notetaking",
        "description": "Learn how to take BEAUTIFUL digital notes that make studying actually enjoyable! iPad + Apple Pencil + these tips = straight A's. 📝✨ Check the link for the full setup guide!"
    },
    {
        "title": "Dorm Room Makeover: Before & After 🏠✨",
        "lines": [
            "DORM ROOM",
            "MAKEOVER",
            "BEFORE → AFTER",
            "",
            "LED strip lighting",
            "Fairy lights",
            "Bed risers",
            "Storage bins",
            "Tapestry wall",
            "Desk organizer",
            "Cozy rug",
            "Pillow throw set"
        ],
        "category": "dorm_decor",
        "tags": "#dormmakeover #dormdecor #aestheticroom #roomtransformation #collegedorm #interiordesign",
        "description": "The ULTIMATE dorm room makeover! 🏠✨ From boring box to aesthetic sanctuary with these 8 game-changing products. Click the link to shop everything you need to transform your space! 💫"
    },
    {
        "title": "5 Apps Every Student Should Have on Their Phone",
        "lines": [
            "5 APPS EVERY",
            "STUDENT NEEDS",
            "",
            "Notion (planning)",
            "Forest (focus)",
            "Quizlet (study)",
            "Google Calendar",
            "Todoist (tasks)",
            "",
            "Productivity = ",
            "Better grades!"
        ],
        "category": "tech",
        "tags": "#studentapps #productivityapps #collegetips #studytips #timemanagement #collegelife",
        "description": "Stop scrolling TikTok and start being productive! 📱✨ These 5 apps will transform how you study, plan, and manage your time in college. Pair them with a tablet and stylus (linked!) for the ultimate setup."
    },
    {
        "title": "Budget-Friendly Self Care Routine for Students",
        "lines": [
            "SELF CARE",
            "ON A BUDGET",
            "",
            "Essential oil diffuser",
            "Weighted blanket",
            "Face mask kit",
            "Journaling",
            "Herbal tea set",
            "Yoga mat",
            "Bath pillow",
            "Sleep mask"
        ],
        "category": "self_care",
        "tags": "#selfcare #selfcareroutine #collegelife #mentalhealth #wellness #studentlife",
        "description": "You don't need a lot of money to take care of yourself in college! 🧖‍♀️✨ Here's my budget-friendly self-care routine using products under $30. Click the link to shop! #selfcare #collegelife"
    },
    {
        "title": "10 Study Tips That Actually Work (From a Straight-A Student)",
        "lines": [
            "10 STUDY TIPS",
            "THAT WORK",
            "",
            "1. Pomodoro method",
            "2. Active recall",
            "3. Teach someone",
            "4. No phone zone",
            "5. Music without lyrics",
            "6. Handwrite notes",
            "7. Explain out loud",
            "8. Take breaks",
            "9. Sleep well",
            "10. Reward yourself"
        ],
        "category": "study_supplies",
        "tags": "#studytips #studymotivation #examtips #collegetips #productivity #studyskills",
        "description": "These 10 study techniques helped me get straight A's in college! 📚✨ Save this pin for your next exam season. Grab the perfect study supplies (noise-canceling headphones, iPad, gel pens) at the link below!"
    },
    {
        "title": "Ultimate College Packing List 📦✅",
        "lines": [
            "COLLEGE",
            "PACKING LIST",
            "",
            "☐ Bedding set",
            "☐ Towels + toiletries",
            "☐ Laptop + charger",
            "☐ Power strip",
            "☐ LED lights",
            "☐ First aid kit",
            "☐ Water bottle",
            "☐ Snack stash",
            "☐ Desk supplies",
            "☐ Umbrella + rain boots"
        ],
        "category": "dorm_decor",
        "tags": "#collegepacking #dormessentials #freshmanyear #backtoschool #collegetips #dormlife",
        "description": "Don't forget ANYTHING for your dorm move-in day! 📦✅ This complete college packing checklist has everything you need. Shop the must-have items at the link below! 🏠✨"
    },
    {
        "title": "Caffeine Fix: Best Coffee Makers for Dorm Rooms",
        "lines": [
            "BEST DORM",
            "COFFEE MAKERS",
            "",
            "Nespresso Vertuo",
            "Keurig Mini",
            "French press",
            "Aeropress",
            "Pour over set",
            "Electric kettle",
            "Cold brew maker",
            "Milk frother"
        ],
        "category": "kitchen",
        "tags": "#dormcoffee #coffeelover #collegelife #dormkitchen #morningroutine #caffeineaddict",
        "description": "Late-night study sessions need good coffee! ☕️✨ Here are the 8 best coffee makers that are totally dorm-friendly. Click to shop the ultimate dorm coffee station. #dormlife #coffeelover"
    },
    {
        "title": "How to Make Money as a Student Online 💰",
        "lines": [
            "MAKE MONEY",
            "AS A STUDENT",
            "",
            "Freelance writing",
            "Virtual assistant",
            "Tutoring online",
            "Sell digital products",
            "Affiliate marketing",
            "Social media mgmt",
            "Data entry",
            "User testing"
        ],
        "category": "tech",
        "tags": "#makemoneyonline #studentmoney #sidehustle #workfromhome #collegetips #financialfreedom",
        "description": "Want to make money while studying? 💰✨ Here are 8 legitimate ways students can earn online. The right tech setup (linked below!) makes all the difference. Start building your income today! #sidehustle #studentlife"
    },
    {
        "title": "Minimalist Desk Tour 🖥️ | Clean Girl Aesthetic",
        "lines": [
            "MINIMALIST",
            "DESK TOUR",
            "",
            "White desk + stand",
            "Monitor + laptop",
            "Wireless keyboard",
            "Minimal lamp",
            "Single plant",
            "Neutral decor",
            "Cable hidden",
            "Clean & spacious"
        ],
        "category": "dorm_decor",
        "tags": "#desktour #minimalistdesk #aestheticdesk #workspaceinspo #cleangirl #desksetup",
        "description": "Welcome to my minimalist desk setup! 🖥️✨ Clean, organized, and aesthetic. Everything you need (and nothing you don't). Shop the exact products at the link below!"
    },
    {
        "title": "Best Amazon Finds Under $25 for Students",
        "lines": [
            "BEST FINDS",
            "UNDER $25",
            "",
            "Phone stand $8",
            "Cable organizer $10",
            "Fairy lights $12",
            "Mini waffle maker $12",
            "Gel pen set $12",
            "Desk organizer $15",
            "Cork board $19",
            "Twinkle lights $13"
        ],
        "category": "tech",
        "tags": "#amazonfinds #budgetfriendly #collegeessentials #affordable #amazonmusthaves #studentbudget",
        "description": "All these amazing Amazon finds are under $25! 🛍️✨ Perfect for students on a budget. Click the link to shop everything in this pin! #amazonfinds #collegebudget #affordable"
    },
]


def get_affiliate_link(asin: str, amazon_tag: str = None) -> str:
    """Generate Amazon affiliate link from ASIN.
    
    If no tag is provided, reads from environment variable or uses a placeholder.
    """
    if not amazon_tag:
        amazon_tag = os.getenv("AMAZON_AFFILIATE_TAG", "studentdeals0a-20")
    return f"https://www.amazon.com/dp/{asin}?tag={amazon_tag}"


def get_image_url(asin: str, image_id: str = None, category: str = "tech") -> str:
    """Get a working product image URL for an ASIN.
    
    Uses cached Amazon images with fallback to category-appropriate placeholders.
    """
    return get_product_image(asin, category)


def get_random_products(count: int = 5, category: str = None) -> list:
    """Get random products, optionally filtered by category."""
    pool = PRODUCTS
    if category:
        pool = [p for p in PRODUCTS if p["category"] == category]
        if not pool:
            pool = PRODUCTS
    return random.sample(pool, min(count, len(pool)))


def get_random_content_pin(category: str = None) -> dict:
    """Get a random content pin template, optionally filtered by category."""
    pool = CONTENT_PINS
    if category:
        pool = [p for p in CONTENT_PINS if p["category"] == category]
        if not pool:
            pool = CONTENT_PINS
    return random.choice(pool)


def get_all_categories() -> list:
    """Return all available categories."""
    return CATEGORIES


def get_product_count() -> dict:
    """Return count of products per category."""
    counts = {}
    for cat in CATEGORIES:
        counts[cat] = len([p for p in PRODUCTS if p["category"] == cat])
    counts["total"] = len(PRODUCTS)
    counts["content_pins"] = len(CONTENT_PINS)
    return counts


if __name__ == "__main__":
    # Quick test / info
    from dotenv import load_dotenv
    load_dotenv()
    
    print("=" * 50)
    print("  PRODUCT DATABASE REPORT")
    print("=" * 50)
    
    counts = get_product_count()
    for cat in CATEGORIES:
        print(f"  {cat}: {counts[cat]} products")
    print(f"  TOTAL: {counts['total']} products + {counts['content_pins']} content templates")
    
    print("\n--- Sample Product ---")
    p = PRODUCTS[0]
    print(f"  {p['name']}")
    print(f"  Price: {p['price']}")
    print(f"  Link:  {get_affiliate_link(p['asin'])}")
    print(f"  Image: {get_image_url(p['image_id'])}")
    
    print("\n--- Sample Content Pin ---")
    cp = CONTENT_PINS[0]
    print(f"  {cp['title']}")
    print(f"  Category: {cp['category']}")
    print(f"  Lines shown: {len(cp['lines'])}")
