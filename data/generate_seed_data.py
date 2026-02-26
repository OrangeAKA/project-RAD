"""Seed data generator for the RAD System prototype.

Creates rad_seed_data.db with 18 customer personas, full booking histories,
and 10 incoming call scenarios exercising all four evaluation layers.

Usage:
    from data.generate_seed_data import create_database
    create_database("data/rad_seed_data.db")

    # or standalone
    python data/generate_seed_data.py
"""

import os
import sqlite3
from datetime import datetime, timedelta

TODAY = datetime(2026, 2, 26, 12, 0, 0)

# ── Experience catalog ──────────────────────────────────────────────────────
# (name, category, value, percentile, supplier_type, confirmation_tat)
EXP_CATALOG = {
    "EXP_COL_SKIP":     ("Colosseum Skip-the-Line Tour",  "tours",         89.0,  62, "direct_contract",         "immediate"),
    "EXP_DUBAI_SAFARI": ("Dubai Desert Safari Premium",   "activities",   215.0,  91, "aggregator",              "2hr"),
    "EXP_NYC_HELI":     ("VIP Helicopter Tour NYC",       "activities",   490.0,  97, "direct_contract",         "immediate"),
    "EXP_PARIS_CRUISE": ("Paris Seine River Cruise",      "tours",         72.0,  48, "direct_contract",         "immediate"),
    "EXP_AMS_CANAL":    ("Amsterdam Canal Cruise",        "tours",         55.0,  50, "aggregator",              "2hr"),
    "EXP_BALI_TREK":    ("Bali Sunrise Trek",             "activities",    80.0,  60, "aggregator",              "2hr"),
    "EXP_LISBON_SUNSET":("Lisbon Sunset Sailing",         "tours",         72.0,  48, "last_minute_marketplace", "variable"),
    "EXP_TOKYO_TEAMLAB":("Tokyo Teamlab Borderless",      "attractions",   45.0,  52, "direct_contract",         "immediate"),
    "EXP_LONDON_FOOD":  ("London Food Tour",              "food_and_drink", 95.0, 70, "direct_contract",         "immediate"),
    "EXP_LOUVRE":       ("Louvre Museum Priority Access",  "attractions",   65.0,  55, "direct_contract",         "immediate"),
    "EXP_BCN_GOTHIC":   ("Barcelona Gothic Quarter Walk", "tours",         35.0,  18, "direct_contract",         "immediate"),
    "EXP_ROME_COL_01":  ("Rome Colosseum Guided Tour",    "tours",         52.0,  50, "aggregator",              "2hr"),
    "EXP_LONDON_EYE":   ("London Eye Standard Entry",     "attractions",   40.0,  40, "direct_contract",         "immediate"),
    "EXP_NYC_BROADWAY":  ("NYC Broadway Show Tickets",    "shows",        130.0,  85, "direct_contract",         "immediate"),
    "EXP_BERLIN_WALL":  ("Berlin Wall Walking Tour",      "tours",         28.0,  15, "direct_contract",         "immediate"),
    "EXP_SG_NIGHT":     ("Singapore Night Safari",        "activities",    65.0,  58, "aggregator",              "2hr"),
    "EXP_ROME_FOOD":    ("Rome Food Tour",                "food_and_drink", 60.0, 50, "aggregator",              "2hr"),
    "EXP_PRG_NIGHT":    ("Prague Old Town Night Walk",    "tours",         38.0,  35, "aggregator",              "2hr"),
}

ALL_EXP_IDS = list(EXP_CATALOG.keys())
HIGH_VALUE_IDS = ["EXP_NYC_HELI", "EXP_DUBAI_SAFARI", "EXP_NYC_BROADWAY"]


def _ts(dt):
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def _bk(bid, cid, eid, bd, ca, *,
         reason=None, req_at=None, status=None,
         cw=None, ptype="cancelable", prate=None,
         ss=False, qr=None,
         co=True, ro=False, cs="auto", notes=None):
    """Build a 23-element booking tuple."""
    nm, cat, val, pct, sup, tat = EXP_CATALOG[eid]
    if cs == "auto":
        if sup == "last_minute_marketplace":
            cs_v = None
        elif tat == "immediate":
            cs_v = _ts(ca + timedelta(minutes=5))
        else:
            cs_v = _ts(ca + timedelta(hours=1))
    elif cs is None:
        cs_v = None
    else:
        cs_v = _ts(cs)
    qv = 1 if qr is True else (0 if qr is False else None)
    rts = _ts(req_at) if req_at else None
    cwv = 1 if cw else (0 if cw is not None else None)
    return (
        bid, cid, eid, nm, cat, val, pct, sup, tat, cs_v,
        1 if co else 0, 1 if ro else 0, qv,
        _ts(bd), _ts(ca), rts, reason, cwv, ptype, prate,
        1 if ss else 0, status, notes,
    )


