import os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

OUTPUT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def create_hotel_stay_pdf():
    """Generates a compliant hotel stay invoice PDF ($410.70 total, $185/night - under $250 limit)."""
    img = Image.new("RGB", (750, 950), color="#FFFFFF")
    draw = ImageDraw.Draw(img)

    # Top Header Banner
    draw.rectangle([(0, 0), (750, 110)], fill="#1B365D")
    draw.text((40, 30), "THE GRAND HYATT DOWNTOWN", fill="#FFFFFF")
    draw.text((40, 65), "Hospitality & Business Conference Suites | San Francisco, CA", fill="#A5C4E8")
    draw.text((580, 45), "FOLIO INVOICE", fill="#FFFFFF")

    # Guest & Stay Details
    draw.text((40, 140), "Guest Name: Luis Teran (Engineering)", fill="#222222")
    draw.text((40, 170), "Confirmation #: HYATT-882194", fill="#222222")
    draw.text((40, 200), "Room Number: 1408 (Standard King)", fill="#222222")

    draw.text((460, 140), "Check-In:  2026-09-02 (15:00)", fill="#444444")
    draw.text((460, 170), "Check-Out: 2026-09-04 (11:00)", fill="#444444")
    draw.text((460, 200), "Payment: Corporate Amex *1004", fill="#444444")

    # Table Header
    draw.rectangle([(40, 250), (710, 290)], fill="#F1F4F9")
    draw.text((60, 262), "Date", fill="#1B365D")
    draw.text((180, 262), "Description / Folio Item", fill="#1B365D")
    draw.text((520, 262), "Rate", fill="#1B365D")
    draw.text((630, 262), "Amount", fill="#1B365D")

    # Line Items
    items = [
        ("2026-09-02", "Room Charge - Night 1 (Standard King)", "$185.00", "$185.00"),
        ("2026-09-02", "City Tourism & Occupancy Tax (14%)", "$25.90", "$25.90"),
        ("2026-09-03", "Room Charge - Night 2 (Standard King)", "$185.00", "$185.00"),
        ("2026-09-03", "City Tourism & Occupancy Tax (14%)", "$25.90", "$25.90"),
        ("2026-09-04", "High-Speed Business Wi-Fi (Complimentary)", "$0.00", "$0.00"),
        ("2026-09-04", "City Tourism Assessment Fee", "$4.00", "$4.00"),
    ]

    y = 310
    for dt, desc, rate, amt in items:
        draw.text((55, y), dt, fill="#555555")
        draw.text((180, y), desc, fill="#222222")
        draw.text((520, y), rate, fill="#555555")
        draw.text((630, y), amt, fill="#222222")
        draw.line([(40, y + 30), (710, y + 30)], fill="#EAECEF", width=1)
        y += 45

    # Totals Block
    draw.rectangle([(450, 600), (710, 720)], fill="#F8FAFC")
    draw.text((470, 615), "Room Subtotal:", fill="#555555")
    draw.text((630, 615), "$370.00", fill="#222222")

    draw.text((470, 645), "Taxes & Local Fees:", fill="#555555")
    draw.text((630, 645), "$55.80", fill="#222222")

    draw.rectangle([(450, 675), (710, 720)], fill="#1B365D")
    draw.text((470, 688), "TOTAL CHARGED:", fill="#FFFFFF")
    draw.text((615, 688), "$425.80 USD", fill="#FFFFFF")

    # Policy Note
    draw.rectangle([(40, 760), (710, 830)], fill="#EBF9F1", outline="#107C41", width=1)
    draw.text((60, 775), "COMPLIANCE VERIFICATION:", fill="#107C41")
    draw.text((60, 795), "Nightly rate of $185.00 is within corporate policy limit ($250.00/night). No room service/alcohol.", fill="#274E36")

    pdf_path = OUTPUT_DIR / "1_compliant_hotel_stay.pdf"
    png_path = OUTPUT_DIR / "1_compliant_hotel_stay.png"
    img.save(str(pdf_path), "PDF", resolution=100.0)
    img.save(str(png_path), "PNG")
    print(f"Generated: {pdf_path} and {png_path}")
    return pdf_path


