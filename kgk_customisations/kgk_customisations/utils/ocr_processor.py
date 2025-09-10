#!/usr/bin/env python3

import re
from typing import Dict


def extract_fields(text: str) -> Dict[str, str]:
    """
    Tokenise OCR output into field segments, extract with regex,
    apply inference and override rules for Blue UV, Brown, Type,
    handle mis-ordered COLOR/RESULT, enforce strict validation on
    Result and Color, and support Fancy Yellow override.
    """
    t = re.sub(r"[\r\n]+", " ", text or "").upper()
    t = re.sub(r"\bYELL\s*UU\b", "YELL UV", t)
    t = t.replace("=", "-").replace("||", "")
    t = re.sub(r"\bLICHT\b", "LIGHT", t)

    t = re.sub(r"\bLUE\s*UV\b", "BLUE UV", t)
    t = re.sub(r"\bWU\b", "UV", t)
    t = re.sub(r"\bROWN\b", "BROWN", t)

    fancy_override = "CHECK FANCY" in t

    m0 = re.search(r"\b(RESULT|COLOR|BLUE\s*UV)\b", t)
    if m0:
        t = t[m0.start() :]

    fields = [
        "RESULT",
        "COLOR",
        "BLUE\\s*UV",
        "BROWN",
        "YELL?OW\\s*UV",
        "TYPE",
        "FANCY\\s*YELLOW",
    ]
    parts = re.split(r"\b(" + "|".join(fields) + r")\b", t, flags=re.IGNORECASE)
    raw = {}
    for i in range(1, len(parts) - 1, 2):
        key = parts[i].strip().upper().replace(" ", "_")
        val = parts[i + 1].strip()
        raw.setdefault(key, val)

    patterns = {
        "RESULT": re.compile(r"([!?]{1,4}|[A-Z0-9+\-]{1,2})"),
        "COLOR": re.compile(r"([A-Z]{1,2}[+\-]?|\d+)"),
        "BLUE_UV": re.compile(r"([A-Z]+)\s*\.?([0-9]{1,3})"),
        "BROWN": re.compile(r"([A-Z? ]+)"),
        "YELLOW_UV": re.compile(r"([A-Z! ]+)"),
        "TYPE": re.compile(r"([A-Z][A-Z ]+)"),
        "FANCY_YELLOW": re.compile(r"([A-Z ]+)"),
    }
    clean = {}
    for fld, pat in patterns.items():
        seg = raw.get(fld, "")
        if fld in ("RESULT", "COLOR"):
            seg = seg.replace(" ", "")
        m = pat.search(seg)
        val = m.group(0).strip() if m else ""
        if fld in ("RESULT", "COLOR"):
            val = val.replace("=", "-")
            dm = re.fullmatch(r"(\d)([+\-]?)", val)
            if dm and dm.group(1) in {"6", "1"}:
                val = {"6": "G", "1": "I"}[dm.group(1)] + dm.group(2)
            if fld == "RESULT" and val.isdigit():
                val = "".join("!" if int(d) < 5 else "?" for d in val)
        if fld == "BLUE_UV" and m:
            val = f"{m.group(1)} {m.group(2)}"
        clean[fld] = val

    col_blob = raw.get("COLOR", "")
    if "RESULT" in col_blob.upper():
        blob = col_blob.replace(" ", "")
        toks = re.findall(r"([A-Z0-9!?+\-]+)", blob)
        if len(toks) >= 2:
            first, second = toks[0], toks[1]
            if first in ("!", "1!"):
                first = "!!"
            elif first.isdigit():
                first = "".join("!" if int(d) < 5 else "?" for d in first)
            clean["RESULT"], clean["COLOR"] = first, second
    elif not clean["COLOR"]:
        resseg = raw.get("RESULT", "").replace(" ", "")
        toks = re.findall(r"([A-Z0-9!?+\-]+)", resseg)
        if len(toks) >= 2:
            first, second = toks[0], toks[1]
            if first in ("!", "1!"):
                first = "!!"
            elif first.isdigit():
                first = "".join("!" if int(d) < 5 else "?" for d in first)
            clean["RESULT"], clean["COLOR"] = first, second

    if clean.get("COLOR") == "1":
        clean["COLOR"] = "I"

    buv = raw.get("BLUE_UV", "")
    m_lbl = re.search(r"\b(FAINT|LIGHT|MEDIUM|STRONG|NONE)\b", buv)
    m_dig = re.search(r"\b(\d{1,4})\b", buv)
    if m_lbl:
        lbl = m_lbl.group(1)
        if lbl == "NONE":
            clean["BLUE_UV"] = "NONE 000"
        elif m_dig:
            code = m_dig.group(1)[:3]
            clean["BLUE_UV"] = f"{lbl} {code}"
        else:
            clean["BLUE_UV"] = lbl
    elif m_dig:
        clean["BLUE_UV"] = m_dig.group(1)[:3]

    if not clean["RESULT"] and "STRONG" in buv:
        clean["RESULT"] = "??"
    if not clean["RESULT"] and raw.get("YELL?OW_UV", ""):
        clean["RESULT"] = "!!"

    br = raw.get("BROWN", "").upper()
    if "TLB?" in br:
        clean["BROWN"] = "TLB?"
    elif re.search(r"\bLB\b", br):
        clean["BROWN"] = "LB!"
    elif "NOT" in br and "MEASURED" in br:
        clean["BROWN"] = "NOT MEASURED"
    elif "NONE" in br:
        clean["BROWN"] = "NONE"
    else:
        clean["BROWN"] = ""

    mT = re.search(r"TYPE\s*2[AB]\s+(MIXED|WHITE|BLUE OR GRAY|GRAY|BROWN)", t)
    clean["TYPE"] = mT.group(1) if mT else ""

    if clean.get("RESULT") in ("!", "1!"):
        clean["RESULT"] = "!!"
    allowed_res = {
        "D",
        "DE",
        "E",
        "E-",
        "E+",
        "F",
        "F-",
        "F+",
        "G",
        "G-",
        "G+",
        "H",
        "H-",
        "H+",
        "I",
        "I-",
        "I+",
        "J",
        "J-",
        "J+",
        "K",
        "K-",
        "K+",
        "?",
        "??",
        "???",
    }
    if (
        not re.fullmatch(r"[!?]{1,4}", clean.get("RESULT", ""))
        and clean.get("RESULT", "") not in allowed_res
    ):
        clean["RESULT"] = ""

    c = clean.get("COLOR", "")
    allowed_col = {
        "D",
        "DE",
        "E",
        "E+",
        "E-",
        "F",
        "F+",
        "F-",
        "G",
        "G+",
        "G-",
        "H",
        "H+",
        "H-",
        "I",
        "I+",
        "I-",
        "J",
        "J+",
        "J-",
        "K",
        "K+",
        "K-",
    }
    if re.fullmatch(r"[A-Z]{1,3}[+\-]?", c):
        if c not in allowed_col:
            clean["COLOR"] = ""
    elif not re.fullmatch(r"\d{3}", c):
        clean["COLOR"] = ""

    scale = [chr(x) for x in range(ord("D"), ord("Z") + 1)]
    r0, c0 = clean.get("RESULT", "")[:1], clean.get("COLOR", "")[:1]
    if r0 in scale and c0 in scale and scale.index(c0) < scale.index(r0):
        clean["COLOR"] = clean["RESULT"]

    if not clean["RESULT"]:
        parts = raw.get("RESULT", "").strip().split()
        norm = []
        skip = False
        for i, p in enumerate(parts):
            if skip:
                skip = False
                continue
            if (
                re.fullmatch(r"[A-Z]", p)
                and i + 1 < len(parts)
                and parts[i + 1] in ("+", "-")
            ):
                norm.append(p + parts[i + 1])
                skip = True
            elif re.fullmatch(r"[A-Z][+\-]?", p):
                norm.append(p)
            elif re.fullmatch(r"[!?]{1,4}", p):
                norm.append(p)
        if norm:
            clean["RESULT"] = norm[0]

    if not clean["COLOR"]:
        rseg = raw.get("RESULT", "")
        toks = re.findall(r"([A-Z][+\-]?|[!?]{1,4})", rseg.replace(" ", ""))
        if len(toks) >= 2:
            letter_toks = [tok for tok in toks if re.fullmatch(r"[A-Z][+\-]?", tok)]
            if letter_toks:
                clean["COLOR"] = letter_toks[-1]

    if not clean["COLOR"]:
        rc = raw.get("COLOR", "").upper()
        m = re.findall(r"[DEFGHIJK]", rc)
        if m:
            clean["COLOR"] = m[0]
        elif "1" in rc:
            clean["COLOR"] = "I"

    if not clean["COLOR"]:
        rc = raw.get("COLOR", "").upper().strip()
        for bad, good in {"FS": "F", "CH": "H", "1": "I"}.items():
            if rc == bad:
                clean["COLOR"] = good
                break

    if fancy_override:
        clean["FANCY_YELLOW"] = "CHECK FANCY"

    return {
        "Result": clean.get("RESULT", ""),
        "Color": clean.get("COLOR", ""),
        "Blue UV": clean.get("BLUE_UV", ""),
        "Brown": clean.get("BROWN", ""),
        "Yellow UV": clean.get("YELLOW_UV", ""),
        "Type": clean.get("TYPE", ""),
        "Fancy Yellow": clean.get("FANCY_YELLOW", ""),
    }


