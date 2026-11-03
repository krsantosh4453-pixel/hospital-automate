"""
Medication safety rules used when a prescription is written (clinical/medication_safety.py).

STARTER LIST, PENDING APPROVAL. Engineering compiled these from well-known
contraindications; they are not a complete interaction database. The
hospital's Pharmacy & Therapeutics committee must review, amend and sign them
off (docs/CLINICAL_SAFETY_REVIEW_PACK.md, section 9) before clinical use.
Change them only through code review, and bump RULES_VERSION.

Names are lower-case generic (salt) names as written in India.
"""

RULES_VERSION = "2026-11-03.1"
REVIEW_STATUS = "Starter list: pending review by the Pharmacy & Therapeutics committee"

HIGH = "high"          # blocks the prescription unless the doctor records a reason
MODERATE = "moderate"  # shown as a warning
INFO = "info"          # shown as a note

# An allergy recorded under one of these names also covers every member.
ALLERGY_CLASSES = {
    "penicillin": {"penicillin", "amoxicillin", "ampicillin", "cloxacillin", "piperacillin", "benzathine penicillin"},
    "cephalosporin": {"cephalexin", "cefuroxime", "cefixime", "cefpodoxime", "ceftriaxone", "cefotaxime", "cefoperazone"},
    "sulfonamide": {"sulfamethoxazole", "sulfasalazine", "sulfadiazine"},
    "sulfa": {"sulfamethoxazole", "sulfasalazine", "sulfadiazine"},
    "nsaid": {"aspirin", "ibuprofen", "diclofenac", "naproxen", "mefenamic acid", "ketorolac", "aceclofenac"},
    "aspirin": {"aspirin"},
    "fluoroquinolone": {"ciprofloxacin", "levofloxacin", "ofloxacin", "norfloxacin", "moxifloxacin"},
    "quinolone": {"ciprofloxacin", "levofloxacin", "ofloxacin", "norfloxacin", "moxifloxacin"},
    "macrolide": {"azithromycin", "clarithromycin", "erythromycin"},
}

_NSAIDS = {"aspirin", "ibuprofen", "diclofenac", "naproxen", "mefenamic acid", "ketorolac", "aceclofenac"}

# Each rule: two groups of salts; any salt from one with any salt from the other alerts.
INTERACTIONS = [
    {
        "id": "pde5-nitrate",
        "a": {"sildenafil", "tadalafil", "vardenafil"},
        "b": {"nitroglycerin", "glyceryl trinitrate", "isosorbide mononitrate", "isosorbide dinitrate", "nicorandil"},
        "severity": HIGH,
        "message": "Severe, possibly fatal fall in blood pressure. Do not combine.",
    },
    {
        "id": "anticoagulant-nsaid",
        "a": {"warfarin", "acenocoumarol"},
        "b": _NSAIDS,
        "severity": HIGH,
        "message": "Raised bleeding risk, including gastrointestinal bleeding.",
    },
    {
        "id": "statin-cyp3a4-inhibitor",
        "a": {"simvastatin", "lovastatin"},
        "b": {"clarithromycin", "erythromycin", "itraconazole", "ketoconazole", "ritonavir"},
        "severity": HIGH,
        "message": "Risk of muscle breakdown (rhabdomyolysis). Avoid the combination or pause the statin.",
    },
    {
        "id": "maoi-serotonergic",
        "a": {"linezolid", "phenelzine", "tranylcypromine", "selegiline"},
        "b": {"fluoxetine", "sertraline", "paroxetine", "citalopram", "escitalopram", "venlafaxine", "duloxetine", "tramadol"},
        "severity": HIGH,
        "message": "Risk of serotonin syndrome.",
    },
    {
        "id": "methotrexate-cotrimoxazole",
        "a": {"methotrexate"},
        "b": {"trimethoprim", "sulfamethoxazole"},
        "severity": HIGH,
        "message": "Risk of bone-marrow suppression (methotrexate toxicity).",
    },
    {
        "id": "tizanidine-cyp1a2-inhibitor",
        "a": {"tizanidine"},
        "b": {"ciprofloxacin", "fluvoxamine"},
        "severity": HIGH,
        "message": "Large rise in tizanidine levels: severe low blood pressure and sedation.",
    },
    {
        "id": "clopidogrel-ppi",
        "a": {"clopidogrel"},
        "b": {"omeprazole", "esomeprazole"},
        "severity": MODERATE,
        "message": "May reduce clopidogrel's effect. Pantoprazole is usually preferred.",
    },
    {
        "id": "raas-potassium",
        "a": {"enalapril", "ramipril", "lisinopril", "losartan", "telmisartan", "olmesartan"},
        "b": {"spironolactone", "eplerenone", "potassium chloride"},
        "severity": MODERATE,
        "message": "Risk of high potassium. Monitor potassium and kidney function.",
    },
]


# Common salts recognised in free text so they are not reported as "not identified".
# Recognition only: being listed here raises no alert.
COMMON_SALTS = {
    "paracetamol", "acetaminophen", "cetirizine", "levocetirizine", "fexofenadine", "montelukast",
    "pantoprazole", "rabeprazole", "ranitidine", "famotidine", "domperidone", "ondansetron",
    "metformin", "glimepiride", "gliclazide", "sitagliptin", "vildagliptin", "insulin",
    "amlodipine", "atenolol", "metoprolol", "bisoprolol", "hydrochlorothiazide", "furosemide", "torsemide",
    "atorvastatin", "rosuvastatin", "levothyroxine", "prednisolone", "methylprednisolone", "dexamethasone",
    "salbutamol", "budesonide", "doxycycline", "metronidazole", "nitrofurantoin", "fluconazole",
    "albendazole", "ivermectin", "vitamin d3", "cholecalciferol", "folic acid", "ferrous sulphate",
    "calcium carbonate", "ors", "oral rehydration salts", "zinc", "multivitamin",
}


def known_salts():
    """Every salt the rules mention or COMMON_SALTS lists, for recognising salts written in free text."""
    names = set(COMMON_SALTS)
    for members in ALLERGY_CLASSES.values():
        names |= members
    for rule in INTERACTIONS:
        names |= rule["a"] | rule["b"]
    return names
