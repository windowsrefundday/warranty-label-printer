from core.models import AssetRecord

class PlainTextLabelFormatter:
    """Formats structured asset records into physical thermal label layouts and colored terminal output."""

    RED = "\033[1;31m"
    RESET = "\033[0m"
    GREEN = "\033[1;32m"
    AMBER = "\033[1;33m"

    @classmethod
    def format_terminal_label(cls, asset: AssetRecord) -> str:
        """Formatted for Terminal CLI output with RED Expiration Date text."""
        border = "=" * 42
        divider = "-" * 42

        # Select status color
        if asset.warranty_status.lower() in ("expired", "coverage expiring", "lookup failed"):
            status_color = cls.RED
        else:
            status_color = cls.GREEN

        suffix = "" if asset.warranty_status.lower() == "lookup failed" else " WARRANTY"
        status_str = f"{status_color}[{asset.warranty_status.upper()}{suffix}]{cls.RESET}"

        entitlement_lines = ""
        for ent in asset.entitlements[:2]:
            entitlement_lines += f" * {ent.service_name[:38]}\n"

        # Expiration Date highlighted in RED text
        exp_date_colored = f"{cls.RED}{asset.expiration_date}{cls.RESET}"

        label = f"""{border}
  ASSET WARRANTY TAG | {asset.vendor.value.upper()}
{border}
MODEL   : {asset.model_name}
TAG / SN: {asset.serial_number}
STATUS  : {status_str}
START   : {asset.ship_date}
EXPIRES : {exp_date_colored}
SOURCE  : {asset.source_confidence.value}
{divider}
ENTITLEMENTS:
{entitlement_lines}{border}
SCAN DATE: {asset.timestamp}
{border}
"""
        return label

    @staticmethod
    def format_asset_label(asset: AssetRecord) -> str:
        """Plain text format without ANSI colors for disk file saving."""
        border = "=" * 42
        divider = "-" * 42
        suffix = "" if asset.warranty_status.lower() == "lookup failed" else " WARRANTY"
        status_str = f"[{asset.warranty_status.upper()}{suffix}]"

        entitlement_lines = ""
        for ent in asset.entitlements[:2]:
            entitlement_lines += f" * {ent.service_name[:38]}\n"

        return f"""{border}
  ASSET WARRANTY TAG | {asset.vendor.value.upper()}
{border}
MODEL   : {asset.model_name}
TAG / SN: {asset.serial_number}
STATUS  : {status_str}
START   : {asset.ship_date}
EXPIRES : {asset.expiration_date}
SOURCE  : {asset.source_confidence.value}
{divider}
ENTITLEMENTS:
{entitlement_lines}{border}
SCAN DATE: {asset.timestamp}
{border}
"""
