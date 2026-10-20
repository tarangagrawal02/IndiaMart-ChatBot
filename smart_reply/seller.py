"""Seller profile, fictional demo catalogue and seller-side consistency checks.

Every seller field is optional free text typed by the seller. The engine only
makes a commercial statement when the matching field is filled in. Nothing is
filled in automatically except when the user explicitly loads a fictional
demo profile.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, fields

from smart_reply import rules

MAX_FIELD_CHARS = 120


@dataclass
class SellerProfile:
    business_name: str = ""
    product_name: str = ""
    material_grade: str = ""
    size: str = ""
    wall_thickness: str = ""
    length: str = ""
    available_quantity: str = ""
    unit_price: str = ""
    moq: str = ""
    dispatch_location: str = ""
    delivery_coverage: str = ""
    dispatch_time: str = ""
    gst_freight: str = ""
    payment_terms: str = ""
    certifications: str = ""

    @classmethod
    def from_dict(cls, data: dict | None) -> "SellerProfile":
        data = data or {}
        names = {f.name for f in fields(cls)}
        return cls(**{k: clean_field(v) for k, v in data.items() if k in names})

    def to_dict(self) -> dict:
        return asdict(self)

    def get(self, name: str) -> str:
        return clean_field(getattr(self, name, ""))

    def filled(self) -> dict:
        return {k: v for k, v in self.to_dict().items() if clean_field(v)}

    def is_empty(self) -> bool:
        return not self.filled()


FIELD_LABELS = {
    "business_name": "Business name",
    "product_name": "Product name",
    "material_grade": "Material grade",
    "size": "Diameter or size",
    "wall_thickness": "Wall thickness",
    "length": "Length",
    "available_quantity": "Available quantity",
    "unit_price": "Unit price",
    "moq": "Minimum order quantity",
    "dispatch_location": "Dispatch location",
    "delivery_coverage": "Delivery coverage",
    "dispatch_time": "Estimated dispatch time",
    "gst_freight": "GST and freight",
    "payment_terms": "Payment terms",
    "certifications": "Certifications",
}

FIELD_HELP = {
    "unit_price": "Include the unit, e.g. ₹68 per kg. A rate without a unit is not used in the reply.",
    "available_quantity": "e.g. 300 pieces. Used only to state current stock, never to promise the full order.",
    "moq": "e.g. 100 pieces",
    "dispatch_time": "e.g. 3-5 working days after order confirmation",
    "delivery_coverage": "e.g. Maharashtra and Gujarat, or Pan India",
    "gst_freight": "e.g. GST 18% extra; freight extra at actuals",
}


def clean_field(value) -> str:
    """Single line, trimmed, length-capped text. Seller input is trusted for
    content (the seller is the author) but kept to one tidy line."""
    if value is None:
        return ""
    value = re.sub(r"\s+", " ", str(value)).strip()
    return value[:MAX_FIELD_CHARS]


# --------------------------------------------------------------------------
# Number parsing helpers used for consistency checks
# --------------------------------------------------------------------------

def parse_amount(text: str) -> tuple[float | None, str | None]:
    """First number in text plus a normalised unit if one follows it."""
    m = re.search(r"(\d[\d,]*(?:\.\d+)?)\s*([a-zA-Z]+)?", text or "")
    if not m:
        return None, None
    number = float(m.group(1).replace(",", ""))
    unit = rules.QUANTITY_UNITS.get((m.group(2) or "").lower())
    return number, unit


def units_compatible(a: str | None, b: str | None) -> bool:
    count = {None, "units", "pieces"}
    if a in count and b in count:
        return True
    return a == b


def price_has_unit(price: str) -> bool:
    return bool(re.search(r"(?:/|\bper\b|\bpr\b)\s*\w+|\b(?:each|piece|pc|kg|ton|mt|metre|meter|unit|nos?|bag)\b",
                          price, re.IGNORECASE))


def format_price(price: str) -> str:
    price = clean_field(price)
    if re.match(r"^\d", price):
        price = "₹" + price
    price = re.sub(r"^(?:rs\.?|inr)\s*", "₹", price, flags=re.IGNORECASE)
    return price


def price_numbers(price: str) -> list[float]:
    return [float(n.replace(",", "")) for n in re.findall(r"\d[\d,]*(?:\.\d+)?", price or "")]


def _numbers_with_unit(text: str) -> tuple[float | None, str]:
    m = re.search(r"(\d+(?:\.\d+)?)\s*(inch|in\b|\"|nb|mm|m\b|ft|feet)?", text or "", re.IGNORECASE)
    if not m:
        return None, ""
    unit = (m.group(2) or "").lower().replace('"', "inch")
    unit = {"in": "inch", "feet": "ft"}.get(unit, unit)
    return float(m.group(1)), unit


def specs_differ(buyer_value: str, seller_value: str) -> bool:
    """True only when both values parse to numbers with the same unit and differ."""
    bn, bu = _numbers_with_unit(buyer_value)
    sn, su = _numbers_with_unit(seller_value)
    if bn is None or sn is None:
        return False
    if bu and su and bu != su:
        return False  # different units: can't compare reliably
    return abs(bn - sn) > 1e-9


def coverage_includes(coverage: str, destination: str | None) -> bool | None:
    """True/False when we can tell from the seller's coverage text, None if unclear."""
    if not coverage or not destination:
        return None
    cov = coverage.lower()
    if re.search(r"\b(?:pan[\s-]*india|all\s*(?:over\s*)?india|across\s*india|anywhere\s*in\s*india|all\s*india)\b", cov):
        return True
    dest = destination.lower().replace("pincode ", "")
    if dest in cov:
        return True
    # A state named in coverage that contains the destination city.
    for state, cities in STATE_CITIES.items():
        if state.lower() in cov and destination in cities:
            return True
    return False