def _generics(cid, acct, count, start=1, emails=True, eids=None):
    """Generate count completed bookings with no refund."""
    rows = []
    if count <= 0:
        return rows, start
    ids = eids or ALL_EXP_IDS
    span = max((TODAY - acct).days - 30, count)
    gap = max(span // count, 1)
    for i in range(count):
        eid = ids[(start + i - 1) % len(ids)]
        ca = acct + timedelta(days=gap * (i + 1))
        bd = ca + timedelta(days=7)
        if bd > TODAY:
            bd = TODAY - timedelta(days=count - i)
            ca = bd - timedelta(days=7)
        s = start + i
        rows.append(_bk(
            f"{cid}_B{s:03d}", cid, eid, bd, ca,
            qr=True if s % 3 != 0 else None,
            co=emails, ro=emails and s % 2 == 0,
        ))
    return rows, start + count


def _build_all():
    """Build all customer profiles, bookings, and calls."""
    bookings = []
    calls = []

    # ── CUST_001  Priya Sharma ──────────────────────────────────────────
    # 32 bookings, 2 refunds (cancellations), 0 no-show. Call 2.
    cid = "CUST_001"
    acct = datetime(2023, 8, 1, 10, 0)
    rows, s = _generics(cid, acct, 29)
    bookings.extend(rows)
    bookings.append(_bk(f"{cid}_B{s:03d}", cid, "EXP_LOUVRE",
        datetime(2024, 6, 15, 10, 0), datetime(2024, 6, 1, 10, 0),
        reason="cancellation", req_at=datetime(2024, 6, 12, 10, 0),
        status="approved", cw=True, prate=1.0)); s += 1
    bookings.append(_bk(f"{cid}_B{s:03d}", cid, "EXP_SG_NIGHT",
        datetime(2025, 3, 20, 10, 0), datetime(2025, 3, 5, 10, 0),
        reason="cancellation", req_at=datetime(2025, 3, 17, 10, 0),
        status="approved", cw=True, prate=1.0)); s += 1
    cb = f"{cid}_B{s:03d}"
    bookings.append(_bk(cb, cid, "EXP_PARIS_CRUISE",
        datetime(2026, 3, 5, 19, 0), datetime(2026, 2, 20, 10, 0),
        reason="cancellation", req_at=datetime(2026, 2, 26, 11, 0),
        status="pending", cw=True, prate=1.0, ro=False))
    calls.append(("CALL_002", cid, cb,
        "Hello, I need to cancel my booking for the Paris Seine River Cruise next week. "
        "Something came up with work and I won't be able to make it. Can I get a refund?",
        "cancellation", "layer1_auto_approve",
        "Clean customer, policy-compliant cancellation", 2))

    # ── CUST_002  Daniel Kim ────────────────────────────────────────────
    # 14 bookings, 1 refund (cancellation), 0 no-show. Call 5.
    cid = "CUST_002"
    acct = datetime(2024, 8, 1, 10, 0)
    rows, s = _generics(cid, acct, 12)
    bookings.extend(rows)
    bookings.append(_bk(f"{cid}_B{s:03d}", cid, "EXP_LOUVRE",
        datetime(2025, 4, 10, 10, 0), datetime(2025, 3, 28, 10, 0),
        reason="cancellation", req_at=datetime(2025, 4, 7, 10, 0),
        status="approved", cw=True, prate=1.0)); s += 1
    cb = f"{cid}_B{s:03d}"
    bookings.append(_bk(cb, cid, "EXP_LONDON_FOOD",
        datetime(2026, 2, 25, 18, 0), datetime(2026, 2, 20, 9, 30),
        reason="partial_service", req_at=datetime(2026, 2, 26, 10, 0),
        status="pending", cw=False, ptype="partially_refundable", prate=0.5, qr=True,
        notes="Customer reported two of four food stops were closed."))
    calls.append(("CALL_005", cid, cb,
        "Hey, I went on the London food tour yesterday and honestly it was disappointing. "
        "Two of the four stops listed in the description were skipped because the restaurants "
        "were closed. I feel like I only got half the experience.",
        "partial_service", "layer2_3_low",
        "Low risk partial service claim", 5))

    # ── CUST_003  Elena Rossi ───────────────────────────────────────────
    # 45 bookings, 4 refunds (2 cancel, 1 partial, 1 no-show), 1 no-show claim, 0 contradicted. No call.
    cid = "CUST_003"
    acct = datetime(2023, 2, 1, 10, 0)
    rows, s = _generics(cid, acct, 41)
    bookings.extend(rows)
    bookings.append(_bk(f"{cid}_B{s:03d}", cid, "EXP_LOUVRE",
        datetime(2024, 3, 10, 10, 0), datetime(2024, 2, 25, 10, 0),
        reason="cancellation", req_at=datetime(2024, 3, 7, 10, 0),
        status="approved", cw=True, prate=1.0, ss=True)); s += 1
    bookings.append(_bk(f"{cid}_B{s:03d}", cid, "EXP_SG_NIGHT",
        datetime(2024, 9, 5, 10, 0), datetime(2024, 8, 20, 10, 0),
        reason="cancellation", req_at=datetime(2024, 9, 2, 10, 0),
        status="approved", cw=True, prate=1.0)); s += 1
    bookings.append(_bk(f"{cid}_B{s:03d}", cid, "EXP_ROME_FOOD",
        datetime(2025, 1, 15, 10, 0), datetime(2025, 1, 1, 10, 0),
        reason="partial_service", req_at=datetime(2025, 1, 16, 10, 0),
        status="approved", cw=False, ptype="partially_refundable", prate=0.5, qr=True,
        notes="Weather disruption; tour shortened, partial refund granted.")); s += 1
    bookings.append(_bk(f"{cid}_B{s:03d}", cid, "EXP_BALI_TREK",
        datetime(2025, 6, 10, 5, 0), datetime(2025, 5, 28, 10, 0),
        reason="no_show", req_at=datetime(2025, 6, 10, 12, 0),
        status="approved", cw=False, ptype="partially_refundable", prate=0.5,
        notes="Customer reported sudden illness; medical note provided."))

    # ── CUST_004  Raj Mehta ─────────────────────────────────────────────
    # 5 bookings, 0 refunds. No call.
    cid = "CUST_004"
    rows, _ = _generics(cid, datetime(2025, 8, 1, 10, 0), 5)
    bookings.extend(rows)

    # ── CUST_005  Sophie Laurent ────────────────────────────────────────
    # 1 booking, 0 refunds. Call 10 (thin data, missing confirmation).
    cid = "CUST_005"
    cb = f"{cid}_B001"
    bookings.append(_bk(cb, cid, "EXP_LISBON_SUNSET",
        datetime(2026, 2, 20, 18, 30), datetime(2026, 2, 18, 16, 0),
        reason="technical_issue", req_at=datetime(2026, 2, 21, 11, 0),
        status="pending", cw=False, ptype="partially_refundable", prate=0.5,
        co=False, ro=False, cs=None, qr=None))
    calls.append(("CALL_010", cid, cb,
        "Hi, this is my first time using Headout. I booked the sunset sailing in Lisbon "
        "but I never received any confirmation email or ticket. I went to the pier and they "
        "had no record of my booking. I'd like a refund.",
        "technical_issue", "layer2_3_medium",
        "First-time customer, missing confirmation", 10))

    # ── CUST_006  Marco Torres ──────────────────────────────────────────
    # 11 bookings, 5 refunds, 3 no-show claims (1 contradicted). No call.
    cid = "CUST_006"
    acct = datetime(2024, 8, 1, 10, 0)
    rows, s = _generics(cid, acct, 6)
    bookings.extend(rows)
    bookings.append(_bk(f"{cid}_B{s:03d}", cid, "EXP_LONDON_EYE",
        datetime(2025, 2, 10, 10, 0), datetime(2025, 1, 28, 10, 0),
        reason="cancellation", req_at=datetime(2025, 2, 7, 10, 0),
        status="approved", cw=True, prate=1.0)); s += 1
    bookings.append(_bk(f"{cid}_B{s:03d}", cid, "EXP_LONDON_EYE",
        datetime(2025, 4, 15, 10, 0), datetime(2025, 4, 1, 10, 0),
        reason="cancellation", req_at=datetime(2025, 4, 12, 10, 0),
        status="approved", cw=True, prate=1.0)); s += 1
    bookings.append(_bk(f"{cid}_B{s:03d}", cid, "EXP_DUBAI_SAFARI",
        datetime(2025, 7, 5, 16, 0), datetime(2025, 6, 20, 10, 0),
        reason="no_show", req_at=datetime(2025, 7, 6, 10, 0),
        status="approved", cw=False, ptype="non_cancelable", prate=0.0)); s += 1
    bookings.append(_bk(f"{cid}_B{s:03d}", cid, "EXP_DUBAI_SAFARI",
        datetime(2025, 9, 10, 16, 0), datetime(2025, 8, 25, 10, 0),
        reason="no_show", req_at=datetime(2025, 9, 11, 10, 0),
        status="approved", cw=False, ptype="non_cancelable", prate=0.0, qr=True,
        notes="Customer was polite but insisted tour did not happen. QR scan showed check-in. "
              "Approved refund per manager instruction.")); s += 1
    bookings.append(_bk(f"{cid}_B{s:03d}", cid, "EXP_COL_SKIP",
        datetime(2025, 11, 20, 10, 0), datetime(2025, 11, 5, 10, 0),
        reason="no_show", req_at=datetime(2025, 11, 21, 10, 0),
        status="approved", cw=False, ptype="non_cancelable", prate=0.0))

    # ── CUST_007  Lisa Chen ─────────────────────────────────────────────
    # 8 bookings, 4 refunds, 2 no-show (0 contradicted). Call 9.
    cid = "CUST_007"
    acct = datetime(2025, 4, 1, 10, 0)
    rows, s = _generics(cid, acct, 3)
    bookings.extend(rows)
    bookings.append(_bk(f"{cid}_B{s:03d}", cid, "EXP_NYC_BROADWAY",
        datetime(2025, 8, 10, 20, 0), datetime(2025, 7, 25, 10, 0),
        reason="other", req_at=datetime(2025, 8, 11, 10, 0),
        status="approved", cw=False, ptype="non_cancelable", prate=0.0, qr=True,
        notes="Customer claims experience was not as described. Seems rehearsed. "
              "Gave same story structure for two different experiences.")); s += 1
    bookings.append(_bk(f"{cid}_B{s:03d}", cid, "EXP_BALI_TREK",
        datetime(2025, 9, 15, 5, 0), datetime(2025, 9, 1, 10, 0),
        reason="other", req_at=datetime(2025, 9, 16, 10, 0),
        status="approved", cw=False, ptype="non_cancelable", prate=0.0, qr=True,
        notes="Customer claims experience was not as described. Story structure similar to prior.")); s += 1
    bookings.append(_bk(f"{cid}_B{s:03d}", cid, "EXP_LOUVRE",
        datetime(2025, 11, 5, 10, 0), datetime(2025, 10, 20, 10, 0),
        reason="no_show", req_at=datetime(2025, 11, 6, 10, 0),
        status="approved", cw=False, ptype="non_cancelable", prate=0.0,
        notes="Customer claimed taxi issues and requested refund.")); s += 1
    bookings.append(_bk(f"{cid}_B{s:03d}", cid, "EXP_SG_NIGHT",
        datetime(2026, 1, 10, 19, 0), datetime(2025, 12, 28, 10, 0),
        reason="no_show", req_at=datetime(2026, 1, 11, 10, 0),
        status="approved", cw=False, ptype="non_cancelable", prate=0.0,
        notes="Repeated no-show claim; QR data unavailable.")); s += 1
    cb = f"{cid}_B{s:03d}"
    bookings.append(_bk(cb, cid, "EXP_TOKYO_TEAMLAB",
        datetime(2026, 2, 20, 20, 0), datetime(2026, 2, 10, 14, 0),
        reason="other", req_at=datetime(2026, 2, 21, 9, 0),
        status="pending", cw=False, ptype="non_cancelable", prate=0.0, qr=True,
        notes="Customer claims half installations were closed."))
    calls.append(("CALL_009", cid, cb,
        "The Tokyo Teamlab exhibit was nothing like what was shown on the website. "
        "Half the installations were closed for maintenance and nobody told us beforehand. "
        "I want a full refund.",
        "other", "layer2_3_high",
        "Repeat chancer, not-as-described pattern", 9))

    # ── CUST_008  Tom Wallace ───────────────────────────────────────────
    # 6 bookings, 3 refunds, 2 no-show (2 contradicted). Call 3.
    cid = "CUST_008"
    acct = datetime(2025, 6, 1, 10, 0)
    rows, s = _generics(cid, acct, 2)
    bookings.extend(rows)
    bookings.append(_bk(f"{cid}_B{s:03d}", cid, "EXP_DUBAI_SAFARI",
        datetime(2025, 9, 15, 16, 0), datetime(2025, 9, 1, 10, 0),
        reason="no_show", req_at=datetime(2025, 9, 16, 10, 0),
        status="approved", cw=False, ptype="non_cancelable", prate=0.0, qr=True,
        notes="Customer became aggressive when told QR showed attendance. "
              "Threatened to leave negative reviews. Threatened chargeback. "
              "Escalated to floor manager who approved coupon.")); s += 1
    bookings.append(_bk(f"{cid}_B{s:03d}", cid, "EXP_NYC_BROADWAY",
        datetime(2025, 11, 10, 20, 0), datetime(2025, 10, 25, 10, 0),
        reason="no_show", req_at=datetime(2025, 11, 11, 10, 0),
        status="approved", cw=False, ptype="non_cancelable", prate=0.0, qr=True,
        notes="QR confirms attendance. Customer aggressive again. Coupon issued.")); s += 1
    bookings.append(_bk(f"{cid}_B{s:03d}", cid, "EXP_LONDON_EYE",
        datetime(2026, 1, 5, 14, 0), datetime(2025, 12, 20, 10, 0),
        reason="cancellation", req_at=datetime(2026, 1, 4, 10, 0),
        status="approved", cw=False, ptype="non_cancelable", prate=0.0,
        notes="Last-minute cancellation, goodwill coupon applied.")); s += 1
    cb = f"{cid}_B{s:03d}"
    bookings.append(_bk(cb, cid, "EXP_DUBAI_SAFARI",
        datetime(2026, 2, 20, 16, 0), datetime(2026, 2, 15, 9, 0),
        reason="no_show", req_at=datetime(2026, 2, 23, 10, 0),
        status="pending", cw=False, ptype="non_cancelable", prate=0.0, qr=True,
        notes="Customer claims taxi did not arrive; QR logs confirm check-in."))
    calls.append(("CALL_003", cid, cb,
        "I'm calling about the Dubai Desert Safari I was supposed to go on last Tuesday. "
        "I never made it there, the taxi didn't show up and I missed the whole thing. "
        "I want my money back.",
        "no_show", "layer1_auto_flag_l2",
        "QR contradicts no-show claim", 3))

    # ── CUST_009  Ananya Nair ───────────────────────────────────────────
    # 20 bookings, 6 refunds, 2 no-show (0 contradicted). Call 6.
    cid = "CUST_009"
    acct = datetime(2024, 2, 1, 10, 0)
    rows, s = _generics(cid, acct, 13)
    bookings.extend(rows)
    for i in range(2):
        bookings.append(_bk(f"{cid}_B{s:03d}", cid, "EXP_AMS_CANAL",
            datetime(2024, 10, 10 + i * 45, 14, 0) if i == 0 else datetime(2024, 11, 25, 14, 0),
            datetime(2024, 9, 25 + i * 45, 10, 0) if i == 0 else datetime(2024, 11, 10, 10, 0),
            reason="cancellation", req_at=datetime(2024, 10, 7 + i * 45, 10, 0) if i == 0 else datetime(2024, 11, 22, 10, 0),
            status="approved", cw=True, prate=1.0)); s += 1
    for i in range(2):
        d = datetime(2025, 3, 10, 10, 0) if i == 0 else datetime(2025, 6, 15, 10, 0)
        c = d - timedelta(days=14)
        bookings.append(_bk(f"{cid}_B{s:03d}", cid, "EXP_ROME_FOOD",
            d, c, reason="partial_service", req_at=d + timedelta(days=1),
            status="approved", cw=False, ptype="partially_refundable", prate=0.5,
            notes="Customer reported minor issues with tour.")); s += 1
    for i in range(2):
        d = datetime(2025, 8, 5, 5, 0) if i == 0 else datetime(2025, 10, 20, 5, 0)
        c = d - timedelta(days=14)
        bookings.append(_bk(f"{cid}_B{s:03d}", cid, "EXP_BALI_TREK",
            d, c, reason="no_show", req_at=d + timedelta(days=1),
            status="approved", cw=False, ptype="non_cancelable", prate=0.0)); s += 1
    cb = f"{cid}_B{s:03d}"
    bookings.append(_bk(cb, cid, "EXP_BALI_TREK",
        datetime(2026, 2, 21, 5, 0), datetime(2026, 2, 10, 8, 0),
        reason="no_show", req_at=datetime(2026, 2, 22, 9, 0),
        status="pending", cw=False, ptype="non_cancelable", prate=0.0))
    calls.append(("CALL_006", cid, cb,
        "I had booked the Bali Sunrise Trek for last Friday but I wasn't able to make it. "
        "Is it possible to get a refund?",
        "no_show", "layer2_3_medium",
        "Medium-risk no-show on non-cancelable", 6))

    # ── CUST_010  James Liu ─────────────────────────────────────────────
    # 18 bookings, 11 refunds (1 no-show + 10 cancellations on high-value non-cancelable). Call 8.
    cid = "CUST_010"
    acct = datetime(2025, 4, 15, 10, 0)
    rows, s = _generics(cid, acct, 6, emails=False, eids=HIGH_VALUE_IDS)
    for r in rows:
        bookings.append(r)
    bookings.append(_bk(f"{cid}_B{s:03d}", cid, "EXP_DUBAI_SAFARI",
        datetime(2025, 7, 10, 16, 0), datetime(2025, 6, 25, 10, 0),
        reason="no_show", req_at=datetime(2025, 7, 11, 10, 0),
        status="approved", cw=False, ptype="non_cancelable", prate=0.0,
        co=False, ro=False)); s += 1
    for i in range(10):
        eid = HIGH_VALUE_IDS[i % 3]
        d = datetime(2025, 8, 1, 10, 0) + timedelta(days=15 * i)
        c = d - timedelta(days=2)
        bookings.append(_bk(f"{cid}_B{s:03d}", cid, eid,
            d, c, reason="cancellation", req_at=d - timedelta(days=1),
            status="approved", cw=False, ptype="non_cancelable", prate=0.0,
            co=False, ro=False,
            notes="High-value last-minute cancellation." if i < 2 else None)); s += 1
    cb = f"{cid}_B{s:03d}"
    bookings.append(_bk(cb, cid, "EXP_NYC_HELI",
        datetime(2026, 2, 24, 17, 0), datetime(2026, 2, 15, 13, 0),
        reason="cancellation", req_at=datetime(2026, 2, 25, 10, 0),
        status="pending", cw=False, ptype="non_cancelable", prate=0.0,
        co=False, ro=False,
        notes="Another high-value non-cancelable last-minute cancellation."))
    calls.append(("CALL_008", cid, cb,
        "I need to cancel my helicopter tour booking. Something came up and I can't make it anymore.",
        "cancellation", "layer2_3_high",
        "High-risk arbitrageur cancellation", 8))

    # ── CUST_011  Victor Okafor ─────────────────────────────────────────
    # 22 bookings, 9 refunds (3 self-service + 6 agent). No call.
    cid = "CUST_011"
    acct = datetime(2025, 2, 1, 10, 0)
    mid_high = ["EXP_NYC_BROADWAY", "EXP_DUBAI_SAFARI", "EXP_PARIS_CRUISE"]
    rows, s = _generics(cid, acct, 13, eids=mid_high)
    bookings.extend(rows)
    for i in range(3):
        d = datetime(2025, 5, 10, 10, 0) + timedelta(days=30 * i)
        c = d - timedelta(days=10)
        bookings.append(_bk(f"{cid}_B{s:03d}", cid, mid_high[i % 3],
            d, c, reason="cancellation", req_at=d - timedelta(days=3),
            status="approved", cw=True, prate=1.0, ss=True)); s += 1
    for i in range(6):
        eid = mid_high[i % 3]
        d = datetime(2025, 9, 1, 10, 0) + timedelta(days=20 * i)
        c = d - timedelta(days=7)
        reason = "cancellation" if i < 3 else "other"
        notes = "Requested cancellation close to cut-off." if reason == "cancellation" else "Minor service issues reported."
        bookings.append(_bk(f"{cid}_B{s:03d}", cid, eid,
            d, c, reason=reason, req_at=d + timedelta(days=1),
            status="approved", cw=False, ptype="partially_refundable", prate=0.5,
            notes=notes)); s += 1

    # ── CUST_012  Sasha Petrov ──────────────────────────────────────────
    # 7 bookings, 5 refunds, coordinator-adjacent with CUST_013. No call.
    cid = "CUST_012"
    acct = datetime(2025, 10, 1, 10, 0)
    rows, s = _generics(cid, acct, 2)
    bookings.extend(rows)
    coord_exps  = ["EXP_PRG_NIGHT", "EXP_BERLIN_WALL", "EXP_PARIS_CRUISE"]
    coord_dates = [datetime(2025, 12, 5, 19, 0), datetime(2025, 12, 20, 10, 0), datetime(2026, 1, 15, 19, 0)]
    for i in range(3):
        c = coord_dates[i] - timedelta(days=7)
        bookings.append(_bk(f"{cid}_B{s:03d}", cid, coord_exps[i],
            coord_dates[i], c, reason="cancellation",
            req_at=coord_dates[i] + timedelta(days=1),
            status="approved", cw=False, ptype="non_cancelable", prate=0.0,
            notes="Booked same experience same day as another refund requestor. Could be coincidence.")); s += 1
    for i in range(2):
        d = datetime(2026, 2, 1, 10, 0) + timedelta(days=7 * i)
        c = d - timedelta(days=5)
        bookings.append(_bk(f"{cid}_B{s:03d}", cid, "EXP_NYC_BROADWAY",
            d, c, reason="cancellation", req_at=d + timedelta(days=1),
            status="approved", cw=False, ptype="non_cancelable", prate=0.0,
            notes="Multiple similar refunds in short tenure.")); s += 1

    # ── CUST_013  Nina Volkov ───────────────────────────────────────────
    # 5 bookings, 4 refunds, coordinator-adjacent with CUST_012. No call.
    cid = "CUST_013"
    acct = datetime(2025, 11, 1, 10, 0)
    rows, s = _generics(cid, acct, 1)
    bookings.extend(rows)
    for i in range(3):
        c = coord_dates[i] - timedelta(days=5)
        bookings.append(_bk(f"{cid}_B{s:03d}", cid, coord_exps[i],
            coord_dates[i], c, reason="cancellation",
            req_at=coord_dates[i] + timedelta(days=1),
            status="approved", cw=False, ptype="non_cancelable", prate=0.0,
            notes="Refunded overlapping bookings; potential coordination.")); s += 1
    bookings.append(_bk(f"{cid}_B{s:03d}", cid, "EXP_NYC_BROADWAY",
        datetime(2026, 2, 5, 20, 0), datetime(2026, 1, 25, 10, 0),
        reason="cancellation", req_at=datetime(2026, 2, 6, 10, 0),
        status="approved", cw=False, ptype="non_cancelable", prate=0.0,
        notes="Another late refund request."))

    # ── CUST_014  Aisha Khan ────────────────────────────────────────────
    # 9 bookings, 6 refunds, 2 no-show (2 contradicted), retrospective flag. Call 4.
    cid = "CUST_014"
    acct = datetime(2024, 2, 1, 10, 0)
    rows, s = _generics(cid, acct, 2)
    bookings.extend(rows)
    for i in range(2):
        d = datetime(2024, 7, 10, 16, 0) + timedelta(days=60 * i)
        c = d - timedelta(days=14)
        bookings.append(_bk(f"{cid}_B{s:03d}", cid, "EXP_DUBAI_SAFARI",
            d, c, reason="no_show", req_at=d + timedelta(days=1),
            status="approved", cw=False, ptype="non_cancelable", prate=0.0, qr=True,
            notes="No-show claim contradicted by QR; approved before retrospective flag.")); s += 1
    for i in range(4):
        d = datetime(2024, 12, 1, 10, 0) + timedelta(days=30 * i)
        c = d - timedelta(days=10)
        bookings.append(_bk(f"{cid}_B{s:03d}", cid, "EXP_AMS_CANAL",
            d, c, reason="cancellation", req_at=d + timedelta(days=1),
            status="approved", cw=False, ptype="non_cancelable", prate=0.0,
            notes="Multiple cancellations leading to retrospective flag.")); s += 1
    cb = f"{cid}_B{s:03d}"
    bookings.append(_bk(cb, cid, "EXP_BCN_GOTHIC",
        datetime(2026, 3, 1, 10, 0), datetime(2026, 2, 20, 9, 0),
        reason="cancellation", req_at=datetime(2026, 2, 24, 15, 0),
        status="pending", cw=True, prate=1.0, ro=False))
    calls.append(("CALL_004", cid, cb,
        "Hi, I'd like to cancel my booking for the Barcelona Gothic Quarter Walk. "
        "I'm cancelling a few days ahead because my plans changed.",
        "cancellation", "layer1_auto_approve",
        "Flagged but policy-compliant cancellation", 4))

    # ── CUST_015  Sarah Mitchell ────────────────────────────────────────
    # 12 bookings, 1 refund. Call 1 (vendor anomaly).
    cid = "CUST_015"
    acct = datetime(2025, 2, 1, 10, 0)
    rows, s = _generics(cid, acct, 10)
    bookings.extend(rows)
    bookings.append(_bk(f"{cid}_B{s:03d}", cid, "EXP_LONDON_EYE",
        datetime(2025, 10, 5, 14, 0), datetime(2025, 9, 20, 10, 0),
        reason="cancellation", req_at=datetime(2025, 10, 2, 10, 0),
        status="approved", cw=True, prate=1.0)); s += 1
    cb = f"{cid}_B{s:03d}"
    bookings.append(_bk(cb, cid, "EXP_ROME_COL_01",
        datetime(2026, 2, 22, 10, 0), datetime(2026, 2, 14, 10, 0),
        reason="no_show", req_at=datetime(2026, 2, 22, 13, 0),
        status="pending", cw=False, ptype="non_cancelable", prate=0.0,
        notes="Guide did not show up at meeting point."))
    calls.append(("CALL_001", cid, cb,
        "Hi, I booked the Colosseum tour for last Sunday but when we got there, nobody was "
        "waiting for us. We waited for 30 minutes and the guide never showed up. "
        "I'd like a full refund please.",
        "no_show", "layer0_vendor",
        "Vendor anomaly - Rome Colosseum", 1))

    # ── CUST_016  Kenji Tanaka ──────────────────────────────────────────
    # 7 bookings, 0 refunds (profile stale – Rome anomaly happened after last computation). No call.
    cid = "CUST_016"
    acct = datetime(2025, 6, 1, 10, 0)
    rows, s = _generics(cid, acct, 6)
    bookings.extend(rows)
    bookings.append(_bk(f"{cid}_B{s:03d}", cid, "EXP_ROME_COL_01",
        datetime(2026, 2, 22, 10, 0), datetime(2026, 2, 14, 10, 30),
        reason="no_show", req_at=datetime(2026, 2, 22, 14, 0),
        status="approved", cw=False, ptype="non_cancelable", prate=0.0,
        notes="Vendor-side failure; grouped with other Rome Colosseum complaints."))

    # ── CUST_017  Maria Garcia ──────────────────────────────────────────
    # 25 bookings, 2 refunds. No call.
    cid = "CUST_017"
    acct = datetime(2024, 2, 1, 10, 0)
    rows, s = _generics(cid, acct, 23)
    bookings.extend(rows)
    bookings.append(_bk(f"{cid}_B{s:03d}", cid, "EXP_AMS_CANAL",
        datetime(2025, 5, 10, 14, 0), datetime(2025, 4, 28, 10, 0),
        reason="partial_service", req_at=datetime(2025, 5, 11, 10, 0),
        status="approved", cw=False, ptype="partially_refundable", prate=0.5, qr=True,
        notes="Partial service issue resolved with partial refund.")); s += 1
    bookings.append(_bk(f"{cid}_B{s:03d}", cid, "EXP_ROME_COL_01",
        datetime(2026, 2, 22, 10, 0), datetime(2026, 2, 14, 11, 0),
        reason="no_show", req_at=datetime(2026, 2, 23, 9, 0),
        status="approved", cw=False, ptype="non_cancelable", prate=0.0,
        notes="Vendor investigation opened due to multiple Rome Colosseum failures."))

    # ── CUST_018  Alex Drummond ─────────────────────────────────────────
    # 15 bookings, 5 refunds, 1 no-show (not contradicted). Call 7.
    cid = "CUST_018"
    acct = datetime(2025, 2, 1, 10, 0)
    rows, s = _generics(cid, acct, 9)
    bookings.extend(rows)
    bookings.append(_bk(f"{cid}_B{s:03d}", cid, "EXP_COL_SKIP",
        datetime(2025, 7, 15, 10, 0), datetime(2025, 7, 1, 10, 0),
        reason="cancellation", req_at=datetime(2025, 7, 12, 10, 0),
        status="approved", cw=True, prate=1.0)); s += 1
    bookings.append(_bk(f"{cid}_B{s:03d}", cid, "EXP_LONDON_EYE",
        datetime(2025, 9, 20, 14, 0), datetime(2025, 9, 5, 10, 0),
        reason="cancellation", req_at=datetime(2025, 9, 17, 10, 0),
        status="approved", cw=True, prate=1.0, co=False, ro=False)); s += 1
    bookings.append(_bk(f"{cid}_B{s:03d}", cid, "EXP_ROME_FOOD",
        datetime(2025, 11, 10, 12, 0), datetime(2025, 10, 28, 10, 0),
        reason="partial_service", req_at=datetime(2025, 11, 11, 10, 0),
        status="approved", cw=False, ptype="partially_refundable", prate=0.5)); s += 1
    bookings.append(_bk(f"{cid}_B{s:03d}", cid, "EXP_LONDON_FOOD",
        datetime(2026, 1, 5, 18, 0), datetime(2025, 12, 22, 10, 0),
        reason="technical_issue", req_at=datetime(2026, 1, 6, 10, 0),
        status="approved", cw=False, ptype="partially_refundable", prate=0.5)); s += 1
    bookings.append(_bk(f"{cid}_B{s:03d}", cid, "EXP_BALI_TREK",
        datetime(2026, 1, 25, 5, 0), datetime(2026, 1, 12, 10, 0),
        reason="no_show", req_at=datetime(2026, 1, 26, 10, 0),
        status="approved", cw=False, ptype="non_cancelable", prate=0.0)); s += 1
    cb = f"{cid}_B{s:03d}"
    bookings.append(_bk(cb, cid, "EXP_AMS_CANAL",
        datetime(2026, 2, 22, 14, 0), datetime(2026, 2, 15, 12, 0),
        reason="technical_issue", req_at=datetime(2026, 2, 22, 17, 0),
        status="pending", cw=False, ptype="partially_refundable", prate=0.5,
        ro=False, qr=None))
    calls.append(("CALL_007", cid, cb,
        "I booked the Amsterdam Canal Cruise for Saturday and when I got there, the app "
        "kept crashing and I couldn't pull up my ticket. By the time I got it working, "
        "I'd missed the boarding window. Can I get a refund?",
        "technical_issue", "layer2_3_medium",
        "Medium-risk technical issue, no QR", 7))

    # ── Customer profile rows ───────────────────────────────────────────
    # (customer_id, name, account_created_at, total_bookings, total_refunds,
    #  total_no_show_refund_claims, no_show_claims_contradicted, refund_rate,
    #  last_profile_computed_at, risk_score, disposition, is_retrospective_fraud_flag)
    lpc = _ts(datetime(2026, 2, 25, 12, 0))
    customers = [
        ("CUST_001", "Priya Sharma",    _ts(datetime(2023, 8, 1, 10, 0)),  32, 2,  0, 0, 2/32,  lpc, 8,    "green",  0),
        ("CUST_002", "Daniel Kim",      _ts(datetime(2024, 8, 1, 10, 0)),  14, 1,  0, 0, 1/14,  lpc, 5,    "green",  0),
        ("CUST_003", "Elena Rossi",     _ts(datetime(2023, 2, 1, 10, 0)),  45, 4,  1, 0, 4/45,  lpc, 12,   "green",  0),
        ("CUST_004", "Raj Mehta",       _ts(datetime(2025, 8, 1, 10, 0)),   5, 0,  0, 0, 0.0,   lpc, 3,    "green",  0),
        ("CUST_005", "Sophie Laurent",  _ts(datetime(2026, 2, 10, 10, 0)),  1, 0,  0, 0, 0.0,   None, None,"green",  0),
        ("CUST_006", "Marco Torres",    _ts(datetime(2024, 8, 1, 10, 0)),  11, 5,  3, 1, 5/11,  lpc, 74,   "red",    0),
        ("CUST_007", "Lisa Chen",       _ts(datetime(2025, 4, 1, 10, 0)),   8, 4,  2, 0, 4/8,   lpc, 62,   "red",    0),
        ("CUST_008", "Tom Wallace",     _ts(datetime(2025, 6, 1, 10, 0)),   6, 3,  2, 2, 3/6,   lpc, 81,   "red",    0),
        ("CUST_009", "Ananya Nair",     _ts(datetime(2024, 2, 1, 10, 0)),  20, 6,  2, 0, 6/20,  lpc, 42,   "yellow", 0),
        ("CUST_010", "James Liu",       _ts(datetime(2025, 4, 15, 10, 0)), 18, 11, 1, 0, 11/18, lpc, 68,   "red",    0),
        ("CUST_011", "Victor Okafor",   _ts(datetime(2025, 2, 1, 10, 0)),  22, 9,  0, 0, 9/22,  lpc, 55,   "yellow", 0),
        ("CUST_012", "Sasha Petrov",    _ts(datetime(2025, 10, 1, 10, 0)),  7, 5,  0, 0, 5/7,   lpc, 78,   "red",    0),
        ("CUST_013", "Nina Volkov",     _ts(datetime(2025, 11, 1, 10, 0)),  5, 4,  0, 0, 4/5,   lpc, 85,   "red",    0),
        ("CUST_014", "Aisha Khan",      _ts(datetime(2024, 2, 1, 10, 0)),   9, 6,  2, 2, 6/9,   lpc, 82,   "red",    1),
        ("CUST_015", "Sarah Mitchell",  _ts(datetime(2025, 2, 1, 10, 0)),  12, 1,  0, 0, 1/12,  lpc, 10,   "green",  0),
        ("CUST_016", "Kenji Tanaka",    _ts(datetime(2025, 6, 1, 10, 0)),   7, 0,  0, 0, 0.0,   _ts(datetime(2026, 2, 20, 12, 0)), 4, "green", 0),
        ("CUST_017", "Maria Garcia",    _ts(datetime(2024, 2, 1, 10, 0)),  25, 2,  0, 0, 2/25,  lpc, 9,    "green",  0),
        ("CUST_018", "Alex Drummond",   _ts(datetime(2025, 2, 1, 10, 0)),  15, 5,  1, 0, 5/15,  lpc, 38,   "yellow", 0),
    ]

    return customers, bookings, calls


# ── Schema DDL ──────────────────────────────────────────────────────────────

_DDL_CUSTOMERS = """
CREATE TABLE IF NOT EXISTS customer_profiles (
    customer_id TEXT PRIMARY KEY,
    customer_name TEXT NOT NULL,
    account_created_at TIMESTAMP NOT NULL,
    total_bookings INTEGER NOT NULL,
    total_refunds INTEGER NOT NULL,
    total_no_show_refund_claims INTEGER NOT NULL,
    no_show_claims_contradicted INTEGER DEFAULT 0,
    refund_rate REAL NOT NULL,
    last_profile_computed_at TIMESTAMP,
    risk_score INTEGER,
    disposition TEXT CHECK(disposition IN ('green', 'yellow', 'red')),
    is_retrospective_fraud_flag INTEGER DEFAULT 0
);"""

_DDL_BOOKINGS = """
CREATE TABLE IF NOT EXISTS booking_refund_records (
    booking_id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL,
    experience_id TEXT NOT NULL,
    experience_name TEXT NOT NULL,
    experience_category TEXT NOT NULL,
    experience_value REAL NOT NULL,
    experience_value_percentile INTEGER NOT NULL,
    supplier_type TEXT CHECK(supplier_type IN ('direct_contract','aggregator','last_minute_marketplace')),
    confirmation_tat_promised TEXT CHECK(confirmation_tat_promised IN ('immediate','2hr','variable')),
    confirmation_sent_at TIMESTAMP,
    confirmation_opened INTEGER,
    reminder_opened INTEGER,
    qr_checkin_confirmed INTEGER,
    booking_date TIMESTAMP NOT NULL,
    booking_created_at TIMESTAMP NOT NULL,
    refund_requested_at TIMESTAMP,
    refund_reason TEXT CHECK(refund_reason IN ('no_show','cancellation','partial_service','technical_issue','other') OR refund_reason IS NULL),
    cancellation_window_applicable INTEGER,
    product_cancelable TEXT CHECK(product_cancelable IN ('cancelable','partially_refundable','non_cancelable')),
    refund_policy_rate REAL,
    is_self_service_cancellation INTEGER DEFAULT 0,
    refund_status TEXT CHECK(refund_status IN ('pending','approved','denied','escalated') OR refund_status IS NULL),
    agent_notes TEXT,
    FOREIGN KEY(customer_id) REFERENCES customer_profiles(customer_id)
);"""

_DDL_CALLS = """
CREATE TABLE IF NOT EXISTS incoming_calls (
    call_id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL,
    booking_id TEXT NOT NULL,
    customer_message TEXT NOT NULL,
    refund_reason TEXT NOT NULL,
    expected_layer_outcome TEXT NOT NULL,
    scenario_label TEXT NOT NULL,
    display_order INTEGER NOT NULL,
    FOREIGN KEY(customer_id) REFERENCES customer_profiles(customer_id),
    FOREIGN KEY(booking_id) REFERENCES booking_refund_records(booking_id)
);"""

_INS_CUST = """INSERT OR REPLACE INTO customer_profiles
(customer_id,customer_name,account_created_at,total_bookings,total_refunds,
 total_no_show_refund_claims,no_show_claims_contradicted,refund_rate,
 last_profile_computed_at,risk_score,disposition,is_retrospective_fraud_flag)
VALUES (?,?,?,?,?,?,?,?,?,?,?,?);"""

_INS_BK = """INSERT OR REPLACE INTO booking_refund_records
(booking_id,customer_id,experience_id,experience_name,experience_category,
 experience_value,experience_value_percentile,supplier_type,confirmation_tat_promised,
 confirmation_sent_at,confirmation_opened,reminder_opened,qr_checkin_confirmed,
 booking_date,booking_created_at,refund_requested_at,refund_reason,
 cancellation_window_applicable,product_cancelable,refund_policy_rate,
 is_self_service_cancellation,refund_status,agent_notes)
VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?);"""

_INS_CALL = """INSERT OR REPLACE INTO incoming_calls
(call_id,customer_id,booking_id,customer_message,refund_reason,
 expected_layer_outcome,scenario_label,display_order)
VALUES (?,?,?,?,?,?,?,?);"""


def create_database(db_path: str) -> None:
    """Create the SQLite database with schema and full seed data."""
    os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        cur.execute("DROP TABLE IF EXISTS incoming_calls;")
        cur.execute("DROP TABLE IF EXISTS booking_refund_records;")
        cur.execute("DROP TABLE IF EXISTS customer_profiles;")
        cur.execute(_DDL_CUSTOMERS)
        cur.execute(_DDL_BOOKINGS)
        cur.execute(_DDL_CALLS)

        customers, bookings, calls = _build_all()

        cur.executemany(_INS_CUST, customers)
        cur.executemany(_INS_BK, bookings)
        cur.executemany(_INS_CALL, calls)

        # Also ensure decision_log table exists for the app layer
        cur.execute("""
            CREATE TABLE IF NOT EXISTS decision_log (
                log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id TEXT, booking_id TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                classification TEXT, risk_score INTEGER,
                recommended_action TEXT, agent_decision TEXT,
                override_reason TEXT, escalated_to_l2 BOOLEAN DEFAULT 0,
                l2_decision TEXT, l2_reason TEXT
            );""")

        conn.commit()

        # Print summary
        for t in ("customer_profiles", "booking_refund_records", "incoming_calls"):
            n = cur.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            print(f"  {t}: {n} rows")
    finally:
        conn.close()


if __name__ == "__main__":
    default_path = os.path.join(os.path.dirname(__file__), "rad_seed_data.db")
    if os.path.exists(default_path):
        os.remove(default_path)
    create_database(default_path)
    print(f"Created seed database at {default_path}")
