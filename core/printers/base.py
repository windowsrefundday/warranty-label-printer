from abc import ABC, abstractmethod
from typing import List, Optional
from core.models import AssetRecord, PrintJobResult

class BasePrinterConnector(ABC):
    """
    Abstract Base Class for all Label Printer Connectors.
    To support a new printer brand or OS subsystem, subclass BasePrinterConnector.
    """

    target_printer: Optional[str] = None

    @property
    @abstractmethod
    def connector_name(self) -> str:
        """Returns human-readable name of the printer driver/connector."""
        pass

    @abstractmethod
    def list_printers(self) -> List[str]:
        """Lists available hardware printers for this connector."""
        pass

    @abstractmethod
    def print_label(self, asset: AssetRecord, printer_name: Optional[str] = None, label_format: str = "text") -> PrintJobResult:
        """
        Formats and prints an asset tag label for the provided AssetRecord.
        """
        pass