STATE_CITIES = {
    "Maharashtra": {"Mumbai", "Pune", "Thane", "Navi Mumbai", "Nashik", "Aurangabad", "Nagpur", "Kolhapur",
                    "Solapur", "Sangli", "Satara", "Ahmednagar", "Jalgaon", "Amravati", "Chakan", "Bhosari",
                    "Pimpri", "Chinchwad", "Talegaon", "Ranjangaon"},
    "Gujarat": {"Ahmedabad", "Surat", "Vadodara", "Rajkot", "Vapi", "Bharuch", "Ankleshwar", "Gandhinagar",
                "Bhavnagar", "Jamnagar", "Morbi"},
    "Karnataka": {"Bengaluru", "Bangalore", "Mysuru", "Mysore", "Mangaluru", "Mangalore", "Hubli", "Belagavi", "Belgaum"},
    "Tamil Nadu": {"Chennai", "Coimbatore", "Madurai", "Tiruchirappalli", "Salem", "Tiruppur", "Hosur", "Sriperumbudur"},
    "Rajasthan": {"Jaipur", "Jodhpur", "Udaipur", "Kota", "Ajmer", "Bikaner", "Bhiwadi", "Neemrana"},
    "Haryana": {"Gurugram", "Gurgaon", "Faridabad", "Panipat", "Sonipat", "Rohtak", "Hisar", "Karnal", "Ambala"},
    "Uttar Pradesh": {"Lucknow", "Kanpur", "Noida", "Ghaziabad", "Meerut", "Agra", "Varanasi", "Prayagraj", "Allahabad"},
    "Madhya Pradesh": {"Indore", "Bhopal", "Gwalior", "Jabalpur", "Pithampur"},
    "Punjab": {"Ludhiana", "Amritsar", "Jalandhar", "Mohali"},
    "Telangana": {"Hyderabad"},
    "West Bengal": {"Kolkata", "Howrah", "Durgapur", "Asansol", "Siliguri"},
}


# --------------------------------------------------------------------------
# Fictional demo catalogue (RAG-lite: keyword retrieval, no embeddings)
# --------------------------------------------------------------------------

