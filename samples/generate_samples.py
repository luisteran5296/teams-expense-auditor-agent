import os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

OUTPUT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def create_software_invoice():
    """Generates a clean, compliant software invoice image."""
    img = Image.new("RGB", (650, 700), color="#FFFFFF")
    draw = ImageDraw.Draw(img)

    # Header Banner
    draw.rectangle([(0, 0), (650, 90)], fill="#1B365D")
    draw.text((30, 25), "CloudScale Systems Inc.", fill="#FFFFFF")
    draw.text((30, 55), "Enterprise Cloud & SaaS Infrastructure", fill="#A0C4FF")
    draw.text((480, 35), "INVOICE", fill="#FFFFFF")

    # Metadata
    draw.text((30, 115), "Invoice Number: INV-2026-9041", fill="#333333")
    draw.text((30, 140), "Date: 2026-09-04", fill="#333333")
    draw.text((30, 165), "Billed To: Luis Teran (Engineering Dept)", fill="#333333")
    draw.text((450, 115), "Payment: Credit Card *4421", fill="#333333")
    draw.text((450, 140), "Status: PAID IN FULL", fill="#107C41")

    # Table Header
    draw.rectangle([(30, 210), (620, 245)], fill="#F0F4F8")
    draw.text((45, 220), "Description", fill="#1B365D")
    draw.text((380, 220), "Qty", fill="#1B365D")
    draw.text((450, 220), "Rate", fill="#1B365D")
    draw.text((540, 220), "Total", fill="#1B365D")

    # Line Items
    draw.line([(30, 245), (620, 245)], fill="#D0D7DE", width=1)
    draw.text((45, 265), "CloudScale Team Collaboration Plan (Monthly)", fill="#222222")
    draw.text((390, 265), "1", fill="#222222")
    draw.text((445, 265), "$180.00", fill="#222222")
    draw.text((535, 265), "$180.00", fill="#222222")

    draw.text((45, 305), "Developer CI/CD Build Add-on", fill="#222222")
    draw.text((390, 305), "1", fill="#222222")
    draw.text((450, 305), "$60.00", fill="#222222")
    draw.text((540, 305), "$60.00", fill="#222222")

    draw.line([(30, 350), (620, 350)], fill="#D0D7DE", width=1)

    # Totals
    draw.text((420, 380), "Subtotal:", fill="#555555")
    draw.text((535, 380), "$240.00", fill="#222222")
    draw.text((420, 410), "Tax (0%):", fill="#555555")
    draw.text((545, 410), "$0.00", fill="#222222")

    draw.rectangle([(400, 445), (620, 490)], fill="#EBF3FB")
    draw.text((420, 460), "Total Amount:", fill="#1B365D")
    draw.text((530, 460), "$240.00", fill="#1B365D")

    out_path = OUTPUT_DIR / "sample_compliant_software_invoice.png"
    img.save(str(out_path))
    print(f"Created: {out_path}")
    return out_path


def create_dining_receipt():
    """Generates a realistic restaurant receipt with alcohol to trigger policy violation."""
    img = Image.new("RGB", (450, 680), color="#FAFAF7")
    draw = ImageDraw.Draw(img)

    # Receipt Header
    draw.text((120, 25), "THE PRIME STEAKHOUSE & BAR", fill="#111111")
    draw.text((150, 45), "742 Evergreen Terrace", fill="#555555")
    draw.text((160, 65), "Tel: (555) 019-2834", fill="#555555")
    draw.text((140, 95), "RECEIPT #: 489102", fill="#333333")
    draw.text((145, 115), "Date: 2026-09-04 19:42", fill="#333333")

    draw.line([(30, 145), (420, 145)], fill="#CCCCCC", width=1)

    # Items
    items = [
        ("2x Prime Ribeye Steak", "$98.00"),
        ("1x Truffle Fries", "$16.00"),
        ("2x Cabernet Sauvignon Wine", "$34.00"),
        ("1x Chocolate Lava Cake", "$12.00"),
    ]

    y = 165
    for desc, amt in items:
        draw.text((35, y), desc, fill="#222222")
        draw.text((360, y), amt, fill="#222222")
        y += 35

    draw.line([(30, y + 10), (420, y + 10)], fill="#CCCCCC", width=1)
    y += 25

    draw.text((240, y), "Subtotal:", fill="#444444")
    draw.text((360, y), "$160.00", fill="#222222")
    y += 28
    draw.text((240, y), "Tax (8.5%):", fill="#444444")
    draw.text((360, y), "$13.60", fill="#222222")
    y += 28
    draw.text((240, y), "Tip / Gratuity:", fill="#444444")
    draw.text((360, y), "$28.00", fill="#222222")
    y += 35

    draw.line([(220, y), (420, y)], fill="#222222", width=2)
    y += 10
    draw.text((240, y), "TOTAL:", fill="#111111")
    draw.text((350, y), "$201.60", fill="#111111")

    out_path = OUTPUT_DIR / "sample_flagged_dining_receipt.png"
    img.save(str(out_path))
    print(f"Created: {out_path}")
    return out_path


if __name__ == "__main__":
    create_software_invoice()
    create_dining_receipt()
