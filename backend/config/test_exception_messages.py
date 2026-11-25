"""
Prompt 4 (E2E audit BUG-007): a pharmacist saw
"lines: {0: {'quantity': [ErrorDetail(string='Ensure …', code='min_value')]}}".
Nested validation errors must read as sentences, never as Python reprs.
"""
from django.test import SimpleTestCase
from rest_framework.exceptions import ErrorDetail, ValidationError

from config.exceptions import _get_error_message, custom_exception_handler


class ErrorMessageTests(SimpleTestCase):
    def test_nested_list_errors_read_as_sentences(self):
        data = {"lines": {0: {"quantity": [ErrorDetail("Ensure this value is greater than or equal to 1.", code="min_value")]}}}

        self.assertEqual(_get_error_message(data), "Line 1, quantity: Ensure this value is greater than or equal to 1.")

    def test_no_python_repr_ever_reaches_the_message(self):
        data = {
            "items": [{"dose": [ErrorDetail("This field is required.", code="required")]}, {}],
            "non_field_errors": [ErrorDetail("Stock is short.", code="invalid")],
            "detail_map": {"a": {"b": ["Deep problem."]}},
        }
        message = _get_error_message(data)
        for leaked in ("ErrorDetail", "{", "[", "code=", "string="):
            self.assertNotIn(leaked, message)
        self.assertIn("Item 1, dose: This field is required.", message)
        self.assertIn("Stock is short.", message)
        self.assertIn("Deep problem.", message)

    def test_simple_messages_are_unchanged(self):
        self.assertEqual(_get_error_message({"detail": "Not found."}), "Not found.")
        self.assertEqual(_get_error_message({"quantity": ["Too many."]}), "quantity: Too many.")
        self.assertEqual(_get_error_message(["One.", "Two."]), "One.; Two.")

    def test_handler_keeps_status_and_structured_details(self):
        exc = ValidationError({"lines": {0: {"quantity": ["Ensure this value is greater than or equal to 1."]}}})
        response = custom_exception_handler(exc, {"view": None, "request": None})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["message"], "Line 1, quantity: Ensure this value is greater than or equal to 1.")
        self.assertIn("lines", response.data["details"])