def process_ocr_data(text_data: str, existing_data: Dict[str, str] = None) -> Dict[str, str]:
    """
    Process OCR text data and return refined field values.
    
    Args:
        text_data: Raw OCR text data
        existing_data: Dictionary containing existing original values
        
    Returns:
        Dictionary with processed field values
    """
    if existing_data is None:
        existing_data = {}
    
    # Extract fields using the main processing function
    parsed = extract_fields(text_data)
    
    # Apply fallback logic for missing fields using existing data
    existing_brown = str(existing_data.get('brown_original', '')).strip().upper()
    if not parsed["Brown"] and existing_brown == "NOT MEASURED":
        parsed["Brown"] = "NOT MEASURED"

    existing_color = str(existing_data.get('color_original', '')).strip().upper()
    if not parsed["Color"] and re.fullmatch(r"[DEFGHIJK][+\-]?|\d{3}", existing_color):
        parsed["Color"] = existing_color

    existing_type = str(existing_data.get('type_original', '')).strip().upper()
    if not parsed["Type"] and existing_type in {
        "MIXED", "WHITE", "BLUE OR GRAY", "GRAY", "BROWN"
    }:
        parsed["Type"] = existing_type

    # Special handling for Yellow UV
    if not parsed["Yellow UV"] and "YELL UV" in text_data.upper():
        parsed["Yellow UV"] = "YELL UV"
    
    return parsed