def create_flagged_dinner_pdf():
    """Generates an executive dinner receipt with alcohol ($291.40 - exceeds $75 limit + wine/whisky)."""
    img = Image.new("RGB", (650, 920), color="#FAF9F5")
    draw = ImageDraw.Draw(img)

    # Receipt Header
    draw.text((170, 35), "OCEAN PRIME STEAK & SEAFOOD", fill="#1A1A1A")
    draw.text((220, 65), "1331 F Street NW | Washington, DC", fill="#555555")
    draw.text((245, 90), "Table 12 | Guests: 2", fill="#555555")
    draw.text((195, 115), "RECEIPT #: OP-89104 | Server: Marcus", fill="#777777")
    draw.text((215, 140), "Date: 2026-09-04  20:15:33", fill="#777777")

    draw.line([(40, 175), (610, 175)], fill="#D1D5DB", width=2)

    # Line Items
    items = [
        ("2x USDA Prime Bone-In Ribeye", "$118.00"),
        ("1x Jumbo Lump Crab Cakes", "$28.00"),
        ("1x Truffle Macaroni & Cheese", "$16.00"),
        ("2x Glenlivet 12 Scotch Whisky", "$38.00"),  # Restricted!
        ("1x Bottle Silverado Cabernet Sauvignon", "$65.00"),  # Restricted!
        ("1x Warm Butter Cake Dessert", "$14.00"),
    ]

    y = 205
    for desc, amt in items:
        color = "#991B1B" if ("Whisky" in desc or "Cabernet" in desc) else "#1F2937"
        draw.text((50, y), desc, fill=color)
        draw.text((510, y), amt, fill=color)
        draw.line([(40, y + 32), (610, y + 32)], fill="#E5E7EB", width=1)
        y += 45

    # Totals
    draw.text((360, y + 15), "Food Subtotal:", fill="#4B5563")
    draw.text((510, y + 15), "$176.00", fill="#1F2937")

    draw.text((360, y + 45), "Beverage (Alcohol):", fill="#991B1B")
    draw.text((510, y + 45), "$103.00", fill="#991B1B")

    draw.text((360, y + 75), "Sales & Meals Tax (10%):", fill="#4B5563")
    draw.text((510, y + 75), "$27.90", fill="#1F2937")

    draw.text((360, y + 105), "Tip / Gratuity (18%):", fill="#4B5563")
    draw.text((510, y + 105), "$50.22", fill="#1F2937")

    draw.line([(340, y + 140), (610, y + 140)], fill="#111827", width=2)

    draw.text((340, y + 155), "TOTAL CHARGED:", fill="#111827")
    draw.text((490, y + 155), "$357.12 USD", fill="#111827")

    # Policy Warning Box
    draw.rectangle([(40, y + 210), (610, y + 300)], fill="#FEF2F2", outline="#DC2626", width=1)
    draw.text((60, y + 225), "⚠️ AUDIT ALERT FOR POLICY ENGINE:", fill="#DC2626")
    draw.text((60, y + 250), "1. Meal total ($357.12) exceeds the standard $75.00/person limit.", fill="#7F1D1D")
    draw.text((60, y + 270), "2. Contains $103.00 in alcoholic beverages (Wine & Whisky prohibited without VP sign-off).", fill="#7F1D1D")

    pdf_path = OUTPUT_DIR / "2_flagged_executive_dinner_alcohol.pdf"
    png_path = OUTPUT_DIR / "2_flagged_executive_dinner_alcohol.png"
    img.save(str(pdf_path), "PDF", resolution=100.0)
    img.save(str(png_path), "PNG")
    print(f"Generated: {pdf_path} and {png_path}")
    return pdf_path