DEMO_SELLERS = [
    {
        "id": "shakti",
        "persona": "manufacturer",
        "summary": "Small MS pipe manufacturer, Pune (fictional)",
        "products": [
            {"category": "ms_pipe", "tags": "ms pipe erw 2 inch 50 nb is 1239 class b",
             "profile": {
                 "business_name": "Shakti Tubes (Demo)",
                 "product_name": "MS ERW pipe",
                 "material_grade": "IS 1239 Class B (Medium)",
                 "size": "2 inch (50 NB)",
                 "wall_thickness": "3.6 mm",
                 "length": "6 m",
                 "available_quantity": "300 pieces",
                 "unit_price": "₹68 per kg",
                 "moq": "100 pieces",
                 "dispatch_location": "Bhosari, Pune",
                 "delivery_coverage": "Maharashtra and Gujarat",
                 "dispatch_time": "3-5 working days after order confirmation",
                 "gst_freight": "GST 18% extra; freight extra at actuals",
                 "payment_terms": "50% advance, balance before dispatch",
                 "certifications": "",
             }},
            {"category": "ms_pipe", "tags": "ms pipe erw 1 inch 25 nb class a light",
             "profile": {
                 "business_name": "Shakti Tubes (Demo)",
                 "product_name": "MS ERW pipe",
                 "material_grade": "IS 1239 Class A (Light)",
                 "size": "1 inch (25 NB)",
                 "wall_thickness": "2.6 mm",
                 "length": "6 m",
                 "available_quantity": "800 pieces",
                 "unit_price": "₹66 per kg",
                 "moq": "200 pieces",
                 "dispatch_location": "Bhosari, Pune",
                 "delivery_coverage": "Maharashtra",
                 "dispatch_time": "2-4 working days after order confirmation",
                 "gst_freight": "GST 18% extra; freight extra at actuals",
                 "payment_terms": "Full advance",
                 "certifications": "",
             }},
        ],
    },
    {
        "id": "omkar",
        "persona": "manufacturer",
        "summary": "Fabrication workshop, Chakan (fictional)",
        "products": [
            {"category": "fabrication", "tags": "fabrication shed structure platform railing ms",
             "profile": {
                 "business_name": "Omkar Fabricators (Demo)",
                 "product_name": "MS structural fabrication",
                 "material_grade": "MS (IS 2062 E250)",
                 "dispatch_location": "Chakan, Pune",
                 "delivery_coverage": "Pune and nearby districts",
                 "dispatch_time": "Depends on design; shared after drawing review",
                 "payment_terms": "40% advance, 50% on delivery, 10% after installation",
             }},
        ],
    },
    {
        "id": "jain",
        "persona": "wholesaler",
        "summary": "High-volume fastener wholesaler, Ahmedabad (fictional)",
        "products": [
            {"category": "fasteners", "tags": "bolts hex bolt m12 8.8 zinc nuts washers",
             "profile": {
                 "business_name": "Jain Fastener House (Demo)",
                 "product_name": "Hex bolts",
                 "material_grade": "Grade 8.8",
                 "size": "M8 to M24",
                 "available_quantity": "50000 pieces",
                 "unit_price": "₹9.50 per piece (M12 × 50, zinc plated)",
                 "moq": "1000 pieces",
                 "dispatch_location": "Ahmedabad",
                 "delivery_coverage": "Pan India",
                 "dispatch_time": "1-2 working days after payment",
                 "gst_freight": "GST 18% extra; freight paid by buyer",
                 "payment_terms": "Full advance for new buyers",
                 "certifications": "",
             }},
        ],
    },
    {
        "id": "balaji",
        "persona": "wholesaler",
        "summary": "TMT and steel sections stockist, Nashik (fictional)",
        "products": [
            {"category": "steel_sections", "tags": "tmt bar fe 500d 12 mm sariya rebar angle channel",
             "profile": {
                 "business_name": "Balaji Steel Traders (Demo)",
                 "product_name": "TMT bars",
                 "material_grade": "Fe 500D",
                 "size": "8 mm to 25 mm",
                 "length": "12 m",
                 "available_quantity": "40 tons",
                 "unit_price": "₹56,500 per ton (12 mm)",
                 "moq": "2 tons",
                 "dispatch_location": "Nashik",
                 "delivery_coverage": "Nashik, Pune and Mumbai",
                 "dispatch_time": "Next working day after payment",
                 "gst_freight": "GST 18% extra; freight extra",
                 "payment_terms": "Full advance",
             }},
        ],
    },
    {
        "id": "sai",
        "persona": "digital",
        "summary": "First-generation polymer trader, Vapi (fictional)",
        "products": [
            {"category": "hdpe_granules", "tags": "hdpe granules film grade blow injection virgin recycled",
             "profile": {
                 "business_name": "Sai Polymers (Demo)",
                 "product_name": "HDPE granules",
                 "material_grade": "Film grade, virgin",
                 "available_quantity": "8 tons",
                 "unit_price": "",
                 "moq": "1 ton",
                 "dispatch_location": "Vapi",
                 "delivery_coverage": "Gujarat and Maharashtra",
                 "dispatch_time": "",
                 "gst_freight": "",
                 "payment_terms": "",
             }},
        ],
    },
]

DEMO_BY_ID = {s["id"]: s for s in DEMO_SELLERS}


def retrieve_demo_product(seller_id: str, category_id: str, enquiry_text: str) -> tuple[dict, list[str]]:
    """Pick the demo seller's product that best matches the enquiry.

    Score = category match (3) + overlapping tag tokens (1 each). Returns the
    product entry and the tokens that matched, so the UI can explain the choice.
    """
    seller = DEMO_BY_ID[seller_id]
    words = set(re.findall(r"[a-z0-9.]+", (enquiry_text or "").lower()))
    best, best_score, best_hits = seller["products"][0], -1, []
    for product in seller["products"]:
        tags = product["tags"].split()
        hits = [t for t in tags if t in words]
        score = len(hits) + (3 if product["category"] == category_id else 0)
        if score > best_score:
            best, best_score, best_hits = product, score, hits
    reasons = []
    if best["category"] == category_id:
        reasons.append("same product category")
    if best_hits:
        reasons.append("matching terms: " + ", ".join(dict.fromkeys(best_hits)))
    return best, reasons
