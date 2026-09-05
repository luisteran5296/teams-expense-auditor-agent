import json
import logging
from typing import List, Optional, Union
from pathlib import Path
from pydantic import BaseModel, Field
from google import genai
from google.genai import types

from src.config import settings

logger = logging.getLogger(__name__)


class LineItem(BaseModel):
    description: str = Field(description="Name or description of the purchased item/service")
    quantity: float = Field(default=1.0, description="Quantity purchased")
    unit_price: float = Field(default=0.0, description="Unit price per item")
    total_price: float = Field(default=0.0, description="Total price for this line")
    category: str = Field(default="General", description="Line category (e.g. Food, Beverage, Alcohol, Software, Transport)")


class ExtractedInvoice(BaseModel):
    vendor_name: str = Field(description="Name of the merchant, store, or vendor")
    invoice_or_receipt_number: Optional[str] = Field(default=None, description="Invoice or receipt number if visible")
    date: str = Field(description="Date of transaction in YYYY-MM-DD format (or closest approximation)")
    currency: str = Field(default="USD", description="Currency symbol or 3-letter ISO code (e.g. USD, EUR)")
    subtotal: float = Field(default=0.0, description="Subtotal amount before tax/tip")
    tax: float = Field(default=0.0, description="Sales tax, VAT, or GST amount")
    tip: float = Field(default=0.0, description="Tip, gratuity, or service fee")
    total_amount: float = Field(description="Final total monetary amount charged")
    category: str = Field(
        default="Other",
        description="Primary expense category: Meals & Entertainment, Software & Cloud, Travel & Lodging, Office Supplies, Hardware, or Other",
    )
    line_items: List[LineItem] = Field(default_factory=list, description="List of individual items purchased")
    payment_method: Optional[str] = Field(default=None, description="Payment method: e.g. Visa *1234, Cash, Amex")
    notes: Optional[str] = Field(default=None, description="Any noteworthy observations from receipt")


EXTRACTOR_PROMPT = """You are an expert Document AI Vision specialist for enterprise accounting.
Inspect the provided receipt or invoice document carefully and extract all transaction details.

Requirements:
1. Identify the merchant/vendor name accurately.
2. Read the transaction date and normalize to YYYY-MM-DD.
3. Extract each purchased line item with quantity, unit price, and total.
4. If this is a restaurant/meal receipt, check specifically if alcoholic beverages (beer, wine, cocktails, spirits) were purchased and tag their line item category as "Alcohol".
5. Extract subtotal, taxes, tips, and the final grand total.
6. Provide output strictly conforming to the requested JSON schema.
"""


class DocumentExtractorAgent:
    """Agent 1: Extracts structured data from receipt and invoice images or PDFs."""

    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None):
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.model_name = model_name or settings.GEMINI_MODEL
        self._client = None
        if self.api_key:
            self._client = genai.Client(api_key=self.api_key)

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key and self._client)

    async def extract_from_file(
        self,
        file_data: Union[bytes, str, Path],
        mime_type: str = "image/png",
    ) -> ExtractedInvoice:
        """Extracts structured invoice information using Gemini Multimodal Vision."""
        if not self.is_configured:
            logger.warning("Gemini API key not configured; returning fallback demo invoice.")
            return self._fallback_invoice()

        if isinstance(file_data, (str, Path)):
            with open(file_data, "rb") as f:
                bytes_content = f.read()
        else:
            bytes_content = file_data

        try:
            image_part = types.Part.from_bytes(data=bytes_content, mime_type=mime_type)
            
            response = self._client.models.generate_content(
                model=self.model_name,
                contents=[image_part, EXTRACTOR_PROMPT],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=ExtractedInvoice,
                    temperature=0.1,
                ),
            )

            result_json = response.text
            data = json.loads(result_json)
            return ExtractedInvoice(**data)

        except Exception as e:
            logger.error(f"Error during multimodal document extraction: {e}", exc_info=True)
            return self._fallback_invoice(error_note=str(e))

    def _fallback_invoice(self, error_note: Optional[str] = None) -> ExtractedInvoice:
        """Fallback invoice data for local testing."""
        return ExtractedInvoice(
            vendor_name="The Tech Bistro & Grill",
            invoice_or_receipt_number="REC-88492",
            date="2026-09-04",
            currency="USD",
            subtotal=64.50,
            tax=5.80,
            tip=12.00,
            total_amount=82.30,
            category="Meals & Entertainment",
            line_items=[
                LineItem(description="Grilled Salmon Plate", quantity=1, unit_price=32.00, total_price=32.00, category="Food"),
                LineItem(description="Caesar Salad", quantity=1, unit_price=14.50, total_price=14.50, category="Food"),
                LineItem(description="Craft IPA Beer", quantity=2, unit_price=9.00, total_price=18.00, category="Alcohol"),
            ],
            payment_method="Corporate Visa *9412",
            notes=f"Simulated extraction {f'({error_note})' if error_note else ''}",
        )