def create_high_value_it_equipment_pdf():
    """Generates an IT hardware invoice exceeding the $1,000 threshold ($1,440.88 - requires PO)."""
    img = Image.new("RGB", (750, 950), color="#FFFFFF")
    draw = ImageDraw.Draw(img)

    # Header
    draw.rectangle([(0, 0), (750, 100)], fill="#0076CE")  # Dell Blue
    draw.text((40, 25), "DELL ENTERPRISE DIRECT", fill="#FFFFFF")
    draw.text((40, 60), "Commercial Hardware & Workstation Solutions", fill="#D4EAFB")
    draw.text((570, 40), "TAX INVOICE", fill="#FFFFFF")

    # Metadata
    draw.text((40, 130), "Invoice #: DELL-US-2026-99410", fill="#222222")
    draw.text((40, 155), "Date: 2026-09-04", fill="#222222")
    draw.text((40, 180), "Customer: Luis Teran (Engineering Dept)", fill="#222222")

    draw.text((440, 130), "Payment Terms: Net 30 / Card", fill="#555555")
    draw.text((440, 155), "Status: PAID", fill="#107C41")
    draw.text((440, 180), "PO Number: [NOT PROVIDED / EXPENSED DIRECTLY]", fill="#DC2626")

    # Table Header
    draw.rectangle([(40, 220), (710, 260)], fill="#F3F4F6")
    draw.text((60, 232), "Item #", fill="#111827")
    draw.text((140, 232), "Description", fill="#111827")
    draw.text((450, 232), "Qty", fill="#111827")
    draw.text((530, 232), "Unit Price", fill="#111827")
    draw.text((630, 232), "Total", fill="#111827")

    items = [
        ("1", "Dell UltraSharp 32-inch 4K USB-C Hub Monitor (U3223QE)", "1", "$849.00", "$849.00"),
        ("2", "Dell Thunderbolt 4 Dock - 180W Power Delivery", "1", "$320.00", "$320.00"),
        ("3", "Dell Premier Wireless Multi-Device ANC Headset", "1", "$159.00", "$159.00"),
    ]

    y = 280
    for num, desc, qty, unit, total in items:
        draw.text((65, y), num, fill="#6B7280")
        draw.text((140, y), desc, fill="#111827")
        draw.text((460, y), qty, fill="#111827")
        draw.text((530, y), unit, fill="#111827")
        draw.text((630, y), total, fill="#111827")
        draw.line([(40, y + 35), (710, y + 35)], fill="#E5E7EB", width=1)
        y += 50

    # Totals
    draw.rectangle([(450, 480), (710, 600)], fill="#F9FAFB")
    draw.text((470, 495), "Hardware Subtotal:", fill="#6B7280")
    draw.text((630, 495), "$1,328.00", fill="#111827")

    draw.text((470, 525), "Sales Tax (8.5%):", fill="#6B7280")
    draw.text((630, 525), "$112.88", fill="#111827")

    draw.rectangle([(450, 555), (710, 600)], fill="#0076CE")
    draw.text((470, 568), "GRAND TOTAL:", fill="#FFFFFF")
    draw.text((605, 568), "$1,440.88 USD", fill="#FFFFFF")

    # Policy Warning Box
    draw.rectangle([(40, 660), (710, 750)], fill="#FEF2F2", outline="#DC2626", width=1)
    draw.text((60, 675), "🚨 POLICY VIOLATION FOR AUDITOR AGENT:", fill="#DC2626")
    draw.text((60, 700), "• Purchase of $1,440.88 exceeds the $1,000.00 unapproved transaction limit.", fill="#7F1D1D")
    draw.text((60, 720), "• IT hardware requires a formal Purchase Order (PO) and Department VP Sign-Off.", fill="#7F1D1D")

    pdf_path = OUTPUT_DIR / "3_high_value_it_equipment_requires_po.pdf"
    png_path = OUTPUT_DIR / "3_high_value_it_equipment_requires_po.png"
    img.save(str(pdf_path), "PDF", resolution=100.0)
    img.save(str(png_path), "PNG")
    print(f"Generated: {pdf_path} and {png_path}")
    return pdf_path


