"""
Utility helpers for the Finance Management module.
"""

import frappe


def get_network_path(main_type: str) -> str:
	"""
	Return the UNC network storage path for a given Cash Document main_type.

	The share name and IP/host are read from Cash Management Settings so they
	can be changed without a code deployment.

	Example result: \\\\192.168.1.114\\Fantasy\\e-dox\\Cash-2
	"""
	try:
		settings = frappe.get_single("Cash Management Settings")
		share_ip   = (settings.get("network_share_ip")   or "").strip()
		share_name = (settings.get("network_share_name") or "").strip()

		if not share_ip or not share_name:
			return ""

		base = f"\\\\{share_ip}\\{share_name}\\e-dox"

		sub_folder = {
			"Cash":   "Cash",
			"Bank":   "Bank",
			"Cash-2": "Cash-2",
			"Bank-2": "Bank-2",
			"JE":     "JE",
		}.get(main_type, "")

		return f"{base}\\{sub_folder}" if sub_folder else base

	except Exception:
		return ""
