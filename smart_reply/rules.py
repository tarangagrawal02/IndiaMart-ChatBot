"""Configurable extraction rules: product categories, specification patterns and
question wording.

Everything the engine "knows" about a product lives here, so adding a category
means adding a dictionary entry rather than changing code. Patterns are
deliberately conservative: when a value is not matched reliably it is treated
as missing and the buyer is asked, never guessed.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# --------------------------------------------------------------------------
# Shared unit patterns
# --------------------------------------------------------------------------

NUM = r"\d+(?:\.\d+)?"

# Units that describe a count or weight of goods (used for quantity).
QUANTITY_UNITS = {
    "units": "units", "unit": "units",
    "pcs": "pieces", "pc": "pieces", "pieces": "pieces", "piece": "pieces",
    "nos": "pieces", "no": "pieces", "numbers": "pieces", "number": "pieces",
    "lengths": "lengths", "length": "lengths",
    "sets": "sets", "set": "sets",
    "tons": "tons", "ton": "tons", "tonnes": "tons", "tonne": "tons", "mt": "tons",
    "kg": "kg", "kgs": "kg", "kilograms": "kg", "kilogram": "kg",
    "bags": "bags", "bag": "bags",
    "boxes": "boxes", "box": "boxes",
    "quintal": "quintals", "quintals": "quintals",
}

# Units where the item noun follows naturally ("500 MS pipes" not "500 units of").
COUNT_UNITS = {"units", "pieces"}

LENGTH_RE = re.compile(
    rf"(?:length\s*(?:of\s*)?(?:each\s*)?(?:pipe\s*)?[:\-]?\s*)?\b({NUM})\s*"
    r"(m|mtr|mtrs|metre|metres|meter|meters|ft|feet|foot)\b"
    r"(\s*(?:long|length|each|per\s+piece|per\s+pipe))?",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class SpecRule:
    """One specification needed before a seller can quote."""

    id: str
    label: str  # shown in the Missing information panel
    short: str  # used inside sentences ("the MS grade, pipe thickness, ...")
    question: dict  # {"simple": ..., "professional": ..., "hinglish": ...}
    patterns: tuple = ()
    display: str = "{value}"  # how a buyer-supplied value is acknowledged
    seller_field: str | None = None  # seller profile field that can offer a value
    custom: str | None = None  # name of a special-case matcher in extractor


@dataclass(frozen=True)
class Category:
    id: str
    label: str
    # keyword regex -> display noun (plural). Display nouns are fixed strings, so
    # buyer text is never echoed into the reply verbatim.
    strong_keywords: dict
    weak_keywords: dict = field(default_factory=dict)
    specs: tuple = ()
    extra_questions: dict = field(default_factory=dict)  # lang/tone -> list
    price_note: dict = field(default_factory=dict)  # tone -> sentence


def _q(simple: str, professional: str, hinglish: str) -> dict:
    return {"simple": simple, "professional": professional, "hinglish": hinglish}


# --------------------------------------------------------------------------
# Categories
# --------------------------------------------------------------------------

MS_PIPE = Category(
    id="ms_pipe",
    label="MS / ERW pipes",
    strong_keywords={
        r"\bms\s*(?:erw\s*)?pipes?\b": "MS pipes",
        r"\bmild\s*steel\s*pipes?\b": "MS pipes",
        r"\berw\s*pipes?\b": "MS ERW pipes",
        r"\bms\s*tubes?\b": "MS tubes",
        r"\bsteel\s*pipes?\b": "steel pipes",
    },
    weak_keywords={r"\bpipes?\b": "pipes", r"\btubes?\b": "tubes"},
    specs=(
        SpecRule(
            id="size",
            label="Pipe size (diameter)",
            short="pipe size",
            question=_q(
                "Pipe size or diameter (for example 2 inch or 50 NB)",
                "Required pipe size / outer diameter (e.g. 2 inch, 50 NB or 60.3 mm OD)",
                "Pipe ka size ya diameter (jaise 2 inch ya 50 NB)",
            ),
            patterns=(
                rf"\b({NUM}(?:\s*/\s*\d+)?)\s*-?\s*(?:inch(?:es)?|in\b|\"|”)",
                rf"\b({NUM})\s*(?:nb)\b",
                rf"\b({NUM})\s*mm\s*(?:od|nb|dia(?:meter)?)\b",
            ),
            display="{value} diameter",
            seller_field="size",
            custom="pipe_size",
        ),
        SpecRule(
            id="grade",
            label="MS grade or class",
            short="MS grade",
            question=_q(
                "MS grade or class (for example IS 1239 Class A, B or C)",
                "Required MS grade or class (e.g. IS 1239 Class A / B / C, or IS 3589)",
                "MS grade ya class (jaise IS 1239 Class A, B ya C)",
            ),
            patterns=(
                r"\bis\s*[:\-]?\s*(?:1239|3589|1161)\b(?:\s*(?:part\s*\d|class\s*[abc]))?",
                r"\bclass\s*[abc]\b",
                r"\b(?:light|medium|heavy)\s*(?:class|grade|duty)?\b",
                r"\bgrade\s*[:\-]?\s*[a-z]?\d{2,3}\b",
                r"\byst\s*\d{3}\b",
            ),
            seller_field="material_grade",
        ),
        SpecRule(
            id="thickness",
            label="Wall thickness",
            short="pipe thickness",
            question=_q(
                "Wall thickness of the pipe (in mm)",
                "Required wall thickness (in mm) or schedule",
                "Pipe ki wall thickness (mm mein)",
            ),
            patterns=(
                rf"\b{NUM}\s*mm\s*(?:thick(?:ness)?|wall)\b",
                rf"\b(?:thickness|thk|wall)\s*(?:of\s*)?[:\-]?\s*{NUM}\s*mm\b",
                r"\b\d{1,2}\s*(?:swg|gauge)\b",
                r"\bsch(?:edule)?\s*\d{2,3}\b",
            ),
            display="{value} wall thickness",
            seller_field="wall_thickness",
        ),
        SpecRule(
            id="length",
            label="Length of each pipe",
            short="required pipe length",
            question=_q(
                "Length of each pipe (for example 6 m or 20 ft)",
                "Required length per pipe (e.g. 6 m or 20 ft random length)",
                "Har pipe ki length (jaise 6 m ya 20 ft)",
            ),
            display="{value} length",
            seller_field="length",
            custom="length",
        ),
    ),
    extra_questions={
        "simple": [
            "Where will you use these pipes (structure, plumbing or general use)?",
            "Do you need a mill test certificate with the material?",
            "By which date do you need the material?",
        ],
        "professional": [
            "Could you share the intended application (structural, water line or general fabrication)?",
            "Will you require a mill test certificate (MTC) with the supply?",
            "What is your required delivery date?",
        ],
        "hinglish": [
            "Pipes kis kaam ke liye chahiye (structure, plumbing ya general use)?",
            "Kya aapko material ke saath test certificate chahiye?",
            "Material kis date tak chahiye?",
        ],
    },
    price_note={
        "simple": "The price of MS pipe depends on its class, thickness and weight, so these details help us quote correctly.",
        "professional": "As MS pipe pricing depends on the class, wall thickness and weight per metre, these details will help us quote accurately.",
        "hinglish": "MS pipe ka rate uski class, thickness aur weight par depend karta hai, isliye yeh details zaroori hain.",
    },
)

FASTENERS = Category(
    id="fasteners",
    label="Fasteners",
    strong_keywords={
        r"\bhex\s*bolts?\b": "hex bolts",
        r"\banchor\s*bolts?\b": "anchor bolts",
        r"\bbolts?\b": "bolts",
        r"\bnuts?\s*(?:and|&|n)\s*bolts?\b": "nuts and bolts",
        r"\bnuts?\b": "nuts",
        r"\bscrews?\b": "screws",
        r"\bwashers?\b": "washers",
        r"\bstuds?\b": "studs",
        r"\bfasteners?\b": "fasteners",
    },
    specs=(
        SpecRule(
            id="size",
            label="Size (thread diameter × length)",
            short="size",
            question=_q(
                "Size (for example M12 × 50 mm)",
                "Required size - thread diameter and length (e.g. M12 × 50 mm)",
                "Size (jaise M12 × 50 mm)",
            ),
            patterns=(
                r"\bm\s?\d{1,2}(?:\s*[x×*]\s*\d{1,3}(?:\s*mm)?)?\b",
                rf"\b{NUM}\s*mm\s*[x×*]\s*{NUM}\s*(?:mm)?\b",
                r"\b\d+\s*/\s*\d+\s*(?:inch|\")",
            ),
            seller_field="size",
        ),
        SpecRule(
            id="grade",
            label="Grade or material",
            short="grade",
            question=_q(
                "Grade or material (for example 8.8, 10.9 or SS 304)",
                "Required property class or material (e.g. 8.8, 10.9, SS 304)",
                "Grade ya material (jaise 8.8, 10.9 ya SS 304)",
            ),
            patterns=(
                r"\b(?:4\.6|4\.8|5\.6|8\.8|10\.9|12\.9)\b",
                r"\bss\s*-?\s*(?:202|304|316)\b",
                r"\bstainless\s*steel\b",
                r"\bhigh\s*tensile\b",
                r"\bgrade\s*[:\-]?\s*[a-z0-9.]+\b",
            ),
            seller_field="material_grade",
        ),
        SpecRule(
            id="finish",
            label="Finish or coating",
            short="finish",
            question=_q(
                "Finish (for example zinc plated, HDG or black)",
                "Required finish or coating (e.g. zinc plated, hot-dip galvanised, black)",
                "Finish (jaise zinc plated, HDG ya black)",
            ),
            patterns=(
                r"\bzinc(?:\s*plated)?\b",
                r"\b(?:hot[\s-]*dip(?:ped)?\s*)?galvani[sz]ed\b",
                r"\bhdg\b",
                r"\bblack(?:\s*finish)?\b",
                r"\bplain(?:\s*finish)?\b",
                r"\bnickel\b",
            ),
        ),
    ),
    extra_questions={
        "simple": [
            "Which standard do you follow (for example IS 1364 or DIN 931)?",
            "Do you need nuts and washers with the bolts?",
            "By which date do you need the material?",
        ],
        "professional": [
            "Please confirm the applicable standard (e.g. IS 1364, DIN 931/933).",
            "Should matching nuts and washers be included in the quotation?",
            "What is your required delivery date?",
        ],
        "hinglish": [
            "Kaunsa standard chahiye (jaise IS 1364 ya DIN 931)?",
            "Kya bolts ke saath nuts aur washers bhi chahiye?",
            "Material kis date tak chahiye?",
        ],
    },
    price_note={
        "simple": "The price depends on size, grade and finish, so these details help us quote correctly.",
        "professional": "Fastener pricing depends on the size, property class and finish, so these details will help us quote accurately.",
        "hinglish": "Rate size, grade aur finish par depend karta hai, isliye yeh details zaroori hain.",
    },
)

STEEL_SECTIONS = Category(
    id="steel_sections",
    label="Steel sections / TMT bars",
    strong_keywords={
        r"\btmt(?:\s*bars?)?\b": "TMT bars",
        r"\bsariya\b": "TMT bars",
        r"\brebars?\b": "TMT bars",
        r"\b(?:ms\s*)?angles?\b": "MS angles",
        r"\b(?:ms\s*)?channels?\b": "MS channels",
        r"\bismc\b": "MS channels",
        r"\bismb\b|\b[ih][\s-]*beams?\b|\bbeams?\b|\bjoists?\b|\bgirders?\b": "steel beams",
        r"\bflat\s*bars?\b": "MS flat bars",
        r"\bsteel\s*sections?\b|\bstructural\s*steel\b": "steel sections",
    },
    specs=(
        SpecRule(
            id="size",
            label="Size or section",
            short="size",
            question=_q(
                "Size (for example 12 mm TMT, ISMC 100 or 50×50×5 angle)",
                "Required size or section (e.g. 12 mm, ISMC 100, 50 × 50 × 5 mm)",
                "Size (jaise 12 mm TMT, ISMC 100 ya 50×50×5 angle)",
            ),
            patterns=(
                rf"\b{NUM}\s*(?:mm)?\s*[x×*]\s*{NUM}(?:\s*[x×*]\s*{NUM})?\s*(?:mm)?\b",
                r"\b(?:ismb|ismc|isa|isjb)\s*\d+\b",
                r"\b\d{1,2}\s*mm\b",
            ),
            seller_field="size",
        ),
        SpecRule(
            id="grade",
            label="Steel grade",
            short="grade",
            question=_q(
                "Steel grade (for example Fe 500D or E250)",
                "Required steel grade (e.g. Fe 500D, Fe 550D, E250 / IS 2062)",
                "Steel grade (jaise Fe 500D ya E250)",
            ),
            patterns=(
                r"\bfe\s*-?\s*\d{3}\s*d?\b",
                r"\be\s*-?\s*(?:250|350|410)\b",
                r"\bis\s*[:\-]?\s*(?:2062|1786)\b",
            ),
            seller_field="material_grade",
        ),
        SpecRule(
            id="length",
            label="Length per piece",
            short="length",
            question=_q(
                "Length of each piece (for example 6 m or 12 m)",
                "Required length per piece (e.g. 6 m or 12 m)",
                "Har piece ki length (jaise 6 m ya 12 m)",
            ),
            display="{value} length",
            seller_field="length",
            custom="length",
        ),
    ),
    extra_questions={
        "simple": [
            "Do you have a preferred brand?",
            "Do you need a mill test certificate?",
            "By which date do you need the material?",
        ],
        "professional": [
            "Please let us know if you have a brand preference.",
            "Will a mill test certificate (MTC) be required?",
            "What is your required delivery date?",
        ],
        "hinglish": [
            "Koi brand preference hai?",
            "Kya test certificate chahiye?",
            "Material kis date tak chahiye?",
        ],
    },
    price_note={
        "simple": "Steel prices change with grade, size and market rate, so these details help us quote correctly.",
        "professional": "As steel pricing varies with grade, section and the prevailing market rate, these details will help us quote accurately.",
        "hinglish": "Steel ka rate grade, size aur market rate par depend karta hai.",
    },
)

HDPE = Category(
    id="hdpe_granules",
    label="HDPE / plastic granules",
    strong_keywords={
        r"\bhdpe\s*(?:granules?|dana|resin)\b": "HDPE granules",
        r"\bl?ldpe\s*(?:granules?|dana|resin)?\b": "LDPE granules",
        r"\bpp\s*(?:granules?|dana)\b|\bpolypropylene\b": "PP granules",
        r"\bplastic\s*(?:granules?|dana)\b": "plastic granules",
        r"\bhdpe\b(?!\s*pipe)": "HDPE granules",
    },
    weak_keywords={r"\bgranules?\b|\bdana\b|\bresin\b": "granules"},
    specs=(
        SpecRule(
            id="grade",
            label="Grade / application",
            short="grade",
            question=_q(
                "Grade or use (for example film, blow moulding or injection)",
                "Required grade / application (e.g. film, blow moulding, injection, pipe grade)",
                "Grade ya use (jaise film, blow moulding ya injection)",
            ),
            patterns=(
                r"\bfilm(?:\s*grade)?\b",
                r"\bblow\s*mou?ld(?:ing)?(?:\s*grade)?\b",
                r"\binjection(?:\s*mou?ld(?:ing)?)?(?:\s*grade)?\b",
                r"\bpipe\s*grade\b",
                r"\braffia(?:\s*grade)?\b",
                r"\bextrusion(?:\s*grade)?\b",
            ),
            seller_field="material_grade",
        ),
        SpecRule(
            id="material_type",
            label="Virgin or recycled",
            short="virgin or recycled",
            question=_q(
                "Virgin or recycled material",
                "Whether virgin or recycled / reprocessed material is required",
                "Virgin chahiye ya recycled",
            ),
            patterns=(r"\bvirgin\b", r"\brecycled\b", r"\breprocessed\b", r"\bprime\b"),
        ),
        SpecRule(
            id="mfi",
            label="MFI (melt flow index)",
            short="MFI",
            question=_q(
                "MFI or melt flow index you need",
                "Required MFI (melt flow index) range",
                "MFI (melt flow index) kitna chahiye",
            ),
            patterns=(rf"\bmfi\s*[:\-]?\s*{NUM}\b", rf"\bmelt\s*flow(?:\s*index)?\s*[:\-]?\s*{NUM}\b"),
        ),
    ),
    extra_questions={
        "simple": [
            "What packing do you need (for example 25 kg bags)?",
            "Do you need a sample first?",
            "By which date do you need the material?",
        ],
        "professional": [
            "Please confirm the preferred packing (e.g. 25 kg bags).",
            "Would you like a sample before placing the order?",
            "What is your required delivery date?",
        ],
        "hinglish": [
            "Packing kaisi chahiye (jaise 25 kg bags)?",
            "Kya pehle sample chahiye?",
            "Material kis date tak chahiye?",
        ],
    },
    price_note={
        "simple": "The price depends on grade, MFI and virgin or recycled material, so these details help us quote correctly.",
        "professional": "Granule pricing depends on the grade, MFI and whether virgin or recycled material is required.",
        "hinglish": "Rate grade, MFI aur virgin/recycled par depend karta hai.",
    },
)

FABRICATION = Category(
    id="fabrication",
    label="Fabricated products",
    strong_keywords={
        r"\b(?:steel|ms|industrial)\s*sheds?\b|\bpeb\b": "steel shed fabrication",
        r"\bfabricat\w*\b": "fabrication work",
        r"\bmezzanine\b": "mezzanine fabrication",
        r"\brailings?\b": "railing fabrication",
        r"\bstaircases?\b": "staircase fabrication",
        r"\bplatforms?\b": "platform fabrication",
        r"\b(?:ms\s*)?gates?\b|\bgrills?\b": "gate / grill fabrication",
        r"\b(?:steel\s*)?structures?\b|\bframes?\b|\benclosures?\b": "structural fabrication",
    },
    specs=(
        SpecRule(
            id="drawing",
            label="Drawing or design",
            short="drawing",
            question=_q(
                "Drawing, sketch or photo of the design",
                "Drawing or design reference for the job",
                "Drawing, sketch ya design ki photo",
            ),
            patterns=(r"\bdrawings?\b", r"\bdwg\b", r"\bsketch\b", r"\bdesign\s*(?:attached|shared|enclosed)\b", r"\battached\b"),
        ),
        SpecRule(
            id="material",
            label="Material",
            short="material",
            question=_q(
                "Material (for example MS, SS 304 or aluminium)",
                "Required material (e.g. MS, SS 304, aluminium)",
                "Material (jaise MS, SS 304 ya aluminium)",
            ),
            patterns=(r"\bms\b", r"\bmild\s*steel\b", r"\bss\s*\d{0,3}\b", r"\bstainless\b", r"\balumin(?:i)?um\b", r"\bgi\b"),
            seller_field="material_grade",
        ),
        SpecRule(
            id="dimensions",
            label="Dimensions",
            short="dimensions",
            question=_q(
                "Size or dimensions (length × width × height)",
                "Overall dimensions (length × width × height) or area",
                "Size ya dimensions (length × width × height)",
            ),
            patterns=(
                rf"\b{NUM}\s*(?:ft|feet|m|mm)?\s*[x×*]\s*{NUM}\s*(?:ft|feet|m|mm)?\b",
                rf"\b{NUM}\s*(?:sq\.?\s*ft|sqft|square\s*feet|sq\.?\s*m)\b",
            ),
            seller_field="size",
        ),
        SpecRule(
            id="finish",
            label="Finish",
            short="finish",
            question=_q(
                "Finish (for example primer, paint or powder coating)",
                "Required finish (e.g. primer, enamel paint, powder coating, galvanising)",
                "Finish (jaise primer, paint ya powder coating)",
            ),
            patterns=(r"\bpaint(?:ed|ing)?\b", r"\bpowder\s*coat(?:ed|ing)?\b", r"\bgalvani[sz]\w*\b", r"\bprimer\b", r"\bepoxy\b"),
        ),
    ),
    extra_questions={
        "simple": [
            "Do you need installation at site, or supply only?",
            "Can you share the site address for a visit?",
            "By which date do you need the work done?",
        ],
        "professional": [
            "Should the quotation include installation at site, or supply only?",
            "Would a site visit be possible to take measurements?",
            "What is your target completion date?",
        ],
        "hinglish": [
            "Kya site par installation bhi chahiye, ya sirf supply?",
            "Kya site visit ke liye address share kar sakte hain?",
            "Kaam kis date tak chahiye?",
        ],
    },
    price_note={
        "simple": "Fabrication cost depends on the design, material, size and finish, so these details help us quote correctly.",
        "professional": "Fabrication pricing depends on the design, material, dimensions and finish, so these details will help us quote accurately.",
        "hinglish": "Fabrication ka rate design, material, size aur finish par depend karta hai.",
    },
)

GENERIC = Category(
    id="generic",
    label="Unrecognised product",
    strong_keywords={},
    specs=(
        SpecRule(
            id="product",
            label="Product name and specification",
            short="product name and specification",
            question=_q(
                "Product name and full specification",
                "Exact product name and specification required",
                "Product ka naam aur poori specification",
            ),
        ),
        SpecRule(
            id="grade",
            label="Material or grade",
            short="material or grade",
            question=_q(
                "Material or grade",
                "Required material or grade",
                "Material ya grade",
            ),
            seller_field="material_grade",
        ),
        SpecRule(
            id="size",
            label="Size or dimensions",
            short="size",
            question=_q(
                "Size or dimensions",
                "Required size or dimensions",
                "Size ya dimensions",
            ),
            seller_field="size",
        ),
    ),
    extra_questions={
        "simple": ["Where will you use this product?", "By which date do you need the material?"],
        "professional": ["Could you share the intended application?", "What is your required delivery date?"],
        "hinglish": ["Product kis kaam ke liye chahiye?", "Material kis date tak chahiye?"],
    },
    price_note={
        "simple": "These details help us share a correct price.",
        "professional": "These details will help us prepare an accurate quotation.",
        "hinglish": "Yeh details milne par hum sahi rate bata payenge.",
    },
)

CATEGORIES = (MS_PIPE, FASTENERS, STEEL_SECTIONS, HDPE, FABRICATION)
CATEGORY_BY_ID = {c.id: c for c in CATEGORIES + (GENERIC,)}

# Asked when the product type itself is unclear (only weak keywords matched).
PRODUCT_TYPE_QUESTION = _q(
    "Exact product type and material (for example MS pipe or GI pipe)",
    "Exact product type and material required",
    "Exact product type aur material",
)

# --------------------------------------------------------------------------
# Intent, destination and safety patterns
# --------------------------------------------------------------------------

INTENT_PATTERNS = {
    "price": r"\b(?:rates?|price|pricing|prices|quot(?:e|ation)|cost|best\s*price|lowest|kitna|kitne|bhav|daam)\b",
    "delivery": r"\b(?:delivery\s*(?:time|timeline|date|schedule|period)|timeline|lead\s*time|how\s*soon|by\s*when|dispatch\s*time|kab\s*tak|how\s*many\s*days|when\s*can)\b",
    "stock": r"\b(?:in\s*stock|ready\s*stock|stock|availability|available)\b",
    "guarantee": r"\b(?:guarantee[ds]?|guaranteed|assure[ds]?|commit(?:ment)?|promise|must\s*(?:be\s*)?deliver(?:ed)?|confirm\s+delivery\s+(?:by|within|in))\b",
    "urgent": r"\b(?:urgent(?:ly)?|asap|immediate(?:ly)?|today|tomorrow|jaldi|turant)\b",
    "sample": r"\bsamples?\b",
    "catalogue": r"\b(?:catalog(?:ue)?|brochure|price\s*list)\b",
    "payment": r"\b(?:credit|payment\s*terms?|advance|pdc|lc)\b",
}

# Instruction-like text inside a buyer message. These never change engine
# behaviour; detection exists only so the seller can see what was ignored.
INJECTION_PATTERNS = (
    r"\bignore\b.{0,30}\b(?:instructions?|rules?|above|previous|prior|guidelines?)\b",
    r"\bdisregard\b.{0,30}\b(?:instructions?|rules?|above|previous)\b",
    r"\bforget\b.{0,30}\b(?:instructions?|rules?)\b",
    r"\b(?:you\s+are\s+now|act\s+as|pretend\s+(?:to\s+be|you)|system\s*prompt|developer\s*mode|jailbreak)\b",
    r"\b(?:override|bypass)\b.{0,30}\b(?:rules?|validation|safety|filters?)\b",
    r"\b(?:reply|respond|write|say|state|confirm)\s+(?:only\s+)?(?:with|that)\b.{0,60}\b(?:guarantee|in\s*stock|lowest|free|price|discount)",
    r"\bnew\s+instructions?\b",
    r"\bconfirm\s+(?:that\s+)?you\b.{0,40}\b(?:have\s+stock|in\s*stock|lowest|guarantee|free)",
)

HINGLISH_MARKERS = (
    "chahiye", "chaiye", "kitna", "kitne", "bhai", "bhejo", "batao", "bataye",
    "kab tak", "maal", "hai", "kya", "aur", "mein", "milega", "jaldi", "bhav", "dena",
)

DESTINATION_STOPWORDS = {
    "time", "timeline", "date", "schedule", "period", "charges", "charge", "cost",
    "asap", "urgent", "soon", "required", "needed", "need", "days", "day", "weeks",
    "week", "months", "month", "two", "three", "four", "five", "six", "seven", "ten",
    "one", "a", "an", "the", "next", "few", "this", "time.", "your", "our", "my",
    "stock", "bulk", "rate", "price", "and", "with", "within", "advance", "full",
}

INDIAN_CITIES = (
    "Mumbai", "Pune", "Delhi", "New Delhi", "Bengaluru", "Bangalore", "Chennai", "Hyderabad",
    "Kolkata", "Ahmedabad", "Surat", "Vadodara", "Rajkot", "Jaipur", "Lucknow", "Kanpur",
    "Nagpur", "Indore", "Bhopal", "Thane", "Navi Mumbai", "Nashik", "Aurangabad", "Ludhiana",
    "Amritsar", "Jalandhar", "Chandigarh", "Mohali", "Gurugram", "Gurgaon", "Noida",
    "Ghaziabad", "Faridabad", "Meerut", "Agra", "Varanasi", "Prayagraj", "Allahabad", "Patna",
    "Ranchi", "Jamshedpur", "Dhanbad", "Bhubaneswar", "Cuttack", "Raipur", "Bhilai",
    "Visakhapatnam", "Vijayawada", "Guntur", "Coimbatore", "Madurai", "Tiruchirappalli",
    "Salem", "Tiruppur", "Kochi", "Cochin", "Thiruvananthapuram", "Kozhikode", "Mysuru",
    "Mysore", "Mangaluru", "Mangalore", "Hubli", "Belagavi", "Belgaum", "Goa", "Panaji",
    "Kolhapur", "Solapur", "Sangli", "Satara", "Ahmednagar", "Jalgaon", "Amravati",
    "Jodhpur", "Udaipur", "Kota", "Ajmer", "Bikaner", "Gwalior", "Jabalpur", "Dehradun",
    "Haridwar", "Rudrapur", "Guwahati", "Siliguri", "Durgapur", "Asansol", "Howrah",
    "Vapi", "Bharuch", "Ankleshwar", "Gandhinagar", "Bhavnagar", "Jamnagar", "Morbi",
    "Silvassa", "Hosur", "Sriperumbudur", "Baddi", "Panipat", "Sonipat", "Rohtak",
    "Hisar", "Karnal", "Ambala", "Bhiwadi", "Neemrana", "Pithampur", "Chakan", "Bhosari",
    "Pimpri", "Chinchwad", "Talegaon", "Ranjangaon", "Daman", "Srinagar", "Jammu",
)

STATES = (
    "Maharashtra", "Gujarat", "Rajasthan", "Karnataka", "Tamil Nadu", "Kerala", "Telangana",
    "Andhra Pradesh", "Uttar Pradesh", "Madhya Pradesh", "Bihar", "Jharkhand", "Odisha",
    "West Bengal", "Punjab", "Haryana", "Uttarakhand", "Himachal Pradesh", "Assam",
    "Chhattisgarh",
)