def create_flight_receipt_pdf():
    """Generates a compliant economy flight receipt ($485.20 - economy class allowed)."""
    img = Image.new("RGB", (750, 950), color="#FFFFFF")
    draw = ImageDraw.Draw(img)

    # Header
    draw.rectangle([(0, 0), (750, 110)], fill="#002244")  # Airline Navy
    draw.text((40, 28), "UNITED AIRLINES E-TICKET RECEIPT", fill="#FFFFFF")
    draw.text((40, 62), "Electronic Passenger Ticket & Baggage Itinerary", fill="#7EB2E6")
    draw.text((580, 45), "TRAVEL FOLIO", fill="#FFFFFF")

    # Passenger info
    draw.text((40, 140), "Passenger: Luis Teran", fill="#222222")
    draw.text((40, 165), "Frequent Flyer: UA-941829", fill="#222222")
    draw.text((40, 190), "Booking Reference (PNR): 7K9L2B", fill="#222222")

    draw.text((440, 140), "Ticket Number: 016-2491048291", fill="#555555")
    draw.text((440, 165), "Issue Date: 2026-09-03", fill="#555555")
    draw.text((440, 190), "Class of Service: Economy (Coach)", fill="#107C41")

    # Flight Segments Table
    draw.rectangle([(40, 235), (710, 275)], fill="#F0F4F8")
    draw.text((60, 248), "Flight", fill="#002244")
    draw.text((160, 248), "Departing", fill="#002244")
    draw.text((340, 248), "Arriving", fill="#002244")
    draw.text((510, 248), "Seat", fill="#002244")
    draw.text((610, 248), "Fare Class", fill="#002244")

    flights = [
        ("UA 1204", "SFO (San Francisco) 08:30", "ORD (Chicago O'Hare) 14:45", "14F", "Economy (W)"),
        ("UA 1892", "ORD (Chicago O'Hare) 17:15", "SFO (San Francisco) 20:10", "16B", "Economy (W)"),
    ]

    y = 295
    for flt, dep, arr, seat, cls in flights:
        draw.text((60, y), flt, fill="#222222")
        draw.text((160, y), dep, fill="#222222")
        draw.text((340, y), arr, fill="#222222")
        draw.text((510, y), seat, fill="#222222")
        draw.text((610, y), cls, fill="#107C41")
        draw.line([(40, y + 30), (710, y + 30)], fill="#EAECEF", width=1)
        y += 45

    # Price Breakdown
    draw.rectangle([(450, 420), (710, 540)], fill="#F8FAFC")
    draw.text((470, 435), "Airfare (Economy):", fill="#555555")
    draw.text((630, 435), "$418.00", fill="#222222")

    draw.text((470, 465), "U.S. Federal Excise Tax:", fill="#555555")
    draw.text((630, 465), "$31.35", fill="#222222")

    draw.text((470, 495), "Airport Security & Facility Fees:", fill="#555555")
    draw.text((630, 495), "$35.85", fill="#222222")

    draw.rectangle([(450, 530), (710, 575)], fill="#002244")
    draw.text((470, 545), "TOTAL PAID:", fill="#FFFFFF")
    draw.text((615, 545), "$485.20 USD", fill="#FFFFFF")

    # Policy Note
    draw.rectangle([(40, 630), (710, 700)], fill="#EBF9F1", outline="#107C41", width=1)
    draw.text((60, 645), "COMPLIANCE STATUS: 100% COMPLIANT", fill="#107C41")
    draw.text((60, 665), "Complies with travel policy: Booked in Standard Economy, domestic business route.", fill="#274E36")

    pdf_path = OUTPUT_DIR / "4_compliant_flight_receipt.pdf"
    png_path = OUTPUT_DIR / "4_compliant_flight_receipt.png"
    img.save(str(pdf_path), "PDF", resolution=100.0)
    img.save(str(png_path), "PNG")
    print(f"Generated: {pdf_path} and {png_path}")
    return pdf_path


if __name__ == "__main__":
    create_hotel_stay_pdf()
    create_flagged_dinner_pdf()
    create_high_value_it_equipment_pdf()
    create_flight_receipt_pdf()
